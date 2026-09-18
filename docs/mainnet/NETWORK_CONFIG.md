# Network Configuration

All values below are sourced from `docs.arc.io` (Circle's official Arc documentation), extracted from the raw page HTML and cross-checked byte-for-byte — not summarized or guessed. Verified 2026-09-18. Full sourcing detail: [MIGRATION_AUDIT.md](MIGRATION_AUDIT.md) Part B.

Everything here is already registered in `arc_devkit/networks.py` — you don't need to copy these values into your own code; read them from `arc.network` (via the `Arc` facade) or `settings.network` (via `arc_devkit.config`).

## Mainnet

| Property | Value |
|---|---|
| Chain ID | `5042` (`0x13b2`) |
| RPC (HTTP) | `https://rpc.mainnet.arc.io` |
| RPC (WebSocket) | Not available on Circle's primary endpoint — HTTP-only. Third-party providers (Alchemy, Blockdaemon, QuickNode) offer WS. |
| Explorer | `https://explorer.arc.io` (Blockscout) |
| Native currency | USDC, 18 decimals |
| Launched | 2026-09-16 |

## Testnet

| Property | Value |
|---|---|
| Chain ID | `5042002` |
| RPC (HTTP) | `https://rpc.testnet.arc.io` |
| RPC (WebSocket) | `wss://rpc.testnet.arc.io` (supported on the primary endpoint) |
| Explorer | `https://explorer.testnet.arc.io` |
| Native currency | USDC, 18 decimals |
| Faucet | [faucet.circle.com](https://faucet.circle.com) (select "Arc Testnet") — no mainnet faucet exists, as expected |

## Alternative RPC providers

Circle's own RPC is the default, but you can point Arc DevKit at any provider by passing `rpc_url=`:

```python
from arc_devkit import Arc

arc = Arc.mainnet(rpc_url="https://arc-mainnet.g.alchemy.com/v2/YOUR_API_KEY")
```

| Provider | Mainnet HTTP | Mainnet WS |
|---|---|---|
| Circle (default) | `https://rpc.mainnet.arc.io` | — |
| Alchemy | `https://arc-mainnet.g.alchemy.com/v2/YOUR_API_KEY` | `wss://arc-mainnet.g.alchemy.com/v2/YOUR_API_KEY` |
| Blockdaemon | `https://rpc.blockdaemon.mainnet.arc.io` | `wss://rpc.blockdaemon.mainnet.arc.io/websocket` |
| dRPC | `https://rpc.drpc.mainnet.arc.io` | — |
| QuickNode | `https://rpc.quicknode.mainnet.arc.io` | `wss://rpc.quicknode.mainnet.arc.io` |

(Swap `mainnet` for `testnet` in each URL for the testnet equivalents — all four providers also serve testnet, all with WS support there.)

## Contract addresses

Verified byte-for-byte against `docs.arc.io/arc/references/contract-addresses`, and cross-checked against the page's own `explorer.arc.io`/`explorer.testnet.arc.io` links, which unambiguously tie each address to its network.

| Contract | Mainnet | Testnet | Notes |
|---|---|---|---|
| USDC (ERC-20 view) | `0x3600000000000000000000000000000000000000` | same | Precompile — see [USDC.md](USDC.md) |
| EURC | `0xbEf5f6d51CB62b58e6A8f77868681825C6fe21c1` | `0x89B50855Aa3bE2F677cD6303Cec089B5F319D72a` | 6 decimals |
| USYC | `0x8a5D989Bbb96929F689B0200f435f53dA42bF490` | `0xe9185F0c5F296Ed1797AaE4238D26CCaBEadb86C` | Tokenized money market fund |
| USYC Entitlements | `0xb69ecb156Dc0028198028c501340d5367845ca72` | `0xcc205224862c7641930c87679e98999d23c26113` | Allowlist controls |
| USYC Teller | `0x51A8CE47dC08ba5CD19c7aa84EA6fD6664f60f9b` | `0x9fdF14c5B14173D74C08Af27AebFf39240dC105A` | Mint/redeem USYC ↔ USDC |
| CCTP TokenMessengerV2 (domain 26) | `0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d` | `0x8FE6B999Dc680CcFDD5Bf7EB0974218be2542DAA` | See CCTP caveat below |
| CCTP MessageTransmitterV2 | `0x81D40F21F12A8F0E3252Bccb954D722d4c464B64` | `0xE737e5cEBEEBa77EFE34D4aa090756590b1CE275` | |
| CCTP TokenMinterV2 | `0xfd78EE919681417d192449715b2594ab58f5D002` | `0xb43db544E2c27092c107639Ad201b3dEfAbcF192` | |
| CCTP MessageV2 | `0xec546b6B005471ECf012e5aF77FBeC07e0FD8f78` | `0xbaC0179bB358A8936169a63408C8481D582390C4` | |
| Gateway Wallet | `0x77777777Dcc4d5A8B6E418Fd04D8997ef11000eE` | `0x0077777d7EBA4688BDeF3E311b846F25870A19B9` | Chain-abstracted USDC |
| Gateway Minter | `0x2222222d7164433c4C09B0b0D809a9b52C04C205` | `0x0022222ABE238Cc2C7Bb1f21003F0a260052475B` | |
| FxEscrow (StableFX) | `0xe2E5F173576B513d994073CCbDaCBE027d43DFe6` | `0x867650F5eAe8df91445971f14d89fd84F0C9a9f8` | Stablecoin swap escrow |
| Memo | `0x5294E9927c3306DcBaDb03fe70b92e01cCede505` | same | Attaches memo metadata to calls |
| Multicall3From | `0x522fAf9A91c41c443c66765030741e4AaCe147D0` | same | Preserves `msg.sender` across subcalls |
| CREATE2 Factory (Arachnid) | `0x4e59b44847b379578588920cA78FbF26c0B4956C` | same | Standard deterministic deployer |
| Multicall3 | `0xcA11bde05977b3631167028862bE2a173976CA11` | same | Standard, same address as most EVM chains |
| Permit2 | `0x000000000022D473030F116dDEE9F6B43aC78BA3` | same | Standard, required for StableFX |

**CCTP caveat:** the contracts above are CCTP **V2**. Arc DevKit's `CCTPBridge` targets the V2 `depositForBurn` signature, but this has **not been validated against a live Arc CCTP V2 contract**. There is also an open, unresolved public report (as of 2026-09-18) that Circle's public Iris attestation API does not return attestations for Arc Testnet's domain 26: [circlefin/evm-cctp-contracts#110](https://github.com/circlefin/evm-cctp-contracts/issues/110). Test on testnet with small amounts and verify attestation retrieval before relying on this in production.

## Accessing this from code

```python
from arc_devkit.networks import get_network

mainnet = get_network("mainnet")
print(mainnet.chain_id, mainnet.rpc_url, mainnet.explorer_url)
print(mainnet.contracts.usdc, mainnet.contracts.cctp_token_messenger)
```

Or via the CLI:

```bash
arcdevkit network show mainnet
arcdevkit network check-mainnet   # dry-run: confirms nothing is a placeholder
```
