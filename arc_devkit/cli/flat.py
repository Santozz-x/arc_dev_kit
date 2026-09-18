"""
Arc DevKit flat CLI — direct commands without subgroups.

Registered as entry point `arc` in pyproject.toml.

Usage:
    arc status
    arc ask "how do I create a wallet on Arc?"
    arc balance 0xAbC...
    arc gas 0xDest... 10.5
    arc debug 0xTxHash...
    arc codegen "create an agent that monitors balance"
    arc config get ARC_RPC_URL
    arc config set LOG_LEVEL DEBUG
    arc history
    arc init
"""

import json as _json
import logging
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

app = typer.Typer(
    name="arc",
    help="[bold cyan]Arc DevKit[/bold cyan] — Direct CLI for the Arc blockchain.",
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)
console = Console()

_HISTORY_FILE = Path.home() / ".arc_devkit" / "history.json"
_ENV_FILE = Path(".env")


def _load_abi_optional(abi_path: str) -> list | None:
    """Load ABI from file path. Returns None if path is empty or file not found."""
    if not abi_path:
        return None
    path = Path(abi_path)
    if not path.exists():
        console.print(f"[red]ABI file not found:[/red] {abi_path}")
        raise typer.Exit(1)
    try:
        from arc_devkit.contracts.loader import load_abi

        return load_abi(path)
    except Exception as exc:
        console.print(f"[red]Failed to load ABI:[/red] {exc}")
        raise typer.Exit(1)


def _validate_address(address: str) -> str:
    """Validate and return the EVM address in checksum format. Prints a friendly error if invalid."""
    from web3 import Web3

    try:
        return Web3.to_checksum_address(address)
    except Exception:
        console.print(f"[red]Invalid address:[/red] {address!r}")
        console.print("[dim]Must be a valid EVM address (0x + 40 hex chars)[/dim]")
        raise typer.Exit(1)


def _save_history(entry: dict) -> None:
    """Save an entry to history at ~/.arc_devkit/history.json."""
    _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    history: list[dict] = []
    if _HISTORY_FILE.exists():
        try:
            history = _json.loads(_HISTORY_FILE.read_text())
        except Exception:
            history = []
    history.append({**entry, "timestamp": datetime.now().isoformat()})
    # keep only the last 100 records
    history = history[-100:]
    _HISTORY_FILE.write_text(_json.dumps(history, indent=2, ensure_ascii=False))


def _set_verbose(verbose: bool) -> None:
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("arc_devkit").setLevel(logging.DEBUG)


@app.command()
def status(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable debug logs."),
) -> None:
    """Check the connection to the active Arc network and display network info."""
    _set_verbose(verbose)
    from arc_devkit.config import settings
    from arc_devkit.core.connection import check_connection, get_web3

    network_label = f"Arc {settings.arc_network.capitalize()}"

    with console.status(f"Connecting to {network_label}...", spinner="dots"):
        ok = check_connection()

    if not ok:
        if json_output:
            console.print_json(_json.dumps({"connected": False, "network": settings.arc_network}))
        else:
            console.print("[red]✗ Connection failed. Check ARC_RPC_URL in your .env[/red]")
        raise typer.Exit(1)

    w3 = get_web3()
    data = {
        "connected": True,
        "network": network_label,
        "chain_id": w3.eth.chain_id,
        "block_number": w3.eth.block_number,
        "gas_price_gwei": str(w3.from_wei(w3.eth.gas_price, "gwei")),
    }

    if json_output:
        console.print_json(_json.dumps(data))
        return

    is_mainnet = settings.arc_network == "mainnet"
    accent = "red" if is_mainnet else "cyan"

    tabela = Table(show_header=False, border_style=accent, padding=(0, 1))
    tabela.add_column("field", style="dim")
    tabela.add_column("value", style="bold")
    tabela.add_row("Status", "[green]✓ connected[/green]")
    tabela.add_row("Network", str(data["network"]))
    tabela.add_row("Chain ID", str(data["chain_id"]))
    tabela.add_row("Current block", f"#{data['block_number']}")
    tabela.add_row("Gas price", f"{data['gas_price_gwei']} gwei")
    if is_mainnet:
        tabela.add_row("", "[bold red]⚠ Real funds — mainnet[/bold red]")

    console.print(
        Panel(tabela, title=f"[bold {accent}]{network_label}[/bold {accent}]", border_style=accent)
    )


