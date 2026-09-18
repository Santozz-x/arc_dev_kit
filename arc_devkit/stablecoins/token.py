"""Circle stablecoin (USDC/EURC) ERC-20 wrapper for the Arc blockchain.

USDC on Arc has a dual interface (see docs/mainnet/MIGRATION_AUDIT.md Part B.6):
USDC is Arc's *native* gas token (18 decimals, read like ETH via
eth_getBalance), and is *also* exposed through an optional ERC-20 interface
at a fixed precompile address (arc_devkit.networks.USDC_ERC20_ADDRESS) using
the conventional 6 decimals. Both views share the same underlying balance —
there is no wrapper token. This module's StablecoinToken/USDCToken classes
operate on the ERC-20 (6-decimal) view; use native_usdc_balance() for the
native (18-decimal) gas balance. Never mix the two without converting.
"""

import logging
from decimal import Decimal

from web3 import Web3

from arc_devkit.core.connection import get_web3
from arc_devkit.networks import NATIVE_USDC_DECIMALS, USDC_ERC20_ADDRESS

logger = logging.getLogger(__name__)

# Circle stablecoins (USDC, EURC) all use 6 decimals on Arc via the ERC-20
# interface (distinct from native USDC's 18 decimals — see module docstring).
USDC_DECIMALS = 6
USDC_MULTIPLIER = 10**USDC_DECIMALS

# int annotation needed: mypy's int.__pow__ returns Any for a non-literal
# exponent (since a negative exponent would produce a float at runtime).
_NATIVE_USDC_MULTIPLIER: int = 10**NATIVE_USDC_DECIMALS

# Minimal ERC-20 ABI for supported operations
_ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_spender", "type": "address"},
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_from", "type": "address"},
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "transferFrom",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"},
        ],
        "name": "Transfer",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "owner", "type": "address"},
            {"indexed": True, "name": "spender", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"},
        ],
        "name": "Approval",
        "type": "event",
    },
]

# Deprecated: use arc_devkit.networks.USDC_ERC20_ADDRESS (or
# settings.network.contracts.usdc) instead. Kept as an alias for backward
# compatibility — this used to be a zero-address testnet placeholder before
# Circle published the real (network-independent) ERC-20 address.
USDC_ARC_TESTNET_ADDRESS = USDC_ERC20_ADDRESS


def native_usdc_balance(address: str, w3: Web3 | None = None) -> Decimal:
    """
    Return the *native* USDC gas balance of an address (18 decimals).

    This reads eth_getBalance, the same call used for any EVM chain's native
    coin — on Arc that balance IS USDC, not a separate gas token. This is
    NOT the same number as StablecoinToken.balance() / USDCToken.balance(),
    which reads the 6-decimal ERC-20 view via balanceOf(). Both represent the
    same underlying funds at different decimal scales — never compare them
    without converting first.
    """
    w3 = w3 or get_web3()
    checksum = Web3.to_checksum_address(address)
    wei = w3.eth.get_balance(checksum)
    return Decimal(str(wei)) / _NATIVE_USDC_MULTIPLIER


