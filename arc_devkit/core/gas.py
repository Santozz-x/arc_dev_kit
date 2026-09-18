"""Gas cost estimation for Arc transactions."""

import logging
from decimal import Decimal

from web3 import Web3

from arc_devkit.core.connection import get_web3

logger = logging.getLogger(__name__)

# Fixed gas cost for a native transfer (ETH/USDC) in gas units
GAS_NATIVE_TRANSFER = 21_000


def estimate_transfer(to: str, amount_usdc: float, from_address: str | None = None) -> dict:
    """
    Estimate the gas cost for a native transfer on Arc.

    Args:
        to: Recipient EVM address.
        amount_usdc: Amount to transfer (in USDC).
        from_address: Sender address (optional — used for a more precise estimate).

    Returns:
        Dict with gas_limit, gas_price_gwei, custo_usdc and custo_wei.
    """
    w3 = get_web3()

    recipient = Web3.to_checksum_address(to)
    gas_price_wei = w3.eth.gas_price
    gas_price_gwei = Decimal(str(w3.from_wei(gas_price_wei, "gwei")))

    # Native transfers use fixed 21,000 gas
    # For contracts, uses eth_estimateGas (more precise, requires from_address)
    if from_address:
        try:
            sender = Web3.to_checksum_address(from_address)
            gas_limit = w3.eth.estimate_gas(
                {
                    "from": sender,
                    "to": recipient,
                    "value": w3.to_wei(amount_usdc, "ether"),
                }
            )
        except Exception:
            gas_limit = GAS_NATIVE_TRANSFER
    else:
        gas_limit = GAS_NATIVE_TRANSFER

    cost_wei = gas_limit * gas_price_wei
    cost_usdc = Decimal(str(w3.from_wei(cost_wei, "ether")))

    logger.debug("Estimate: %d gas × %s gwei = %s USDC", gas_limit, gas_price_gwei, cost_usdc)

    return {
        "gas_limit": gas_limit,
        "gas_price_gwei": str(gas_price_gwei),
        "gas_price_wei": str(gas_price_wei),
        "custo_usdc": str(cost_usdc),
        "custo_wei": str(cost_wei),
        "amount_usdc": amount_usdc,
        "to": str(recipient),
    }


def quote_fee(
    to: str,
    amount: float,
    token: str = "native",
    from_address: str | None = None,
) -> dict:
    """
    Quote the fee for a transfer on Arc, denominated in USDC (the gas token).

    Arc's Stable Fee Design means gas is always paid in USDC regardless of
    what's being transferred, so this works for both native ARC transfers
    and stablecoin (USDC/EURC) ERC-20 transfers. Also reports whether a
    paymaster is available to sponsor/redenominate the fee (see
    arc_devkit.paymaster.detect_paymaster — always False until Arc publishes
    a paymaster contract).

    Args:
        to: Recipient EVM address.
        amount: Amount to transfer, in the given token's unit.
        token: "native" for native ARC, "usdc" for the ERC-20 USDC transfer.
        from_address: Sender address (optional — used for a more precise estimate).

    Returns:
        Dict with gas_limit, gas_price_gwei/wei, fee_usdc/wei, and paymaster_available.
    """
    from arc_devkit.core.validation import validate_address
    from arc_devkit.paymaster.detector import detect_paymaster

    if token not in ("native", "usdc"):
        raise ValueError(f"Unknown token {token!r} — use 'native' or 'usdc'.")

    w3 = get_web3()
    recipient = validate_address(to)
    gas_price_wei = w3.eth.gas_price
    gas_price_gwei = Decimal(str(w3.from_wei(gas_price_wei, "gwei")))

    if token == "usdc":
        from arc_devkit.config import settings
        from arc_devkit.stablecoins.token import _ERC20_ABI, USDC_MULTIPLIER

        usdc_contract_address = settings.network.contracts.usdc
        if usdc_contract_address is None:
            raise ValueError(f"No USDC contract configured for network {settings.arc_network!r}.")
        usdc_address = Web3.to_checksum_address(usdc_contract_address)
        contract = w3.eth.contract(address=usdc_address, abi=_ERC20_ABI)
        atomic = int(Decimal(str(amount)) * USDC_MULTIPLIER)
        gas_limit = 65_000  # conservative default for an ERC-20 transfer
        if from_address:
            try:
                sender = Web3.to_checksum_address(from_address)
                gas_limit = contract.functions.transfer(recipient, atomic).estimate_gas(
                    {"from": sender}
                )
            except Exception:
                pass
    else:
        if from_address:
            try:
                sender = Web3.to_checksum_address(from_address)
                gas_limit = w3.eth.estimate_gas(
                    {
                        "from": sender,
                        "to": recipient,
                        "value": w3.to_wei(amount, "ether"),
                    }
                )
            except Exception:
                gas_limit = GAS_NATIVE_TRANSFER
        else:
            gas_limit = GAS_NATIVE_TRANSFER

    cost_wei = gas_limit * gas_price_wei
    fee_usdc = Decimal(str(w3.from_wei(cost_wei, "ether")))

    paymaster = detect_paymaster()

    logger.debug(
        "Fee quote (%s): %d gas × %s gwei = %s USDC", token, gas_limit, gas_price_gwei, fee_usdc
    )

    return {
        "to": str(recipient),
        "token": token,
        "amount": amount,
        "gas_limit": gas_limit,
        "gas_price_gwei": str(gas_price_gwei),
        "gas_price_wei": str(gas_price_wei),
        "fee_usdc": str(fee_usdc),
        "fee_wei": str(cost_wei),
        "paymaster_available": paymaster.available,
    }
