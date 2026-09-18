"""Shared implementation for `arc doctor` / `arcdevkit doctor` — network health check."""

import typer
from rich.console import Console


def run_doctor(console: Console) -> None:
    """Print a health-check report for the active Arc network and exit(1) if not ready."""
    from arc_devkit.config import settings
    from arc_devkit.health import run_health_check

    console.print("\n[bold]Arc DevKit Doctor[/bold]\n")

    profile = settings.network
    with console.status(f"Checking Arc {profile.name.capitalize()}...", spinner="dots"):
        report = run_health_check(profile)

    is_mainnet = profile.name == "mainnet"
    accent = "red" if is_mainnet else "cyan"

    console.print(f"Network:       [bold {accent}]Arc {profile.name.capitalize()}[/bold {accent}]")
    console.print(f"RPC:           {_mark(report.rpc_ok)} {report.rpc_url or '[dim]not set[/dim]'}")
    if report.rpc_error:
        console.print(f"               [red]{report.rpc_error}[/red]")
    console.print(
        f"Chain ID:      {_mark(report.chain_id_match)} "
        f"expected {report.expected_chain_id}, RPC reports {report.rpc_chain_id}"
    )
    if report.latest_block is not None:
        console.print(f"Latest block:  [bold]{report.latest_block}[/bold]")
    if report.latency_ms is not None:
        console.print(f"Latency:       [bold]{report.latency_ms} ms[/bold]")
    console.print(f"USDC contract: {_mark(report.usdc_contract_ok)}")
    console.print(
        f"Explorer:      {_mark(report.explorer_configured)} {profile.explorer_url or ''}"
    )

    console.print()
    if report.ready:
        console.print("[bold green]Status: READY[/bold green]\n")
    else:
        console.print("[bold yellow]Status: NOT READY[/bold yellow]\n")
        raise typer.Exit(1)


def _mark(ok: bool) -> str:
    return "[green]OK[/green]" if ok else "[yellow]FAIL[/yellow]"
