# Demonstração na Mainnet

**Arc DevKit é um toolkit Python (SDK + CLI)** para construir e depurar aplicações sobre a Arc Mainnet. Esta página é evidência técnica de que o pacote publicado — `pip install arc-devkit` — instala e funciona contra a Arc Mainnet real, usando apenas a API pública do SDK (`arc_devkit.Arc`).

> Esta página apresenta evidência técnica de funcionamento, não uma promessa de aprovação em qualquer programa. A gravação em vídeo, por si só, não substitui nem satisfaz nenhum requisito de "live deployment" — ela é um registro complementar da instalação e do uso reais do pacote.

## 1. O que está sendo demonstrado

1. Um script Python (`demo/mainnet_demo.py`) que usa somente `arc_devkit.Arc` para: conectar à Arc Mainnet, rodar `health_check()`, ler o bloco mais recente, localizar/consultar uma transação real confirmada e analisá-la com `debug_transaction(..., use_ai=False)` — sem qualquer dependência de IA ou credencial.
2. Uma página no site (`/demo`) que executa as mesmas operações através de um backend Python separado que chama o próprio SDK — nunca substitui o SDK por chamadas diretas de RPC em JavaScript.
3. Uma gravação real de terminal, de um ambiente virtual novo até a consulta e análise de uma transação da mainnet.

## 2. Instalação e uso (tutorial)

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install arc-devkit==0.10.0
```

```bash
curl -O https://raw.githubusercontent.com/Jeielsantosdev/arc-devkit/main/demo/mainnet_demo.py
python3 mainnet_demo.py                       # busca uma transação recente automaticamente
python3 mainnet_demo.py 0xSEU_HASH_AQUI       # ou informe um hash específico
```

Script completo: [`demo/mainnet_demo.py`](../../demo/mainnet_demo.py) (repositório). Não depende de nada além do pacote `arc-devkit` publicado — sem `.env` pessoal, sem carteira privada, sem envio de transação, sem deploy de contrato. Consulta exclusivamente dados públicos da rede.

Equivalente mínimo em código:

```python
from arc_devkit import Arc

