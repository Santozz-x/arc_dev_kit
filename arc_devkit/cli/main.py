"""Arc DevKit CLI entry point — built with Typer."""

import typer
from rich.console import Console
from rich.panel import Panel

from arc_devkit import __version__
from arc_devkit.cli.commands import agent, bridge, copilot, debug, fees, network, oracle, privacy
from arc_devkit.cli.commands import mcp as mcp_cmd
from arc_devkit.cli.flat import config_app, portfolio_app

# Main Typer application
app = typer.Typer(
    name="arcdevkit",
    help="[bold cyan]Arc DevKit[/bold cyan] — Developer tools for the Arc blockchain.",
    add_completion=True,
    rich_markup_mode="rich",
    no_args_is_help=False,
)

# Register subcommand groups
app.add_typer(copilot.app, name="copilot", help="AI assistant for Arc development.")
app.add_typer(agent.app, name="agent", help="Wallet and agent management.")
app.add_typer(debug.app, name="debug", help="Transaction analysis and debugging.")
app.add_typer(config_app, name="config", help="Manage Arc DevKit settings via .env.")
app.add_typer(portfolio_app, name="portfolio", help="Wallet portfolio analysis on Arc.")
app.add_typer(
    network.app, name="network", help="Arc network profiles (testnet/mainnet) and contracts."
)
app.add_typer(fees.app, name="fees", help="Fee quotes for transfers on Arc.")
app.add_typer(bridge.app, name="bridge", help="Cross-chain USDC bridge (CCTP) for Arc.")
app.add_typer(mcp_cmd.app, name="mcp", help="Arc DevKit MCP server.")
app.add_typer(oracle.app, name="oracle", help="Chainlink-compatible price feed queries.")
app.add_typer(privacy.app, name="privacy", help="Experimental privacy primitives (view-keys).")

console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Display the installed version."),
) -> None:
    """Arc DevKit — Developer tools for the Arc blockchain."""
    if version:
        console.print(f"[bold]Arc DevKit[/bold] v{__version__}")
        raise typer.Exit()

    # Show banner when no subcommand is invoked
    if ctx.invoked_subcommand is None:
        console.print(
            Panel.fit(
                f"[bold cyan]Arc DevKit[/bold cyan] [dim]v{__version__}[/dim]\n\n"
                "  [white]Developer tools for the Arc blockchain[/white]\n"
                "  [dim]EVM · USDC as gas · Malachite (<1s)[/dim]\n\n"
                "  Use [bold]arcdevkit --help[/bold] to see available commands.",
                border_style="cyan",
                padding=(1, 3),
            )
        )


@app.command()
def init() -> None:
    """Interactive wizard to create your .env from scratch."""
    from arc_devkit.cli.flat import init as _run_init

    _run_init()


@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of records to display."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """List recent CLI operations saved in ~/.arc_devkit/history.json."""
    from arc_devkit.cli.flat import history as _run_history

    _run_history(limit=limit, json_output=json_output)


@app.command()
def codegen(
    topic: str = typer.Argument(..., help="Describe what the script should do."),
    save: bool = typer.Option(True, "--save/--no-save", help="Save to generated/<timestamp>.py"),
    output_dir: str = typer.Option(".", "--out", "-o", help="Output directory (default: current)."),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable debug logs."),
) -> None:
    """Generate a Python script for Arc from a natural language description."""
    from arc_devkit.cli.flat import codegen as _run_codegen

    _run_codegen(topic=topic, save=save, output_dir=output_dir, verbose=verbose)


@app.command()
def status() -> None:
    """Check the connection to the active Arc network and display network information."""
    from arc_devkit.config import settings
    from arc_devkit.core.connection import check_connection, get_web3

    network_label = f"Arc {settings.arc_network.capitalize()}"
    console.print(f"\n[bold]Checking {network_label} connection...[/bold]\n")

    if not check_connection():
        console.print("[red]✗[/red] Could not connect to Arc.")
        console.print("  Check that [bold]ARC_RPC_URL[/bold] is configured correctly.")
        raise typer.Exit(1)

    w3 = get_web3()
    console.print(f"[green]✓[/green] Connected to {network_label}!\n")
    console.print(f"  Current block:  [bold]#{w3.eth.block_number}[/bold]")
    console.print(f"  Chain ID:       [bold]{w3.eth.chain_id}[/bold]")
    console.print(f"  Gas Price:      [bold]{w3.from_wei(w3.eth.gas_price, 'gwei')} gwei[/bold]")
    if settings.arc_network == "mainnet":
        console.print("\n  [bold red]⚠ Real funds — this is Arc Mainnet.[/bold red]")
    console.print()


@app.command()
def doctor() -> None:
    """Quick health check for the active Arc network — RPC, chain ID, USDC contract, explorer."""
    from arc_devkit.cli.doctor import run_doctor

    run_doctor(console)