class StablecoinToken:
    """
    Wrapper for interacting with a Circle stablecoin ERC-20 contract on Arc.

    Supports balance reads, transfers, allowance queries, and approvals.
    Human-readable values are always in the stablecoin's own unit (Decimal);
    on-chain values are atomic units (int) with 6 decimal places.

    Example:
        usdc = StablecoinToken(contract_address="0x...", symbol="USDC")
        balance = usdc.balance("0xMyWallet...")
        print(f"Balance: {balance} {usdc.symbol}")
    """

    def __init__(
        self,
        contract_address: str,
        w3: Web3 | None = None,
        symbol: str = "USDC",
        decimals: int = USDC_DECIMALS,
    ) -> None:
        """
        Args:
            contract_address: Stablecoin contract address on the target network.
            w3: Optional Web3 instance (uses get_web3() if omitted).
            symbol: Human-readable ticker (e.g. "USDC", "EURC").
            decimals: Token decimals (Circle stablecoins on Arc use 6).
        """
        self.symbol = symbol
        self._decimals = decimals
        self._multiplier = 10**decimals
        self._w3 = w3 or get_web3()
        self._address = Web3.to_checksum_address(contract_address)
        self._contract = self._w3.eth.contract(address=self._address, abi=_ERC20_ABI)
        logger.debug("%s token initialized at contract %s", symbol, self._address)

    @property
    def contract_address(self) -> str:
        return self._address

    def _to_atomic(self, amount: Decimal) -> int:
        """Convert human-readable amount (Decimal) to atomic units (int)."""
        return int(amount * self._multiplier)

    def _from_atomic(self, amount: int) -> Decimal:
        """Convert atomic units (int) to human-readable amount (Decimal)."""
        return Decimal(str(Decimal(amount) / self._multiplier))

    def balance(self, address: str) -> Decimal:
        """
        Return the token balance of an address.

        Args:
            address: EVM address (checksummed or not).

        Returns:
            Balance in the token's human-readable unit.
        """
        checksum = Web3.to_checksum_address(address)
        atomic = self._contract.functions.balanceOf(checksum).call()
        bal = self._from_atomic(atomic)
        logger.debug("%s balance of %s: %s", self.symbol, checksum, bal)
        return bal

    def allowance(self, owner: str, spender: str) -> Decimal:
        """
        Return how much the spender is allowed to spend on behalf of owner.

        Returns:
            Allowance in the token's human-readable unit.
        """
        owner_cs = Web3.to_checksum_address(owner)
        spender_cs = Web3.to_checksum_address(spender)
        atomic = self._contract.functions.allowance(owner_cs, spender_cs).call()
        return self._from_atomic(atomic)

    def transfer(
        self,
        to: str,
        amount: Decimal,
        private_key: str,
        gas: int = 65_000,
    ) -> str:
        """
        Transfer tokens to an address.

        Args:
            to: EVM destination address.
            amount: Amount to transfer, in the token's human-readable unit.
            private_key: Sender's private key.
            gas: Gas limit (conservative default for ERC-20).

        Returns:
            Transaction hash (hex with 0x prefix).
        """
        from eth_account import Account

        destinatario = Web3.to_checksum_address(to)
        remetente = Account.from_key(private_key).address
        atomic = self._to_atomic(amount)

        tx = self._contract.functions.transfer(destinatario, atomic).build_transaction(
            {
                "from": remetente,
                "gas": gas,
                "gasPrice": self._w3.eth.gas_price,
                "nonce": self._w3.eth.get_transaction_count(remetente),
                "chainId": self._w3.eth.chain_id,
            }
        )

        signed = self._w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
        tx_hash_hex = "0x" + tx_hash.hex() if not tx_hash.hex().startswith("0x") else tx_hash.hex()

        logger.info("Transfer %s %s → %s: %s", self.symbol, remetente, destinatario, tx_hash_hex)
        return tx_hash_hex

    def approve(
        self,
        spender: str,
        amount: Decimal,
        private_key: str,
        gas: int = 65_000,
    ) -> str:
        """
        Approve a spender to spend tokens on behalf of the caller.

        Args:
            spender: EVM address to approve.
            amount: Allowance, in the token's human-readable unit.
            private_key: Owner's private key.
            gas: Gas limit.

        Returns:
            Transaction hash.
        """
        from eth_account import Account

        spender_cs = Web3.to_checksum_address(spender)
        owner = Account.from_key(private_key).address
        atomic = self._to_atomic(amount)

        tx = self._contract.functions.approve(spender_cs, atomic).build_transaction(
            {
                "from": owner,
                "gas": gas,
                "gasPrice": self._w3.eth.gas_price,
                "nonce": self._w3.eth.get_transaction_count(owner),
                "chainId": self._w3.eth.chain_id,
            }
        )

        signed = self._w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()

    def transfer_from(
        self,
        owner: str,
        to: str,
        amount: Decimal,
        private_key: str,
        gas: int = 65_000,
    ) -> str:
        """
        Transfer tokens from `owner` to `to` using a prior approve() allowance.

        Args:
            owner: Address that previously approved the caller as spender.
            to: EVM destination address.
            amount: Amount to transfer, in the token's human-readable unit.
            private_key: Spender's (caller's) private key.
            gas: Gas limit.

        Returns:
            Transaction hash.
        """
        from eth_account import Account

        owner_cs = Web3.to_checksum_address(owner)
        destinatario = Web3.to_checksum_address(to)
        spender = Account.from_key(private_key).address
        atomic = self._to_atomic(amount)

        tx = self._contract.functions.transferFrom(
            owner_cs, destinatario, atomic
        ).build_transaction(
            {
                "from": spender,
                "gas": gas,
                "gasPrice": self._w3.eth.gas_price,
                "nonce": self._w3.eth.get_transaction_count(spender),
                "chainId": self._w3.eth.chain_id,
            }
        )

        signed = self._w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()


class USDCToken(StablecoinToken):
    """
    USDC on Arc (ERC-20 view, 6 decimals).

    The ERC-20 address is identical on mainnet and testnet
    (arc_devkit.networks.USDC_ERC20_ADDRESS), so it's used as the default —
    no network guessing involved, unlike the old zero-address placeholder.
    Pass contract_address explicitly only if you need to override it.
    """

    def __init__(
        self,
        contract_address: str = USDC_ERC20_ADDRESS,
        w3: Web3 | None = None,
    ) -> None:
        super().__init__(contract_address, w3=w3, symbol="USDC", decimals=USDC_DECIMALS)


class EURCToken(StablecoinToken):
    """EURC on Arc. No default address yet — Circle hasn't published one."""

    def __init__(self, contract_address: str, w3: Web3 | None = None) -> None:
        super().__init__(contract_address, w3=w3, symbol="EURC", decimals=USDC_DECIMALS)
