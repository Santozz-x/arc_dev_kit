"""CLI commands to inspect Arc network profiles and contract addresses."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="Arc network profiles (testnet/mainnet) and contract addresses.")
console = Console()


def _dim_or(value: str | None) -> str:
    return value if value else "[dim]not available yet[/dim]"


@app.command(name="list")
def list_networks() -> None:
    """List all known Arc network profiles."""
    from arc_devkit.config import settings

    tabela = Table(
        title="Arc Networks",
        show_header=True,
        header_style="bold magenta",
        border_style="magenta",
    )
    tabela.add_column("Network", style="bold", min_width=10)
    tabela.add_column("Chain ID")
    tabela.add_column("RPC URL")
    tabela.add_column("Explorer")
    tabela.add_column("Status")

    from arc_devkit.networks import NETWORKS

    for name, profile in NETWORKS.items():
        rotulo = f"[cyan]{name}[/cyan]"
        if name == settings.arc_network:
            rotulo += " [bold green](active)[/bold green]"
        configurada = profile.rpc_url is not None and profile.chain_id is not None
        status = "[green]✓ configured[/green]" if configurada else "[yellow]○ placeholder[/yellow]"
        tabela.add_row(
            rotulo,
            str(profile.chain_id) if profile.chain_id else _dim_or(None),
            _dim_or(profile.rpc_url),
            _dim_or(profile.explorer_url),
            status,
        )

    console.print(tabela)


@app.command(name="show")
def show_network(
    name: str = typer.Argument(..., help="Network name (e.g. testnet, mainnet)."),
) -> None:
    """Show details for a single Arc network profile, including contract addresses."""
    from arc_devkit.networks import get_network

    try:
        profile = get_network(name)
    except ValueError as exc:
        console.print(f"\n[red]✗ Error:[/red] {exc}\n")
        raise typer.Exit(1) from exc

    contracts = profile.contracts
    console.print(
        Panel(
            f"[bold]Chain ID:[/bold]      {_dim_or(str(profile.chain_id) if profile.chain_id else None)}\n"
            f"[bold]RPC URL:[/bold]       {_dim_or(profile.rpc_url)}\n"
            f"[bold]WS RPC URL:[/bold]    {_dim_or(profile.ws_rpc_url)}\n"
            f"[bold]Explorer:[/bold]      {_dim_or(profile.explorer_url)}\n"
            f"[bold]Native gas:[/bold]    {profile.native_currency_symbol} "
            f"({profile.native_currency_decimals} decimals)\n\n"
            f"[bold]Contracts[/bold]\n"
            f"  USDC (ERC-20, 6 dec):        {_dim_or(contracts.usdc)}\n"
            f"  EURC:                        {_dim_or(contracts.eurc)}\n"
            f"  CCTP Token Messenger (V2):   {_dim_or(contracts.cctp_token_messenger)}\n"
            f"  CCTP Message Transmitter:    {_dim_or(contracts.cctp_message_transmitter)}\n"
            f"  CCTP Token Minter:           {_dim_or(contracts.cctp_token_minter)}\n"
            f"  CCTP domain:                 {_dim_or(str(contracts.cctp_domain) if contracts.cctp_domain is not None else None)}\n"
            f"  Gateway Wallet:              {_dim_or(contracts.gateway_wallet)}\n"
            f"  Gateway Minter:              {_dim_or(contracts.gateway_minter)}\n"
            f"  Multicall3:                  {_dim_or(contracts.multicall3)}\n"
            f"  Permit2:                     {_dim_or(contracts.permit2)}",
            title=f"[bold cyan]Arc Network — {profile.name}[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )


@app.command(name="check-mainnet")
def check_mainnet() -> None:
    """
    Mainnet-readiness dry-run: checks that all required network config is filled in.

    Validates arc_devkit.networks.NETWORKS["mainnet"] (chain ID, RPC URL,
    explorer, contract addresses) without switching ARC_NETWORK — see
    MAINNET_CHECKLIST.md for the full pre-launch checklist. Exits non-zero
    if anything required is still a placeholder.
    """
    from arc_devkit.networks import get_network

    profile = get_network("mainnet")
    checks = [
        ("Chain ID", profile.chain_id is not None),
        ("RPC URL", profile.rpc_url is not None),
        ("Explorer URL", profile.explorer_url is not None),
        ("USDC contract", profile.contracts.usdc is not None),
        ("EURC contract", profile.contracts.eurc is not None),
        ("CCTP Token Messenger", profile.contracts.cctp_token_messenger is not None),
        ("CCTP Message Transmitter", profile.contracts.cctp_message_transmitter is not None),
        ("Gateway Wallet", profile.contracts.gateway_wallet is not None),
        ("Gateway Minter", profile.contracts.gateway_minter is not None),
    ]

    tabela = Table(
        title="Mainnet Readiness Check",
        show_header=True,
        header_style="bold magenta",
        border_style="magenta",
    )
    tabela.add_column("Check", style="bold", min_width=22)
    tabela.add_column("Status")

    all_ready = True
    for label, ok in checks:
        tabela.add_row(label, "[green]✓ configured[/green]" if ok else "[yellow]○ missing[/yellow]")
        all_ready = all_ready and ok

    console.print(tabela)

    if all_ready:
        console.print("\n[bold green]✓ Ready — all mainnet config is filled in.[/bold green]\n")
    else:
        console.print(
            "\n[bold yellow]○ Not ready[/bold yellow] — fill in the missing fields in "
            'arc_devkit/networks.py NETWORKS["mainnet"] before switching ARC_NETWORK=mainnet. '
            "See MAINNET_CHECKLIST.md for the full pre-launch checklist.\n"
        )
        raise typer.Exit(1)
