"""CLI commands for the CCTP cross-chain USDC bridge."""

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Cross-chain USDC bridge (CCTP) for Arc.")
console = Console()


def _print_transfer(transfer) -> None:
    tabela = Table(
        title="Bridge Transfer",
        show_header=True,
        header_style="bold cyan",
        border_style="cyan",
    )
    tabela.add_column("Field", style="bold", min_width=16)
    tabela.add_column("Value")

    tabela.add_row("ID", transfer.id)
    tabela.add_row("Status", transfer.status.value)
    tabela.add_row("From", transfer.sender)
    tabela.add_row("To", transfer.recipient)
    tabela.add_row("Amount", f"{transfer.amount_usdc} USDC")
    if transfer.burn_tx_hash:
        tabela.add_row("Burn TX", transfer.burn_tx_hash)
    if transfer.mint_tx_hash:
        tabela.add_row("Mint TX", transfer.mint_tx_hash)
    if transfer.error:
        tabela.add_row("Error", f"[red]{transfer.error}[/red]")

    console.print(tabela)


@app.command()
def send(
    to: str = typer.Argument(..., help="Recipient address on the destination chain."),
    amount: float = typer.Argument(..., help="Amount of USDC to bridge."),
    dest_domain: int = typer.Option(
        ..., "--dest-domain", help="CCTP destination domain id (Circle-assigned)."
    ),
    dest_chain_id: int = typer.Option(
        ..., "--dest-chain-id", help="EVM chain id of the destination chain."
    ),
    key: str = typer.Option("", "--key", help="Private key (overrides ARC_PRIVATE_KEY)."),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Skip the mainnet confirmation prompt (for scripts/automation)."
    ),
) -> None:
    """
    Burn USDC on Arc to start a CCTP cross-chain transfer.

    Uses the CCTP TokenMessengerV2 contract for the active network (see
    `arcdevkit network show <testnet|mainnet>`). NOT VALIDATED against a live
    Arc CCTP contract from this SDK yet — test on testnet with small amounts
    first (see arc_devkit/bridge/cctp.py module docstring).

    Example:
      arcdevkit bridge send 0xDest... 10.0 --dest-domain 0 --dest-chain-id 1
    """
    from decimal import Decimal

    from arc_devkit.bridge.cctp import CCTPBridge
    from arc_devkit.config import settings
    from arc_devkit.core.connection import get_web3

    private_key = key or settings.arc_private_key

    if settings.arc_network == "mainnet":
        console.print("\n[bold red]Network: ARC MAINNET[/bold red]")
        console.print(
            "[bold red]WARNING: This bridges real funds cross-chain (hard to reverse).[/bold red]"
        )
        console.print(f"  Sending {amount} USDC to {to} (destination domain {dest_domain})\n")
        if not yes and not typer.confirm("Burn USDC on Arc Mainnet to start this transfer?"):
            console.print("[yellow]Aborted — no transaction sent.[/yellow]")
            raise typer.Exit(1)
    if not private_key:
        console.print("\n[red]✗ Error:[/red] No private key configured.\n")
        raise typer.Exit(1)

    try:
        bridge = CCTPBridge(w3=get_web3(), network=settings.arc_network)
    except ValueError as exc:
        console.print(f"\n[red]✗ Error:[/red] {exc}\n")
        raise typer.Exit(1) from exc

    with console.status("[bold]Burning USDC on Arc...[/bold]", spinner="dots"):
        transfer = bridge.start_transfer(
            amount_usdc=Decimal(str(amount)),
            recipient=to,
            destination_domain=dest_domain,
            dest_chain_id=dest_chain_id,
            private_key=private_key,
        )

    _print_transfer(transfer)


@app.command()
def status(transfer_id: str = typer.Argument(..., help="Bridge transfer id.")) -> None:
    """Show the status of a bridge transfer."""
    from arc_devkit.bridge.store import load_transfer

    transfer = load_transfer(transfer_id)
    if transfer is None:
        console.print(f"\n[red]✗ Error:[/red] No transfer found with id {transfer_id}.\n")
        raise typer.Exit(1)

    _print_transfer(transfer)


@app.command()
def resume(
    transfer_id: str = typer.Argument(..., help="Bridge transfer id."),
    dest_rpc: str = typer.Option(
        "", "--dest-rpc", help="Destination chain RPC URL (needed to mint)."
    ),
    message_transmitter: str = typer.Option(
        "",
        "--message-transmitter",
        help="MessageTransmitter address on the destination chain (needed to mint).",
    ),
    key: str = typer.Option("", "--key", help="Private key (overrides ARC_PRIVATE_KEY)."),
) -> None:
    """
    Resume a bridge transfer from its last known status (error recovery).

    Examples:
      arcdevkit bridge resume <id>
      arcdevkit bridge resume <id> --dest-rpc https://... --message-transmitter 0x...
    """
    from web3 import Web3

    from arc_devkit.bridge.cctp import CCTPBridge
    from arc_devkit.bridge.store import load_transfer
    from arc_devkit.config import settings
    from arc_devkit.core.connection import get_web3

    transfer = load_transfer(transfer_id)
    if transfer is None:
        console.print(f"\n[red]✗ Error:[/red] No transfer found with id {transfer_id}.\n")
        raise typer.Exit(1)

    private_key = key or settings.arc_private_key
    dest_w3 = Web3(Web3.HTTPProvider(dest_rpc)) if dest_rpc else None

    try:
        bridge = CCTPBridge(w3=get_web3(), network=settings.arc_network)
    except ValueError as exc:
        console.print(f"\n[red]✗ Error:[/red] {exc}\n")
        raise typer.Exit(1) from exc

    with console.status("[bold]Resuming transfer...[/bold]", spinner="dots"):
        transfer = bridge.resume(
            transfer,
            dest_w3=dest_w3,
            message_transmitter_address=message_transmitter or None,
            private_key=private_key,
        )

    _print_transfer(transfer)
