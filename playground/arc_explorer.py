"""
Arc Explorer — explorador interativo da Arc blockchain.

Usa o arc-devkit instalado via PyPI para demonstrar os três módulos:
  - DevCopilot   (assistente de IA)
  - Core         (conexão, saldo, gas)
  - Tx Debugger  (análise de transações)

Instalação:
    pip install -r requirements.txt
    cp ../.env.example .env   # preencha ANTHROPIC_API_KEY e ARC_RPC_URL

Uso:
    python arc_explorer.py
"""

from decimal import Decimal

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

console = Console()

MENU = {
    "1": ("Perguntar ao DevCopilot", "cyan"),
    "2": ("Verificar saldo de carteira", "green"),
    "3": ("Estimar custo de gás", "yellow"),
    "4": ("Analisar transação", "magenta"),
    "0": ("Sair", "dim"),
}


def banner(block: int, chain_id: int, gas_gwei: str) -> None:
    from arc_devkit.config import settings

    tabela = Table(show_header=False, border_style="cyan", padding=(0, 1))
    tabela.add_column("campo", style="dim")
    tabela.add_column("valor", style="bold")
    tabela.add_row("Rede", f"Arc {settings.arc_network.capitalize()}")
    tabela.add_row("Chain ID", str(chain_id))
    tabela.add_row("Bloco atual", f"#{block}")
    tabela.add_row("Gas price", f"{gas_gwei} gwei")

    console.print(
        Panel(
            tabela,
            title="[bold cyan]Arc Explorer[/bold cyan]  [dim]via arc-devkit (PyPI)[/dim]",
            border_style="cyan",
            padding=(0, 1),
        )
    )


def print_menu() -> None:
    console.print()
    for key, (label, cor) in MENU.items():
        console.print(f"  [{cor}][{key}][/{cor}] {label}")
    console.print()


def cmd_copilot() -> None:
    question = Prompt.ask("\n[cyan]Pergunta[/cyan]")
    if not question.strip():
        return

    from arc_devkit.copilot.agent import DevCopilot

    with console.status("[cyan]DevCopilot pensando...[/cyan]", spinner="dots"):
        copilot = DevCopilot()
        answer = copilot.ask(question)

    console.print(
        Panel(
            Markdown(answer),
            title="[bold cyan]DevCopilot[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )


def cmd_balance(w3) -> None:
    address = Prompt.ask("\n[green]Endereço da carteira[/green]")
    address = address.strip()
    if not address:
        return

    try:
        from web3 import Web3

        checksum = Web3.to_checksum_address(address)
        balance_wei = w3.eth.get_balance(checksum)
        balance = Decimal(str(w3.from_wei(balance_wei, "ether")))
        nonce = w3.eth.get_transaction_count(checksum)

        tabela = Table(
            title=f"[dim]{checksum[:20]}...[/dim]",
            show_header=False,
            border_style="green",
            padding=(0, 1),
        )
        tabela.add_column("campo", style="dim")
        tabela.add_column("valor", style="bold")
        tabela.add_row("Endereço", checksum)
        tabela.add_row("Saldo nativo", f"[green]{balance:.6f}[/green] ARC")
        tabela.add_row("Transações enviadas (nonce)", str(nonce))

        console.print(tabela)

    except Exception as exc:
        console.print(f"[red]Erro: {exc}[/red]")


def cmd_gas(w3) -> None:
    to = Prompt.ask("\n[yellow]Endereço de destino[/yellow]")
    amount_str = Prompt.ask("[yellow]Valor a transferir (USDC)[/yellow]", default="1.0")

    try:
        from arc_devkit.core.gas import estimate_transfer

        with console.status("[yellow]Consultando RPC...[/yellow]", spinner="dots"):
            est = estimate_transfer(to.strip(), float(amount_str))

        tabela = Table(
            title="Estimativa de Gás",
            show_header=False,
            border_style="yellow",
            padding=(0, 1),
        )
        tabela.add_column("campo", style="dim")
        tabela.add_column("valor", style="bold")
        tabela.add_row("Destino", est["to"])
        tabela.add_row("Transferência", f"{amount_str} USDC")
        tabela.add_row("Gas limit", str(est["gas_limit"]))
        tabela.add_row("Gas price", f"{est['gas_price_gwei']} gwei")
        tabela.add_row("Custo de gás", f"[bold yellow]{est['custo_usdc']}[/bold yellow] USDC")

        console.print(tabela)

    except Exception as exc:
        console.print(f"[red]Erro: {exc}[/red]")


def cmd_debug() -> None:
    tx_hash = Prompt.ask("\n[magenta]Hash da transação (0x...)[/magenta]")
    tx_hash = tx_hash.strip()
    if not tx_hash:
        return

    try:
        from arc_devkit.debugger.tx_analyzer import TxAnalyzer

        with console.status("[magenta]Analisando transação...[/magenta]", spinner="dots"):
            resultado = TxAnalyzer().analyze(tx_hash)

        status = resultado.get("status", "desconhecido")
        cor = "green" if status == "sucesso" else "red"
        icone = "✓" if status == "sucesso" else "✗"

        tabela = Table(
            title=f"[dim]{tx_hash[:20]}...[/dim]",
            show_header=False,
            border_style="magenta",
            padding=(0, 1),
        )
        tabela.add_column("campo", style="dim")
        tabela.add_column("valor", style="bold")
        tabela.add_row("Hash", tx_hash[:24] + "...")
        tabela.add_row("Status", f"[{cor}]{icone} {status}[/{cor}]")
        tabela.add_row("Custo gás", f"{resultado.get('custo_usdc', 'N/A')} USDC")

        console.print(tabela)

        if resultado.get("resumo"):
            console.print(
                Panel(
                    Markdown(resultado["resumo"]),
                    title="[bold magenta]Análise AI[/bold magenta]",
                    border_style="magenta",
                    padding=(1, 2),
                )
            )

    except Exception as exc:
        console.print(f"[red]Erro: {exc}[/red]")


def main() -> None:
    # Conectar na Arc antes de qualquer coisa
    from arc_devkit.config import settings
    from arc_devkit.core.connection import check_connection, get_web3

    console.print(f"\n[dim]Conectando na Arc {settings.arc_network.capitalize()}...[/dim]")

    if not check_connection():
        console.print(
            "[red]✗ Não foi possível conectar.\n  Configure ARC_RPC_URL no arquivo .env[/red]"
        )
        return

    w3 = get_web3()
    gas_gwei = str(w3.from_wei(w3.eth.gas_price, "gwei"))
    banner(w3.eth.block_number, w3.eth.chain_id, gas_gwei)

    handlers = {
        "1": cmd_copilot,
        "2": lambda: cmd_balance(w3),
        "3": lambda: cmd_gas(w3),
        "4": cmd_debug,
    }

    while True:
        print_menu()
        choice = Prompt.ask("Escolha", choices=list(MENU.keys()), default="0")

        if choice == "0":
            console.print("\n[dim]Até logo![/dim]\n")
            break

        handler = handlers.get(choice)
        if handler:
            handler()


if __name__ == "__main__":
    main()