@app.command()
def doctor() -> None:
    """Quick health check for the active Arc network — RPC, chain ID, USDC contract, explorer."""
    from arc_devkit.cli.doctor import run_doctor

    run_doctor(console)


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question for DevCopilot."),
    raw: bool = typer.Option(False, "--raw", help="Print plain text without Markdown rendering."),
    stream: bool = typer.Option(False, "--stream", "-s", help="Stream response token by token."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable debug logs."),
) -> None:
    """Query DevCopilot — AI assistant specialized in Arc blockchain development."""
    _set_verbose(verbose)
    from arc_devkit.copilot.agent import DevCopilot

    copilot = DevCopilot()

    if stream:
        console.print("[dim]DevCopilot (streaming)...[/dim]")
        partes = []
        for chunk in copilot.ask_stream(question):
            console.print(chunk, end="", highlight=False)
            partes.append(chunk)
        console.print()
        answer = "".join(partes)
    else:
        with console.status("DevCopilot thinking...", spinner="dots"):
            answer = copilot.ask(question)

    if json_output:
        console.print_json(_json.dumps({"response": answer, "model": copilot.model}))
        return
    if raw:
        console.print(answer)
        return
    console.print(
        Panel(
            Markdown(answer),
            title="[bold cyan]DevCopilot[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )


@app.command()
def balance(
    address: str = typer.Argument(..., help="EVM wallet address (0x...)."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable debug logs."),
) -> None:
    """Display the native balance and nonce of an Arc wallet."""
    _set_verbose(verbose)
    from arc_devkit.core.connection import get_web3

    checksum = _validate_address(address)
    w3 = get_web3()
    from eth_typing import ChecksumAddress as _CA

    saldo = Decimal(str(w3.from_wei(w3.eth.get_balance(cast(_CA, checksum)), "ether")))
    nonce = w3.eth.get_transaction_count(cast(_CA, checksum))

    data = {"address": checksum, "balance_arc": str(saldo), "nonce": nonce}

    if json_output:
        console.print_json(_json.dumps(data))
        return

    tabela = Table(show_header=False, border_style="green", padding=(0, 1))
    tabela.add_column("field", style="dim")
    tabela.add_column("value", style="bold")
    tabela.add_row("Address", checksum)
    tabela.add_row("Native balance", f"[green]{saldo:.6f}[/green] ARC")
    tabela.add_row("Nonce (txs sent)", str(nonce))

    console.print(Panel(tabela, title="[bold green]Balance[/bold green]", border_style="green"))


@app.command()
def gas(
    to: str = typer.Argument(..., help="Recipient address (0x...)."),
    amount: float = typer.Argument(..., help="Amount to transfer (USDC)."),
    from_address: str = typer.Option("", "--from", "-f", help="Sender address (optional)."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable debug logs."),
) -> None:
    """Estimate the gas cost for a transfer on Arc."""
    _set_verbose(verbose)
    _validate_address(to)
    if from_address:
        _validate_address(from_address)

    from arc_devkit.core.gas import estimate_transfer

    with console.status("Querying RPC...", spinner="dots"):
        est = estimate_transfer(to, amount, from_address or None)

    if json_output:
        console.print_json(_json.dumps(est))
        return

    tabela = Table(show_header=False, border_style="yellow", padding=(0, 1))
    tabela.add_column("field", style="dim")
    tabela.add_column("value", style="bold")
    tabela.add_row("Recipient", est["to"])
    tabela.add_row("Transfer", f"{amount} USDC")
    tabela.add_row("Gas limit", str(est["gas_limit"]))
    tabela.add_row("Gas price", f"{est['gas_price_gwei']} gwei")
    tabela.add_row("Gas cost", f"[bold yellow]{est['custo_usdc']}[/bold yellow] USDC")

    console.print(
        Panel(tabela, title="[bold yellow]Gas Estimate[/bold yellow]", border_style="yellow")
    )


@app.command()
def debug(
    tx_hash: str = typer.Argument(..., help="Transaction hash (0x...)."),
    abi_path: str = typer.Option(
        "", "--abi", "-a", help="Path to ABI JSON file for input/error decoding."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable debug logs."),
) -> None:
    """Analyze an Arc transaction with AI diagnosis and optional ABI decoding."""
    _set_verbose(verbose)
    from arc_devkit.debugger.tx_analyzer import TxAnalyzer

    abi = _load_abi_optional(abi_path)

    with console.status(f"Analyzing {tx_hash[:16]}...", spinner="dots"):
        resultado = TxAnalyzer().analyze(tx_hash, abi=abi)

    _save_history({"type": "debug", "tx_hash": tx_hash, "result": resultado})

    if json_output:
        console.print_json(_json.dumps(resultado))
        return

    status_str = resultado.get("status", "unknown")
    cor = "green" if status_str == "success" else "red"
    icone = "✓" if status_str == "success" else "✗"

    tabela = Table(show_header=False, border_style="magenta", padding=(0, 1))
    tabela.add_column("field", style="dim")
    tabela.add_column("value", style="bold")
    tabela.add_row("Hash", tx_hash[:24] + "...")
    tabela.add_row("Status", f"[{cor}]{icone} {status_str}[/{cor}]")
    tabela.add_row("Gas cost", f"{resultado.get('custo_usdc', 'N/A')} USDC")

    if resultado.get("revert_reason"):
        tabela.add_row("Revert reason", f"[red]{resultado['revert_reason']}[/red]")

    if resultado.get("decoded_input"):
        di = resultado["decoded_input"]
        args_str = ", ".join(f"{k}={v}" for k, v in di.get("args", {}).items())
        tabela.add_row("Function called", f"[cyan]{di['function']}({args_str})[/cyan]")

    console.print(
        Panel(tabela, title="[bold magenta]Transaction[/bold magenta]", border_style="magenta")
    )

    if resultado.get("summary"):
        console.print(
            Panel(
                Markdown(resultado["summary"]),
                title="[bold magenta]AI Analysis[/bold magenta]",
                border_style="magenta",
                padding=(1, 2),
            )
        )


@app.command("debug-batch")
def debug_batch(
    hashes_file: str = typer.Argument(
        ..., help="Text file with one tx hash per line (or JSON array)."
    ),
    abi_path: str = typer.Option(
        "", "--abi", "-a", help="Path to ABI JSON file applied to all transactions."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable debug logs."),
) -> None:
    """Analyze multiple transactions from a file (one hash per line or JSON array)."""
    _set_verbose(verbose)

    hashes_path = Path(hashes_file)
    if not hashes_path.exists():
        console.print(f"[red]File not found:[/red] {hashes_file}")
        raise typer.Exit(1)

    raw = hashes_path.read_text().strip()
    if raw.startswith("["):
        try:
            tx_hashes = _json.loads(raw)
        except Exception as exc:
            console.print(f"[red]Invalid JSON:[/red] {exc}")
            raise typer.Exit(1)
    else:
        tx_hashes = [line.strip() for line in raw.splitlines() if line.strip()]

    if not tx_hashes:
        console.print("[red]No transaction hashes found in file.[/red]")
        raise typer.Exit(1)

    abi = _load_abi_optional(abi_path)

    from arc_devkit.debugger.tx_analyzer import TxAnalyzer

    analyzer = TxAnalyzer()

    if json_output:
        # Silent run — no progress display so stdout is clean JSON
        results = analyzer.analyze_batch(tx_hashes, abi=abi)
        _save_history({"type": "debug-batch", "count": len(results), "hashes_file": hashes_file})
        console.print_json(_json.dumps(results))
        return

    from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn

    with Progress(
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing transactions", total=len(tx_hashes))

        def on_progress(current: int, total: int, tx_hash: str) -> None:
            progress.update(task, completed=current - 1, description=f"{tx_hash[:16]}...")

        results = analyzer.analyze_batch(tx_hashes, abi=abi, on_progress=on_progress)
        progress.update(task, completed=len(tx_hashes), description="Done")

    _save_history({"type": "debug-batch", "count": len(results), "hashes_file": hashes_file})

    summary_table = Table(
        title=f"Batch Analysis — {len(results)} transactions",
        border_style="magenta",
        show_lines=False,
    )
    summary_table.add_column("Hash", style="dim")
    summary_table.add_column("Status")
    summary_table.add_column("Gas cost (USDC)", justify="right")
    summary_table.add_column("Revert reason")

    for r in results:
        st = r.get("status", "?")
        cor = "green" if st == "success" else "red" if st == "reverted" else "yellow"
        revert = r.get("revert_reason") or ""
        if len(revert) > 40:
            revert = revert[:40] + "..."
        summary_table.add_row(
            (r.get("hash") or "")[:20] + "...",
            f"[{cor}]{st}[/{cor}]",
            r.get("custo_usdc", "0"),
            f"[red]{revert}[/red]" if revert else "[dim]—[/dim]",
        )

    console.print(summary_table)
    ok = sum(1 for r in results if r.get("status") == "success")
    fail = len(results) - ok
    console.print(f"\n[green]✓ {ok} succeeded[/green]  [red]✗ {fail} failed[/red]")


@app.command()
def codegen(
    topic: str = typer.Argument(..., help="Describe what the script should do."),
    save: bool = typer.Option(True, "--save/--no-save", help="Save to generated/<timestamp>.py"),
    output_dir: str = typer.Option(".", "--out", "-o", help="Output directory (default: current)."),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable debug logs."),
) -> None:
    """Generate a Python script for Arc from a natural language description."""
    _set_verbose(verbose)
    from arc_devkit.copilot.agent import DevCopilot

    prompt = (
        f"Gere um script Python COMPLETO e FUNCIONAL usando o pacote `arc-devkit` "
        f"(instalado via `pip install arc-devkit`).\n\n"
        f"## Objetivo\n{topic}\n\n"
        f"## Requisitos\n"
        f"1. Importe exclusivamente de `arc_devkit`\n"
        f"2. Use `rich` para saída formatada\n"
        f"3. Use `Decimal` para valores monetários\n"
        f"4. Inclua `if __name__ == '__main__':` e docstring no topo\n\n"
        f"Responda com: parágrafo curto de explicação + bloco ```python ... ```"
    )

    with console.status("DevCopilot generating code...", spinner="dots"):
        resposta = DevCopilot(max_tokens=8000).ask(prompt)

    match = re.search(r"```python\s*(.*?)```", resposta, re.DOTALL)
    if not match:
        # Fallback: grab everything after ```python even if closing fence is missing
        match = re.search(r"```python\s*(.*)", resposta, re.DOTALL)
    codigo = match.group(1).strip() if match else None
    explicacao = re.sub(r"```python.*?```", "", resposta, flags=re.DOTALL).strip()

    if explicacao:
        console.print(
            Panel(Markdown(explicacao), title="[dim]What the script does[/dim]", border_style="dim")
        )

    if not codigo:
        console.print("[red]Could not extract a code block from the response.[/red]")
        console.print(Markdown(resposta))
        raise typer.Exit(1)

    console.print(
        Panel(
            Syntax(codigo, "python", theme="monokai", line_numbers=True),
            title="[bold green]Generated code[/bold green]",
            border_style="green",
        )
    )

    if save:
        destino = Path(output_dir)
        destino.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = re.sub(r"[^a-z0-9]+", "_", topic.lower())[:40]
        arquivo = destino / f"{ts}_{slug}.py"
        arquivo.write_text(codigo, encoding="utf-8")
        console.print(f"\n[bold green]✓[/bold green] Saved to: [bold]{arquivo}[/bold]")


# ---------------------------------------------------------------------------
# arc config — read and write .env
# ---------------------------------------------------------------------------

config_app = typer.Typer(help="Manage Arc DevKit settings via .env")
app.add_typer(config_app, name="config")


@config_app.command("get")
def config_get(
    key: str = typer.Argument(..., help="Variable name (e.g. ARC_RPC_URL)."),
) -> None:
    """Read a variable from .env."""
    import os

    valor = os.getenv(key)
    if valor is None:
        # Try reading directly from .env file
        if _ENV_FILE.exists():
            for linha in _ENV_FILE.read_text().splitlines():
                if linha.startswith(f"{key}="):
                    valor = linha.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if valor is not None:
        console.print(f"[bold]{key}[/bold]=[cyan]{valor}[/cyan]")
    else:
        console.print(f"[yellow]{key}[/yellow] is not defined")
        raise typer.Exit(1)


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Variable name (e.g. LOG_LEVEL)."),
    value: str = typer.Argument(..., help="New value."),
) -> None:
    """Set or update a variable in .env."""
    linhas: list[str] = []
    encontrou = False

    if _ENV_FILE.exists():
        for linha in _ENV_FILE.read_text().splitlines():
            if linha.startswith(f"{key}="):
                linhas.append(f"{key}={value}")
                encontrou = True
            else:
                linhas.append(linha)

    if not encontrou:
        linhas.append(f"{key}={value}")

    _ENV_FILE.write_text("\n".join(linhas) + "\n")
    console.print(f"[green]✓[/green] {key}={value} saved to [bold]{_ENV_FILE}[/bold]")


@config_app.command("keyring-set")
def config_keyring_set() -> None:
    """
    Store ARC_PRIVATE_KEY in the OS keyring instead of plaintext .env.

    Uses the system Keychain (macOS), Credential Manager (Windows), or
    libsecret (Linux). Once stored, remove ARC_PRIVATE_KEY from your .env —
    the toolkit falls back to the keyring automatically.
    """
    try:
        import keyring
    except ImportError:
        console.print(
            "[red]The 'keyring' package is not installed.[/red]\n"
            "Install it with: [bold]pip install 'arc-devkit[security]'[/bold]"
        )
        raise typer.Exit(1)

    from arc_devkit.config import KEYRING_KEY_NAME, KEYRING_SERVICE

    valor = typer.prompt("Private key (0x...)", hide_input=True)
    if not valor.strip():
        console.print("[red]Empty key — aborted.[/red]")
        raise typer.Exit(1)

    keyring.set_password(KEYRING_SERVICE, KEYRING_KEY_NAME, valor.strip())
    console.print(
        "[green]✓[/green] Private key stored in the OS keyring.\n"
        "[dim]Now remove ARC_PRIVATE_KEY from your .env — the keyring is used as fallback.[/dim]"
    )


@config_app.command("keyring-clear")
def config_keyring_clear() -> None:
    """Remove ARC_PRIVATE_KEY from the OS keyring."""
    try:
        import keyring
    except ImportError:
        console.print("[red]The 'keyring' package is not installed.[/red]")
        raise typer.Exit(1)

    from arc_devkit.config import KEYRING_KEY_NAME, KEYRING_SERVICE

    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_KEY_NAME)
        console.print("[green]✓[/green] Private key removed from the OS keyring.")
    except Exception:
        console.print("[dim]No private key stored in the keyring.[/dim]")


@config_app.command("list")
def config_list() -> None:
    """List all variables defined in .env."""
    if not _ENV_FILE.exists():
        console.print("[yellow].env file not found[/yellow]")
        raise typer.Exit(1)

    tabela = Table(title=".env", show_header=True, header_style="bold cyan", border_style="cyan")
    tabela.add_column("Variable", style="bold")
    tabela.add_column("Value")

    for linha in _ENV_FILE.read_text().splitlines():
        if linha.strip() and not linha.startswith("#") and "=" in linha:
            k, v = linha.split("=", 1)
            # Mask sensitive values
            masked = v if "KEY" not in k.upper() else v[:6] + "***"
            tabela.add_row(k.strip(), masked.strip())

    console.print(tabela)


# ---------------------------------------------------------------------------
# arc wallet — create wallet, check balance
# ---------------------------------------------------------------------------

wallet_app = typer.Typer(help="EVM wallet management for Arc")
app.add_typer(wallet_app, name="wallet")


@wallet_app.command("create")
def wallet_create(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Create a new EVM wallet and display the address and private key."""
    from arc_devkit.core.wallet import create_wallet as _criar

    carteira = _criar()

    if json_output:
        console.print_json(_json.dumps(carteira))
        return

    console.print(
        Panel(
            f"[bold green]✓ New wallet created![/bold green]\n\n"
            f"  [bold]Address:[/bold]\n"
            f"  [cyan]{carteira['address']}[/cyan]\n\n"
            f"  [bold]Private Key:[/bold]\n"
            f"  [dim]{carteira['private_key']}[/dim]\n\n"
            "[bold red]⚠ WARNING:[/bold red] Private key shown only once.\n"
            "Store it securely. Never share or commit to git.",
            title="[bold green]New Arc Wallet[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )


@wallet_app.command("balance")
def wallet_balance(
    address: str = typer.Argument(..., help="EVM address (0x...)."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Display the balance of an Arc wallet."""
    from arc_devkit.core.wallet import get_balance

    checksum = _validate_address(address)
    with console.status("[bold]Fetching balance...[/bold]", spinner="dots"):
        resultado = get_balance(checksum)

    if json_output:
        console.print_json(
            _json.dumps(
                {
                    "address": resultado["address"],
                    "balance_wei": resultado["balance_wei"],
                    "balance_usdc": str(resultado["balance_usdc"]),
                }
            )
        )
        return

    console.print(f"\n  [bold]Wallet:[/bold] [cyan]{resultado['address']}[/cyan]")
    console.print(f"  [bold]Balance:[/bold] [green]{resultado['balance_usdc']}[/green] ARC\n")


# ---------------------------------------------------------------------------
# arc send — payment via PaymentAgent
# ---------------------------------------------------------------------------


@app.command()
def send(
    to: str = typer.Argument(..., help="Recipient EVM address (0x...)."),
    amount: float = typer.Argument(..., help="Amount to transfer."),
    token: str = typer.Option(
        "native", "--token", "-t", help="Token type: 'native' (ARC) or 'usdc' (ERC-20)."
    ),
    broadcast: bool = typer.Option(
        False, "--broadcast", "-b", help="Broadcast transaction (requires ARC_PRIVATE_KEY)."
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip the mainnet confirmation prompt (for scripts/automation).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable debug logs."),
) -> None:
    """Build (and optionally broadcast) a payment transaction on Arc."""
    _set_verbose(verbose)

    import os

    from arc_devkit.config import settings

    private_key = os.getenv("ARC_PRIVATE_KEY", "").strip() or None
    if not private_key:
        console.print("[red]ARC_PRIVATE_KEY not set — cannot sign transactions.[/red]")
        raise typer.Exit(1)

    dest = _validate_address(to)

    if broadcast and settings.arc_network == "mainnet":
        console.print("\n[bold red]Network: ARC MAINNET[/bold red]")
        console.print("[bold red]WARNING: This transaction uses real funds.[/bold red]")
        console.print(f"  Sending {amount} {'ARC' if token == 'native' else 'USDC'} to {dest}\n")
        if not yes and not typer.confirm("Broadcast this transaction on Arc Mainnet?"):
            console.print("[yellow]Aborted — no transaction sent.[/yellow]")
            raise typer.Exit(1)

    from arc_devkit.agents.payment_agent import PaymentAgent

    agent = PaymentAgent(private_key=private_key)

    with console.status("[bold]Preparing transaction...[/bold]", spinner="dots"):
        resultado = agent.execute(
            to=dest, amount_usdc=amount, enviar=broadcast, token=token, wait_receipt=broadcast
        )

    if json_output:
        console.print_json(_json.dumps(resultado))
        return

    status_str = resultado.get("status", "unknown")
    cor = "green" if status_str in ("signed", "confirmed", "sent") else "red"

    tabela = Table(show_header=False, border_style="cyan", padding=(0, 1))
    tabela.add_column("field", style="dim")
    tabela.add_column("value", style="bold")
    tabela.add_row("Status", f"[{cor}]{status_str}[/{cor}]")
    tabela.add_row("Token", token.upper())
    tabela.add_row("From", str(resultado.get("from", "N/A")))
    tabela.add_row("To", dest)
    tabela.add_row("Amount", f"{amount} {'ARC' if token == 'native' else 'USDC'}")
    if resultado.get("tx_hash"):
        tabela.add_row("Tx hash", str(resultado["tx_hash"]))
    if resultado.get("raw_transaction"):
        raw = str(resultado["raw_transaction"])
        tabela.add_row("Raw tx", raw[:32] + "...")
    if resultado.get("aviso"):
        tabela.add_row("Warning", f"[yellow]{resultado['aviso']}[/yellow]")

    console.print(Panel(tabela, title="[bold cyan]Payment[/bold cyan]", border_style="cyan"))


# ---------------------------------------------------------------------------
# arc history — analysis history
# ---------------------------------------------------------------------------


@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of records to display."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """List recent analyses saved in ~/.arc_devkit/history.json."""
    if not _HISTORY_FILE.exists():
        console.print("[yellow]No history found.[/yellow]")
        console.print(f"[dim]Records are saved to {_HISTORY_FILE}[/dim]")
        return

    try:
        dados = _json.loads(_HISTORY_FILE.read_text())
    except Exception as exc:
        console.print(f"[red]Error reading history: {exc}[/red]")
        raise typer.Exit(1)

    recentes = dados[-limit:]

    if json_output:
        console.print_json(_json.dumps(recentes))
        return

    if not recentes:
        console.print("[yellow]History is empty.[/yellow]")
        return

    tabela = Table(title=f"History ({len(recentes)} records)", border_style="cyan")
    tabela.add_column("Timestamp", style="dim", min_width=20)
    tabela.add_column("Type", style="bold")
    tabela.add_column("Detail")

    for item in reversed(recentes):
        ts = item.get("timestamp", "")[:19]
        tipo = item.get("type", "?")
        detalhe = item.get("tx_hash", item.get("prompt", ""))
        if detalhe and len(detalhe) > 50:
            detalhe = detalhe[:50] + "..."
        tabela.add_row(ts, tipo, detalhe)

    console.print(tabela)


# ---------------------------------------------------------------------------
# arc portfolio — wallet portfolio analysis
# ---------------------------------------------------------------------------

portfolio_app = typer.Typer(help="Wallet portfolio analysis on Arc")
app.add_typer(portfolio_app, name="portfolio")

_SCORE_COLOR = {
    "high": "green",
    "medium": "yellow",
    "low": "cyan",
    "inactive": "dim",
}
_SCORE_ICON = {
    "high": "🔥",
    "medium": "📊",
    "low": "📉",
    "inactive": "💤",
}


@portfolio_app.command("analyze")
def portfolio_analyze(
    address: str = typer.Argument(..., help="EVM wallet address to analyze."),
    blocks: int = typer.Option(100, "--blocks", "-b", help="Number of recent blocks to scan."),
    no_ai: bool = typer.Option(False, "--no-ai", help="Skip AI analysis (faster)."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable debug logs."),
) -> None:
    """Analyze a wallet: balances, transaction history, and AI insights."""
    _set_verbose(verbose)
    checksum = _validate_address(address)

    from arc_devkit.analytics.portfolio import PortfolioAnalyzer

    analyzer = PortfolioAnalyzer()

    with console.status(
        f"Scanning last [bold]{blocks}[/bold] blocks for [cyan]{checksum[:10]}...[/cyan]",
        spinner="dots",
    ):
        snapshot = analyzer.analyze(checksum, scan_blocks=blocks)

    if json_output:
        data = analyzer.to_dict(snapshot)
        if not no_ai:
            data["ai_analysis"] = _portfolio_ai_analysis(snapshot)
        _save_history({"type": "portfolio", "address": checksum, "result": data})
        console.print_json(_json.dumps(data))
        return

    # Rich display
    score_color = _SCORE_COLOR[snapshot.activity_score]
    score_icon = _SCORE_ICON[snapshot.activity_score]

    # Balance table
    bal_table = Table(show_header=False, border_style=score_color, padding=(0, 1))
    bal_table.add_column("field", style="dim")
    bal_table.add_column("value", style="bold")
    bal_table.add_row("Address", f"[cyan]{snapshot.address}[/cyan]")
    bal_table.add_row(
        "Native balance",
        f"[green]{snapshot.native_balance:.6f}[/green] ARC",
    )
    if snapshot.usdc_balance is not None:
        bal_table.add_row(
            "USDC balance",
            f"[green]{snapshot.usdc_balance:.6f}[/green] USDC",
        )
    else:
        bal_table.add_row("USDC balance", "[dim]unavailable (contract pending)[/dim]")
    bal_table.add_row("Nonce (txs sent)", str(snapshot.nonce))
    bal_table.add_row(
        "Activity score",
        f"[{score_color}]{score_icon} {snapshot.activity_score}[/{score_color}]",
    )
    bal_table.add_row(
        "Blocks scanned",
        f"{snapshot.blocks_scanned} (#{snapshot.blocks_from} → #{snapshot.blocks_to})",
    )
    bal_table.add_row("Txs found", str(len(snapshot.recent_txs)))

    console.print(
        Panel(
            bal_table,
            title=f"[bold {score_color}]Portfolio — {checksum[:10]}...[/bold {score_color}]",
            border_style=score_color,
        )
    )

    # Recent transactions table
    if snapshot.recent_txs:
        tx_limit = 10
        tx_table = Table(
            title=f"Recent transactions (last {min(tx_limit, len(snapshot.recent_txs))} of {len(snapshot.recent_txs)})",
            border_style="dim",
            show_lines=False,
        )
        tx_table.add_column("Block", style="dim", justify="right")
        tx_table.add_column("Hash", style="dim")
        tx_table.add_column("Dir", justify="center")
        tx_table.add_column("Value (ARC)", justify="right")
        tx_table.add_column("Status")

        for tx in snapshot.recent_txs[-tx_limit:]:
            dir_style = "[green]↑ sent[/green]" if tx.direction == "sent" else "[blue]↓ recv[/blue]"
            status_style = (
                "[green]✓[/green]"
                if tx.status == "success"
                else "[red]✗[/red]"
                if tx.status == "failed"
                else "[yellow]…[/yellow]"
            )
            tx_table.add_row(
                str(tx.block),
                tx.hash[:18] + "...",
                dir_style,
                f"{tx.value_arc:.4f}",
                status_style,
            )
        console.print(tx_table)
    else:
        console.print("[dim]No transactions found in the scanned range.[/dim]")

    # AI analysis
    if not no_ai:
        with console.status("DevCopilot analyzing...", spinner="dots"):
            analysis = _portfolio_ai_analysis(snapshot)

        console.print(
            Panel(
                Markdown(analysis),
                title="[bold cyan]AI Analysis[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
            )
        )

    analyzer.save_snapshot(snapshot)
    _save_history(
        {
            "type": "portfolio",
            "address": checksum,
            "activity_score": snapshot.activity_score,
            "native_balance": str(snapshot.native_balance),
        }
    )


@portfolio_app.command("history")
def portfolio_history(
    address: str = typer.Argument(..., help="EVM wallet address."),
    limit: int = typer.Option(10, "--limit", "-n", help="Max snapshots to display."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Show saved balance history for a wallet (sorted newest first)."""
    from arc_devkit.analytics.portfolio import PortfolioAnalyzer

    checksum = _validate_address(address)
    records = PortfolioAnalyzer.load_history(checksum, limit=limit)

    if not records:
        console.print(
            f"[yellow]No history found for[/yellow] [cyan]{checksum}[/cyan]. "
            "Run [bold]arc portfolio analyze[/bold] first."
        )
        raise typer.Exit(0)

    if json_output:
        console.print_json(_json.dumps(records))
        return

    table = Table(
        title=f"Balance history — {checksum[:10]}... (last {len(records)})",
        border_style="cyan",
    )
    table.add_column("Timestamp", style="dim")
    table.add_column("Native (ARC)", justify="right", style="green")
    table.add_column("USDC", justify="right", style="green")
    table.add_column("Activity", justify="center")
    table.add_column("Txs", justify="right")

    for rec in records:
        table.add_row(
            rec.get("timestamp", "N/A")[:19].replace("T", " "),
            rec.get("native_balance", "?"),
            rec.get("usdc_balance") or "[dim]N/A[/dim]",
            rec.get("activity_score", "?"),
            str(rec.get("tx_count", "?")),
        )

    console.print(table)


@portfolio_app.command("report")
def portfolio_report(
    wallets_file: str = typer.Argument(
        ..., help="JSON file with wallet addresses (list of strings or [{address, label}])."
    ),
    blocks: int = typer.Option(100, "--blocks", "-b", help="Blocks to scan per wallet."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable debug logs."),
) -> None:
    """Consolidated portfolio report for multiple wallets from a JSON file."""
    _set_verbose(verbose)

    wallets_path = Path(wallets_file)
    if not wallets_path.exists():
        console.print(f"[red]File not found:[/red] {wallets_file}")
        raise typer.Exit(1)

    try:
        raw = _json.loads(wallets_path.read_text())
    except Exception as exc:
        console.print(f"[red]Could not read wallet file:[/red] {exc}")
        raise typer.Exit(1)

    # Accept both ["0x..."] and [{"address": "0x...", "label": "..."}]
    entries: list[dict] = []
    for item in raw:
        if isinstance(item, str):
            entries.append({"address": item, "label": ""})
        elif isinstance(item, dict) and "address" in item:
            entries.append({"address": item["address"], "label": item.get("label", "")})
        else:
            console.print(f"[yellow]Skipping invalid entry:[/yellow] {item}")

    if not entries:
        console.print("[red]No valid addresses found in file.[/red]")
        raise typer.Exit(1)

    from arc_devkit.analytics.portfolio import PortfolioAnalyzer

    analyzer = PortfolioAnalyzer()
    results: list[dict] = []

    report_table = Table(
        title=f"Portfolio Report — {len(entries)} wallets",
        border_style="cyan",
        show_lines=True,
    )
    report_table.add_column("Label", style="bold")
    report_table.add_column("Address")
    report_table.add_column("ARC Balance", justify="right")
    report_table.add_column("USDC", justify="right")
    report_table.add_column("Nonce", justify="right")
    report_table.add_column("Txs", justify="right")
    report_table.add_column("Activity")

    for entry in entries:
        addr = entry["address"]
        label = entry.get("label", "")
        try:
            checksum = _validate_address(addr)
        except SystemExit:
            continue

        with console.status(f"Analyzing [cyan]{checksum[:10]}...[/cyan]", spinner="dots"):
            snapshot = analyzer.analyze(checksum, scan_blocks=blocks)

        data = analyzer.to_dict(snapshot)
        data["label"] = label
        results.append(data)

        score_color = _SCORE_COLOR[snapshot.activity_score]
        score_icon = _SCORE_ICON[snapshot.activity_score]
        usdc_str = f"{snapshot.usdc_balance:.4f}" if snapshot.usdc_balance is not None else "N/A"

        report_table.add_row(
            label or "—",
            f"{checksum[:10]}...",
            f"{snapshot.native_balance:.4f}",
            usdc_str,
            str(snapshot.nonce),
            str(len(snapshot.recent_txs)),
            f"[{score_color}]{score_icon} {snapshot.activity_score}[/{score_color}]",
        )

    if json_output:
        console.print_json(_json.dumps(results))
        return

    console.print(report_table)
    console.print(
        f"\n[dim]Scanned last {blocks} blocks per wallet. "
        f"Run [bold]arc portfolio analyze <address>[/bold] for full detail.[/dim]"
    )


def _portfolio_ai_analysis(snapshot) -> str:  # type: ignore[no-untyped-def]
    """Call DevCopilot to generate a brief portfolio analysis."""
    from arc_devkit.config import settings
    from arc_devkit.copilot.agent import DevCopilot

    usdc_str = (
        f"{snapshot.usdc_balance:.6f} USDC" if snapshot.usdc_balance is not None else "unavailable"
    )
    sent = sum(1 for tx in snapshot.recent_txs if tx.direction == "sent")
    received = sum(1 for tx in snapshot.recent_txs if tx.direction == "received")
    failed = sum(1 for tx in snapshot.recent_txs if tx.status == "failed")

    prompt = (
        f"Analyze this wallet on Arc {settings.arc_network.capitalize()} and give a brief, "
        f"practical summary (3-5 sentences).\n\n"
        f"Wallet: {snapshot.address}\n"
        f"Native (ARC) balance: {snapshot.native_balance:.6f}\n"
        f"USDC balance: {usdc_str}\n"
        f"Total txs ever sent (nonce): {snapshot.nonce}\n"
        f"Blocks scanned: {snapshot.blocks_scanned} "
        f"(#{snapshot.blocks_from} to #{snapshot.blocks_to})\n"
        f"Txs found in window: {len(snapshot.recent_txs)} "
        f"(sent: {sent}, received: {received}, failed: {failed})\n"
        f"Activity score: {snapshot.activity_score}\n\n"
        f"Focus on: balance health, activity patterns, and any notable observations."
    )

    return DevCopilot().ask(prompt)


# ---------------------------------------------------------------------------
# arc init — interactive wizard to create .env
# ---------------------------------------------------------------------------


@app.command()
def init() -> None:
    """Interactive wizard to create your .env from scratch."""
    console.print(
        Panel.fit(
            "[bold cyan]Arc DevKit — Initial Setup[/bold cyan]\n"
            "[dim]Let's set up your .env file with the required variables.[/dim]",
            border_style="cyan",
        )
    )

    if _ENV_FILE.exists():
        sobrescrever = typer.confirm(".env already exists. Overwrite?", default=False)
        if not sobrescrever:
            console.print("[yellow]Setup cancelled.[/yellow]")
            raise typer.Exit()

    campos = [
        ("ANTHROPIC_API_KEY", "Your Anthropic API key (sk-ant-...)", True),
        ("ARC_NETWORK", "Network — mainnet or testnet", False, "mainnet"),
        (
            "ARC_RPC_URL",
            "Arc RPC URL override (blank = official default for ARC_NETWORK)",
            False,
            "",
        ),
        (
            "ARC_CHAIN_ID",
            "Arc chain ID override (blank = official default for ARC_NETWORK)",
            False,
            "",
        ),
        ("ARC_PRIVATE_KEY", "EVM private key (optional, 0x...)", False, ""),
        ("LOG_LEVEL", "Log level", False, "INFO"),
    ]

    valores: dict[str, str] = {}
    for campo in campos:
        nome, descricao = campo[0], campo[1]
        obrigatorio = campo[2] if len(campo) > 2 else False
        default = campo[3] if len(campo) > 3 else ""

        prompt = f"[bold]{nome}[/bold] — {descricao}"
        if default:
            prompt += f" [dim](default: {default})[/dim]"

        console.print(f"\n  {prompt}")
        valor = typer.prompt("  > ", default=default, show_default=False)

        if obrigatorio and not valor.strip():
            console.print(f"[red]  ✗ {nome} is required.[/red]")
            raise typer.Exit(1)

        valores[str(nome)] = valor

    linhas = [f"{k}={v}" for k, v in valores.items() if v]
    _ENV_FILE.write_text("\n".join(linhas) + "\n")

    # Private key in .env: restrict file permissions and warn about safer options
    if valores.get("ARC_PRIVATE_KEY"):
        import os as _os
        import stat as _stat

        try:
            _os.chmod(_ENV_FILE, 0o600)
            console.print("[dim]Applied chmod 600 to .env (owner read/write only).[/dim]")
        except Exception:
            pass

        mode = _ENV_FILE.stat().st_mode
        if mode & (_stat.S_IRGRP | _stat.S_IROTH):
            console.print(
                "[bold yellow]⚠ Warning:[/bold yellow] your .env contains a private key and "
                "is readable by other users. Run: [bold]chmod 600 .env[/bold]"
            )
        console.print(
            "[dim]Tip: store the key in the OS keyring instead of .env with "
            "[bold]arc config keyring-set[/bold] (requires pip install 'arc-devkit[security]').[/dim]"
        )

    console.print(
        f"\n[bold green]✓[/bold green] File [bold]{_ENV_FILE}[/bold] created successfully!\n"
        "Run [bold]arc status[/bold] to test the connection."
    )
