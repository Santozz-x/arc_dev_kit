"""CLI commands for the Tx Debugger."""

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="Transaction analysis and debugging for Arc.")
console = Console()


@app.command()
def tx(
    tx_hash: str = typer.Argument(..., help="Transaction hash to analyze (0x...)."),
    json_output: bool = typer.Option(False, "--json", help="Display result as raw JSON."),
) -> None:
    """
    Analyze an Arc transaction and display full diagnosis.

    Examples:
      arcdevkit debug tx 0xabc123...
      arcdevkit debug tx 0xabc123... --json
    """
    import json

    from arc_devkit.debugger.tx_analyzer import TxAnalyzer

    analyzer = TxAnalyzer()

    with console.status(
        f"[bold yellow]Analyzing transaction {tx_hash[:16]}...[/bold yellow]",
        spinner="dots",
    ):
        resultado = analyzer.analyze(tx_hash)

    # Raw JSON output
    if json_output:
        console.print_json(json.dumps(resultado, default=str))
        return

    # Summary table
    status = resultado.get("status", "unknown")
    cor_status = "green" if status == "success" else "red"
    icone = "✓" if status == "success" else "✗"

    tabela = Table(
        title=f"Transaction [dim]{tx_hash[:20]}...[/dim]",
        show_header=True,
        header_style="bold yellow",
        border_style="yellow",
    )
    tabela.add_column("Field", style="bold", min_width=14)
    tabela.add_column("Value")

    tabela.add_row("Hash", f"{tx_hash[:20]}...")
    tabela.add_row("Status", f"[{cor_status}]{icone} {status}[/{cor_status}]")
    tabela.add_row("Gas Cost", f"{resultado.get('custo_usdc', 'N/A')} USDC")

    if resultado.get("error"):
        tabela.add_row("Error", f"[red]{resultado['error']}[/red]")

    console.print(tabela)

    # Natural language analysis (if available)
    if resultado.get("summary"):
        console.print(
            Panel(
                Markdown(resultado["summary"]),
                title="[bold yellow]Analysis[/bold yellow]",
                border_style="yellow",
                padding=(1, 2),
            )
        )


@app.command()
def batch(
    hashes_file: str = typer.Argument(
        ..., help="Text file with one tx hash per line (or JSON array)."
    ),
    abi_path: str = typer.Option(
        "", "--abi", "-a", help="Path to ABI JSON file applied to all transactions."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Analyze multiple transactions from a file (one hash per line or JSON array).

    Examples:
      arcdevkit debug batch hashes.txt
      arcdevkit debug batch hashes.txt --abi MyContract.json --json
    """
    from arc_devkit.cli.flat import debug_batch as _run_batch

    _run_batch(hashes_file=hashes_file, abi_path=abi_path, json_output=json_output, verbose=False)


@app.command()
def estimate(
    to: str = typer.Argument(..., help="Recipient EVM address."),
    amount: float = typer.Argument(..., help="Amount to transfer (in USDC)."),
    from_address: str = typer.Option("", "--from", help="Sender address (optional)."),
) -> None:
    """
    Estimate the gas cost for a transfer on Arc.

    Examples:
      arcdevkit debug estimate 0xDest... 10.5
      arcdevkit debug estimate 0xDest... 10.5 --from 0xSender...
    """
    from arc_devkit.core.gas import estimate_transfer

    with console.status("[bold]Estimating gas cost...[/bold]", spinner="dots"):
        est = estimate_transfer(to, amount, from_address or None)

    tabela = Table(
        title="Gas Estimate",
        show_header=True,
        header_style="bold blue",
        border_style="blue",
    )
    tabela.add_column("Field", style="bold", min_width=16)
    tabela.add_column("Value")

    tabela.add_row("Recipient", est["to"])
    tabela.add_row("Transfer", f"{amount} USDC")
    tabela.add_row("Gas Limit", str(est["gas_limit"]))
    tabela.add_row("Gas Price", f"{est['gas_price_gwei']} gwei")
    tabela.add_row("Gas Cost", f"[bold green]{est['custo_usdc']}[/bold green] USDC")

    console.print(tabela)


@app.command()
def trace(
    tx_hash: str = typer.Argument(..., help="Transaction hash to trace (0x...)."),
    tracer: str = typer.Option("callTracer", "--tracer", help="Trace type (node-dependent)."),
) -> None:
    """
    Fetch an internal-call trace via debug_traceTransaction, if the RPC supports it.

    Most public RPC endpoints (including Circle's default Arc RPC, on both
    mainnet and testnet) disable the debug_* namespace — this fails with a clear message rather than a
    generic RPC error.

    Example:
      arcdevkit debug trace 0xabc123...
    """
    import json

    from arc_devkit.debugger.tx_analyzer import TxAnalyzer

    with console.status(
        f"[bold yellow]Tracing transaction {tx_hash[:16]}...[/bold yellow]", spinner="dots"
    ):
        result = TxAnalyzer().trace_transaction(tx_hash, tracer=tracer)

    if not result["supported"]:
        console.print(f"\n[red]✗ Not available:[/red] {result['error']}\n")
        raise typer.Exit(1)

    console.print_json(json.dumps(result["trace"], default=str))


@app.command()
def compare(
    hash1: str = typer.Argument(..., help="First transaction hash."),
    hash2: str = typer.Argument(..., help="Second transaction hash."),
) -> None:
    """
    Analyze two transactions side by side and highlight the differences.

    Example:
      arcdevkit debug compare 0xabc123... 0xdef456...
    """
    from arc_devkit.debugger.tx_analyzer import TxAnalyzer

    analyzer = TxAnalyzer()
    with console.status(
        "[bold yellow]Analyzing both transactions...[/bold yellow]", spinner="dots"
    ):
        r1 = analyzer.analyze(hash1, use_ai=False)
        r2 = analyzer.analyze(hash2, use_ai=False)

    tabela = Table(
        title="Transaction Comparison",
        show_header=True,
        header_style="bold yellow",
        border_style="yellow",
    )
    tabela.add_column("Field", style="bold", min_width=16)
    tabela.add_column(f"{hash1[:14]}...")
    tabela.add_column(f"{hash2[:14]}...")

    def _row(label: str, v1, v2) -> None:
        diff = v1 != v2
        style = "yellow" if diff else "dim"
        marker = " ⚠" if diff else ""
        tabela.add_row(
            label, f"[{style}]{v1}{marker}[/{style}]", f"[{style}]{v2}{marker}[/{style}]"
        )

    _row("Status", r1["status"], r2["status"])
    _row("Cost (USDC)", r1["custo_usdc"], r2["custo_usdc"])
    _row("Revert reason", r1.get("revert_reason") or "—", r2.get("revert_reason") or "—")

    raw1, raw2 = r1.get("raw_data") or {}, r2.get("raw_data") or {}
    _row("Gas used", raw1.get("gas_used", "N/A"), raw2.get("gas_used", "N/A"))
    _row("Block", raw1.get("block", "N/A"), raw2.get("block", "N/A"))

    console.print(tabela)