arc = Arc.mainnet()
health = arc.health_check()          # rpc_ok, chain_id_match, latency_ms...
block = arc.latest_block()           # number, timestamp, hash...
tx = arc.get_transaction(tx_hash)    # dados brutos da transação
report = arc.debug_transaction(tx_hash, use_ai=False)  # status, custo_usdc, resumo
```

## 3. Gravação: da instalação ao uso

Sessão real de terminal, gravada com [asciinema](https://asciinema.org), mostrando exatamente os passos acima — `python3 --version`, criação/ativação do venv, `pip install arc-devkit==0.10.0`, verificação da versão instalada, e a execução real do script contra a Arc Mainnet.

| Formato | Arquivo |
|---|---|
| Cast (asciinema, fonte da verdade) | [`demo/recording/arc_devkit_mainnet_demo.cast`](../../demo/recording/arc_devkit_mainnet_demo.cast) |
| Player no navegador (offline, autocontido) | [`demo/recording/player/index.html`](../../demo/recording/player/index.html) |
| Vídeo WebM | [`demo/recording/arc_devkit_mainnet_demo.webm`](../../demo/recording/arc_devkit_mainnet_demo.webm) |
| Vídeo MP4 | [`demo/recording/arc_devkit_mainnet_demo.mp4`](../../demo/recording/arc_devkit_mainnet_demo.mp4) |
| Transcrição em texto | [`demo/recording/transcript.txt`](../../demo/recording/transcript.txt) |

Detalhes de metodologia, isolamento de credenciais e o script que conduziu a sessão estão documentados em [`demo/recording/README.md`](../../demo/recording/README.md), incluindo a divulgação explícita de que a sessão foi conduzida por um script de automação (não digitada manualmente), com todos os comandos genuinamente executados e sem edição de conteúdo (apenas limite de tempo ocioso do próprio asciinema).

**A gravação, isoladamente, comprova instalação e uso do pacote — ela não constitui, por si só, um "live deployment" do produto.**

## 4. Evidência real observada (registro histórico)

> 🕒 **Resultado histórico gravado** — os valores abaixo foram observados durante a gravação da Seção 3 e ficam fixos neste documento. Para conferir o estado atual da rede, use a consulta ao vivo na [página `/demo` do site](#5-demonstração-ao-vivo-no-site) ou execute o script você mesmo.

| Campo | Valor |
|---|---|
| Pacote instalado | `arc-devkit` |
| Versão | `0.10.0` |
| Origem da instalação | PyPI (`pip install arc-devkit==0.10.0`), não build local |
| Data/hora da execução | 2026-09-18 |
| Rede | Arc Mainnet |
| Chain ID observado (via RPC, `health_check()`) | `5042` |
| Hash da transação analisada | `0x66805e7addc8884e80260a7a4abfad144f37341cd323b3327e93ea2cfbc23ceb` |
| Bloco | `21537082` |
| Explorer | <https://explorer.arc.io/tx/0x66805e7addc8884e80260a7a4abfad144f37341cd323b3327e93ea2cfbc23ceb> |

Uma segunda transação, encontrada em uma execução de validação separada nesta mesma tarefa (fora da gravação), também confirma um Transfer ERC-20 de USDC real e decodificado corretamente: `0xafcc72e47de265ed4dc2f584f8e1a325a4cf45d24f41e299da76becdb76dcc74`, bloco `21530719`, 524.671261 USDC — <https://explorer.arc.io/tx/0xafcc72e47de265ed4dc2f584f8e1a325a4cf45d24f41e299da76becdb76dcc74>.

## 5. Demonstração ao vivo no site

A página [`/demo`](/demo) do site executa as mesmas quatro operações (status/health check, bloco mais recente, busca de transação recente, consulta+análise de transação) em tempo real, contra a Arc Mainnet, através de um backend Python (`arc_devkit.api.demo_app`) que reutiliza diretamente `arc_devkit.Arc` — nunca chamadas diretas de RPC em JavaScript.

- Quando o backend está publicado e acessível, a página mostra um indicador **"AO VIVO"** e os dados vêm de uma chamada de rede real, com timestamp da consulta.
- Quando o backend não está configurado/acessível, a página mostra explicitamente **"backend indisponível"**, desabilita os controles de consulta e nunca substitui isso por dados simulados.
- A seção "Referência histórica gravada" da própria página reexibe os dados da Seção 4 acima, marcados como não-ao-vivo.

**Status de publicação no momento desta entrega:** o backend (`arc_devkit/api/demo_app.py`) foi validado localmente (testes automatizados, execução via `uvicorn`, e build/execução via Docker — todos contra a Arc Mainnet real) e possui configuração de deploy pronta ([`demo/Dockerfile`](../../demo/Dockerfile), [`demo/render.yaml`](../../demo/render.yaml)), mas **não foi implantado em nenhum serviço público** como parte desta tarefa — o site em produção (Vercel/Next.js) não executa Python, então esse backend precisa de um serviço separado, e implantá-lo requer acesso/autorização de hospedagem que está fora do escopo desta entrega. Enquanto isso, `/demo` funciona corretamente no estado "backend indisponível", sem apresentar nenhum dado como ao vivo.

## 6. Limitações

- A demonstração cobre apenas operações de leitura (consulta de bloco, transação, health check, análise via debugger sem IA). Não cobre envio de transações, assinatura, deploy de contratos ou uso do Copilot (que exige `ANTHROPIC_API_KEY`).
- A transação usada na gravação (Seção 3) e no registro histórico (Seção 4) foi encontrada automaticamente entre os blocos recentes no momento da execução — não foi criada ou enviada por esta demonstração.
- A gravação foi conduzida por um script de automação, não digitada manualmente; ver a divulgação completa em [`demo/recording/README.md`](../../demo/recording/README.md).
- O backend do site (`arc_devkit/api/demo_app.py`) ainda não está publicamente hospedado — ver Seção 5.
- `arc.debug_transaction(..., use_ai=True)` (análise em linguagem natural via IA) não é exercitado por esta demonstração; apenas o modo `use_ai=False`, que não depende de credenciais de IA.

## 7. Como reproduzir

```bash
# 1. Instalação em ambiente limpo
python3 -m venv .venv && source .venv/bin/activate
pip install arc-devkit==0.10.0

# 2. Execução do script (busca automática de transação)
python3 demo/mainnet_demo.py

# 3. Ou com um hash específico
python3 demo/mainnet_demo.py 0x66805e7addc8884e80260a7a4abfad144f37341cd323b3327e93ea2cfbc23ceb

# 4. Reprodução da gravação
asciinema play demo/recording/arc_devkit_mainnet_demo.cast

# 5. Backend da demo do site, localmente
uvicorn arc_devkit.api.demo_app:app --reload --port 8010
curl http://127.0.0.1:8010/demo/status
```

Repositório: <https://github.com/Jeielsantosdev/arc-devkit> · Script completo: [`demo/mainnet_demo.py`](../../demo/mainnet_demo.py) · Instruções adicionais: [`demo/README.md`](../../demo/README.md).
