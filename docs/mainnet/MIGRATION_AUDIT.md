# Migration Audit — Arc Testnet → Arc Mainnet

**Data da auditoria:** 2026-09-18
**Versão atual do pacote:** `0.8.0` (`pyproject.toml`, status `Development Status :: 3 - Alpha`)
**Escopo:** inventário completo de tudo no Arc DevKit que hoje depende de suposições de Arc Testnet, antes de qualquer alteração de código.

Este documento tem duas partes:

- **Parte A** — inventário do que existe hoje no repositório (auditoria de código/documentação).
- **Parte B** — configuração oficial e atual da Arc Mainnet, pesquisada em `docs.arc.io` e verificada byte a byte contra o HTML bruto da página oficial (não apenas resumida por IA). Nenhum valor abaixo foi inventado; cada um cita a fonte oficial e a data da consulta.

---

## Parte A — Inventário de dependências de Testnet no código atual

### A.0 Contexto de versão

- Versão atual: `0.8.0`. Última entrada do `CHANGELOG.md`: `[0.8.0] — 2026-07-25` ("multi-network config, fees/paymaster, CCTP bridge, agentic economy, MCP, privacy/PQ groundwork").
- Já existe um `MAINNET_CHECKLIST.md` na raiz do repositório, criado como rascunho de planejamento para esta mesma migração — deve ser consolidado/substituído pelos documentos em `docs/mainnet/`, não duplicado.
- `README.md:735` — instrução de instalação desatualizada (`pip install arc-devkit==0.4.0`, pacote já está em `0.8.0`) — corrigir independentemente da mainnet.
- `docs/getting-started.md:5` — `> Current version: 0.2+`, também desatualizado.
- `copilot/agent.py:39` — system prompt do Claude contém literalmente **"Testnet active since October 2025; mainnet expected Summer 2026"**. Isso é injetado como fato em toda resposta do Copilot (`arcdevkit copilot ask`, `arc ask`, `arcdevkit debug`, `arcdevkit portfolio analyze`) — é a peça de conteúdo desatualizado mais crítica, pois não é apenas documentação lida por humanos, é contexto que o modelo trata como verdade.

### A.1 Chain ID hardcoded (`5042002`)

| Local | Observação |
|---|---|
| `arc_devkit/networks.py:34` | `chain_id=5042002` dentro de `NETWORKS["testnet"]` — correto, escopado ao perfil testnet. |
| **`arc_devkit/config.py:117`** | **Bug de segurança.** `chain_id = int(chain_id_raw) if chain_id_raw else (profile.chain_id or 5042002)`. Se `ARC_NETWORK=mainnet` e `ARC_CHAIN_ID` não for definido explicitamente, `settings.arc_chain_id` cai silenciosamente para `5042002` (chain ID da **testnet**), mesmo apontando para um RPC de mainnet real. Ver detalhes de risco em A.9. |
| `arc_devkit/cli/flat.py:1113` | Wizard `arc init` sugere `"5042002"` como default, sem alternativa de mainnet. |
| `.env.example`, `docs/getting-started.md`, `docs/index.md`, `docs/migration-rpc.md`, `docs/cli-guide.md`, `docs/modules/analytics.md`, `docs/modules/agent-starter-kit.md`, `docs/api-reference.md`, `README.md` | Múltiplas ocorrências de `5042002` como único valor documentado. |
| `.github/workflows/ci.yml`, `tests/conftest.py` e ~18 arquivos de teste | CI e testes fixam `5042002` — esperado para testes unitários/regressão, mas nenhum testa o caminho `mainnet`. |
| `website/components/Sidebar.tsx:68`, `website/lib/i18n.ts:40-41` | Site de marketing hardcoda "Chain ID: 5042002" na UI. |

### A.2 RPC hardcoded (`https://arc-testnet.drpc.org`)

- `arc_devkit/networks.py:35` — escopado corretamente a `NETWORKS["testnet"]`, mas **o valor em si está desatualizado**: a URL oficial atual da Circle para testnet é `https://rpc.testnet.arc.io` (ver Parte B, item 9). `arc-testnet.drpc.org` parece ser um domínio antigo/genérico da dRPC, não o endpoint atualmente documentado em `docs.arc.io`.
- `arc_devkit/cli/flat.py:1112` — default do wizard `arc init`.
- `.env.example:20,22`, `.github/workflows/ci.yml:11`, `tests/conftest.py:12` + ~6 outros arquivos de teste, cassettes VCR (`tests/cassettes/testnet_*.yaml`).
- Docs: `docs/getting-started.md`, `docs/index.md`, `docs/migration-rpc.md` (documento inteiro é sobre uma migração de RPC *anterior*, `rpc.arc.io` → `arc-testnet.drpc.org`), `docs/cli-guide.md`, `docs/modules/analytics.md`, `docs/modules/agent-starter-kit.md`, `examples/01_check_connection.py:8`, `README.md`.
- `website/components/Sidebar.tsx:69`.

### A.3 Endereços de contrato hardcoded

- **`arc_devkit/stablecoins/token.py:93`** — `USDC_ARC_TESTNET_ADDRESS = "0x0000000000000000000000000000000000000000"` — um placeholder de endereço zero, não um contrato real.
- **`arc_devkit/stablecoins/token.py:259`** — esse placeholder é o **valor default do construtor** de `USDCToken`, então `USDCToken()` sem argumento aponta silenciosamente para o endereço zero.
- `arc_devkit/usdc/token.py:5` — shim de compatibilidade reexporta o mesmo placeholder.
- **`arc_devkit/core/gas.py:106,110`** — `quote_fee(..., token="usdc")` importa e usa `USDC_ARC_TESTNET_ADDRESS` diretamente, **ignorando** `settings.network.contracts.usdc`. Resultado: `arcdevkit fees quote --token usdc` cota contra o endereço zero independentemente de `ARC_NETWORK`.
- **`arc_devkit/agents/payment_agent.py:115,117,121`** — mesmo padrão: `PaymentAgent._build_usdc_signed_tx()` usa o placeholder hardcoded em vez de resolver pelo `NetworkProfile` ativo.
- **`arc_devkit/bridge/cctp.py:136,183`** — `CCTPBridge.start_transfer()` usa o placeholder como `burnToken` em vez de `self._profile.contracts.usdc`. Hoje inofensivo porque o construtor já levanta erro quando `cctp_token_messenger is None`, mas o bug fica exposto assim que endereços reais de CCTP forem configurados (que agora existem — ver Parte B, item 7).
- `arc_devkit/networks.py:38` — `NETWORKS["testnet"].contracts.usdc` também aponta para o endereço zero — mas isso está **desatualizado**: a Circle já publica o endereço real da interface ERC-20 do USDC tanto para testnet quanto mainnet (`0x3600...0000`, ver Parte B, item 6).
- `arc_devkit/networks.py:46-57` — `NETWORKS["mainnet"]` usa `None` explícito em todos os campos — padrão correto, é só preencher com os valores verificados na Parte B.

### A.4 Explorers de testnet

- Nenhuma URL de explorer está hardcoded em `arc_devkit/` hoje — `NetworkProfile.explorer_url` é `None` tanto para testnet quanto mainnet (`networks.py:36,50`). Isso é uma lacuna também para testnet, não só mainnet.
- `tests/test_cli_sprint6.py:25`, `tests/test_bridge.py:15` usam URLs fake apenas como fixtures de teste — sem risco.

### A.5 Dependência de faucet

- `docs/getting-started.md:20,160` — link para `https://faucet.arc.io` (URL desatualizada — o faucet oficial atual é `https://faucet.circle.com`, ver Parte B, item 9).
- `docs/modules/agent-starter-kit.md:278` — exemplo `FaucetAgent` que distribui USDC sob demanda para qualquer endereço. Padrão inerentemente de testnet; **perigoso se apontado para mainnet** (agente que dá fundos reais a quem pedir).
- `tests/test_integration.py:15` — comentário menciona endereço "faucet" de testnet.
- Nenhum código de `arc_devkit/` em si chama um endpoint de faucet — o acoplamento está em docs/exemplos.

### A.6 Suposições específicas de testnet espalhadas pelo código

- `arc_devkit/core/connection.py:11-25` — comentários descrevem o middleware PoA como "comum em testnets" / "compatibilidade com Arc testnet". A mainnet da Arc também roda com um conjunto de validadores permissionado (ver Parte B, item 15.5), então o middleware provavelmente continua necessário — mas o comentário precisa ser corrigido para não sugerir que é exclusivo de testnet.
- **`arc_devkit/cli/flat.py:98-138`** (`arc status`) e **`arc_devkit/cli/main.py:96-108`** (`arcdevkit status`) — texto hardcoded `"Arc Testnet"` / `"Connected to Arc testnet!"` independente de `settings.arc_network`. Um usuário com `ARC_NETWORK=mainnet` vê "Arc Testnet" na tela mesmo com o chain ID real de mainnet ao lado.
- `arc_devkit/api/main.py:248-254` (`GET /health`) — docstring hardcoda "Arc testnet" (corpo da resposta é agnóstico, só a documentação está desatualizada).
- `arc_devkit/analytics/portfolio.py` (via `cli/flat.py:1064,1071`) — prompt de IA do `_portfolio_ai_analysis()` afirma `"Analyze this wallet on the Arc blockchain testnet..."` incondicionalmente — a análise de um wallet de mainnet real seria descrita como testnet.
- `playground/arc_explorer.py:40,193` — hardcoda "Arc Testnet" / "Conectando na Arc testnet..." (demo de baixa prioridade, mas ainda ship no repo).
- `arc_devkit/paymaster/detector.py:26`, `arc_devkit/bridge/cctp.py:74` — parâmetro `network` com default `"testnet"` (a maioria dos call sites já passa `settings.arc_network` explicitamente — confirmar antes de tratar como prioridade alta).

### A.7 Documentação desatualizada / URLs antigas

- `docs/migration-rpc.md` — documenta uma migração *histórica* de RPC pré-existente (`rpc.arc.io` → `arc-testnet.drpc.org`), não relacionada à migração mainnet atual. Pode servir de template estrutural para o novo guia, mas como está hoje confunde quem procura orientação de mainnet.
- `README.md:735` — "Arc DevKit targets Arc testnet... Mainnet is expected summer 2026" — desatualizado (mainnet já lançou, 2026-09-16).
- `README.md:8` — badge estático `arc-testnet-orange`.
- `docs/getting-started.md:3` — todo o guia é enquadrado em testnet, sem branch de mainnet.
- `docs/playground.md:9` — "Todos os exemplos abaixo usam a testnet por padrão" — correto hoje, precisa de contraparte de mainnet.
- Quatro locais separados (`docs/modules/analytics.md`, `docs/index.md`, `docs/cookbook.md`, `docs/modules/agent-starter-kit.md`) repetem a mesma ressalva "endereço USDC é zero-address placeholder" — todos precisam de atualização em conjunto quando o endereço real entrar em `networks.py`.

### A.8 Exemplos que não funcionariam corretamente em mainnet

- `examples/01_check_connection.py:15`, `examples/02_copilot_ask.py:22,30` — texto de console/prompt hardcoda "Arc testnet"; funcionalmente funcionam via `.env`, mas a saída é enganosa.
- `examples/06_agent_job_negotiation.py:2` — docstring descreve o fluxo como exercício "on testnet" via ERC-8183 escrow, sem nenhum aviso sobre risco de fundos reais caso apontado para um registry de mainnet.
- `examples/03_estimate_gas.py`, `examples/04_monitor_wallet.py`, `examples/05_debug_tx.py` — agnósticos de rede, sem mudanças necessárias.
- Nenhum exemplo mostra como alternar para `ARC_NETWORK=mainnet` nem avisa que transações de mainnet movem USDC real — lacuna de documentação, não de código.

### A.9 Código potencialmente perigoso em mainnet

1. **`config.py:117`** (ver A.1) — maior prioridade. Cenário: operador define `ARC_NETWORK=mainnet` e `ARC_RPC_URL` real (obrigatório, já que mainnet não tem RPC default), mas esquece `ARC_CHAIN_ID`. `settings.arc_chain_id` vira silenciosamente `5042002` (testnet) enquanto toda transação vai para o RPC real de mainnet. Os caminhos de assinatura de transação inspecionados (`payment_agent.py`, `stablecoins/token.py`, `cctp.py`) usam `self._w3.eth.chain_id` (lido do RPC ao vivo, portanto correto) e não `settings.arc_chain_id` — então o risco imediato de assinatura está contido. Mas `settings.arc_chain_id` é exposto via `arcdevkit config get ARC_CHAIN_ID` e endpoints de status/health, e qualquer código externo que confie nesse valor para validação anti-replay antes de assinar seria enganado.
2. **Nenhuma confirmação pré-broadcast em nenhum lugar do CLI.** `arc send --broadcast` (`cli/flat.py:660-717`) vai direto de montar a tx para `agent.execute(..., enviar=broadcast)`, sem prompt interativo "você está prestes a enviar fundos reais em `<network>`, confirma?" — ao contrário do wizard `arc init`, que já usa `typer.confirm(...)` ao sobrescrever `.env`.
3. **`PaymentAgent.execute()`/`execute_batch()`** — nenhuma exibição de rede nem checagem de sanidade de chain ID antes de `send_raw_transaction`.
4. **`CCTPBridge.start_transfer()`/`mint()`** — queima/emite USDC real entre chains sem confirmação; hoje protegido apenas pelo guard `cctp_token_messenger is None`, que deixa de proteger assim que endereços reais forem preenchidos (que já existem — Parte B, item 7). Cross-chain é mais difícil de reverter que same-chain.
5. **Guardrails (`MAX_SPEND_PER_DAY_USDC`, `AGENT_ALLOWED_RECIPIENTS`) são opt-in e vazios por default** (`.env.example:58-64`, `config.py:35-36`) — `PaymentAgent`/`CCTPBridge`/`JobRegistry` rodam **sem limite de gasto e sem whitelist de destinatário** a menos que o caller construa `Guardrails` explicitamente.
6. **`USDCToken()` com default de endereço zero** (`stablecoins/token.py:257-262`) — falha silenciosa em vez de erro imediato na construção; inconsistente com o padrão já usado por `EURCToken`, `AgentRegistry`, `JobRegistry`, `CCTPBridge`, `PriceOracle`, `ConfidentialTransferClient` (todos exigem endereço explícito).

### A.10 Abstrações já existentes e reaproveitáveis sem mudanças

- **`arc_devkit/networks.py`** — `NetworkProfile`/`ContractAddresses` + registro `NETWORKS` + `get_network()`. É a base correta; `NETWORKS["mainnet"]` já existe com `None` explícito em todos os campos. **Preencher esses sete valores é a maior parte do trabalho real de migração** — tudo que já lê `settings.network`/`get_network()` herda automaticamente.
- **`arc_devkit/config.py`** — resolução de `ARC_NETWORK` e overrides explícitos de `ARC_RPC_URL`/`ARC_CHAIN_ID` já funciona corretamente, exceto pelo bug pontual em A.9.1.
- **`arcdevkit network list|show|check-mainnet`** (`cli/commands/network.py`) — já genérico; `check-mainnet` é exatamente o dry-run gate necessário para esta migração.
- **`paymaster/detector.py::detect_paymaster()`** — aceita qualquer rede/perfil, sem lógica testnet-específica.
- **`bridge/cctp.py`** — `CCTPBridge.__init__` já resolve contratos a partir do `NetworkProfile` (exceto o bug pontual em A.3) e levanta erro claro quando `cctp_token_messenger is None` para qualquer rede.
- **`agents/identity.py`/`jobs.py`** — `AgentRegistry`/`JobRegistry` sempre exigem endereço de registry explícito do caller; agnósticos de rede por construção.
- **`core/signer.py`** — `Signer` ABC/`LocalKeySigner` totalmente agnóstico de rede.
- **`oracle/price_feed.py`, `privacy/view_key.py`, `contracts/loader.py`, `events/listener.py`, `deploy/deployer.py`, `stablecoins/token.py` (classe base `StablecoinToken`)** — todos operam sobre `w3`/endereço/ABI fornecidos pelo caller, sem default testnet-específico problemático (a única exceção é o default de `USDCToken`, já listado em A.3/A.9.6).

---

## Parte B — Configuração oficial e atual da Arc Mainnet

**Fonte primária:** `docs.arc.io` (site oficial de documentação da Circle para a Arc). Todos os valores abaixo foram extraídos do HTML bruto das páginas oficiais e conferidos byte a byte (não apenas resumidos), em 2026-09-18. Endereços de contrato foram cruzados contra os links `href="https://explorer.arc.io/address/0x..."` / `href="https://explorer.testnet.arc.io/address/0x..."` embutidos na própria página, que amarram cada endereço à rede correta de forma inequívoca.

### B.1 Chain ID

- **Mainnet: `5042`** (`0x13b2`)
- **Testnet: `5042002`** (sem alteração)
- Fonte: `https://docs.arc.io/arc/references/rpc-endpoints`, tabela "Parameter | Value" — verificado 2026-09-18.

### B.2 RPC HTTP

| Rede | Provider | HTTP |
|---|---|---|
| Mainnet | Primary (Circle) | `https://rpc.mainnet.arc.io` |
| Mainnet | Alchemy | `https://arc-mainnet.g.alchemy.com/v2/YOUR_API_KEY` |
| Mainnet | Blockdaemon | `https://rpc.blockdaemon.mainnet.arc.io` |
| Mainnet | dRPC | `https://rpc.drpc.mainnet.arc.io` |
| Mainnet | QuickNode | `https://rpc.quicknode.mainnet.arc.io` |
| Testnet | Primary (Circle) | `https://rpc.testnet.arc.io` |
| Testnet | Blockdaemon | `https://rpc.blockdaemon.testnet.arc.io` |
| Testnet | dRPC | `https://rpc.drpc.testnet.arc.io` |
| Testnet | QuickNode | `https://rpc.quicknode.testnet.arc.io` |

**Nota importante:** o RPC atualmente hardcoded no SDK (`https://arc-testnet.drpc.org`) **não é** o endpoint testnet documentado atualmente (`https://rpc.testnet.arc.io`). Verificar se a URL antiga ainda resolve antes de descontinuá-la na documentação, mas o novo default deve ser o endpoint oficial da Circle.

Fonte: `https://docs.arc.io/arc/references/rpc-endpoints` — verificado 2026-09-18.

### B.3 RPC WebSocket

| Rede | Provider | WebSocket |
|---|---|---|
| Mainnet | Primary (Circle) | **— (não suportado)** |
| Mainnet | Alchemy | `wss://arc-mainnet.g.alchemy.com/v2/YOUR_API_KEY` |
| Mainnet | Blockdaemon | `wss://rpc.blockdaemon.mainnet.arc.io/websocket` |
| Mainnet | dRPC | **— (não suportado)** |
| Mainnet | QuickNode | `wss://rpc.quicknode.mainnet.arc.io` |
| Testnet | Primary (Circle) | `wss://rpc.testnet.arc.io` |
| Testnet | Blockdaemon | `wss://rpc.blockdaemon.testnet.arc.io/websocket` |
| Testnet | dRPC | `wss://rpc.drpc.testnet.arc.io` |
| Testnet | QuickNode | `wss://rpc.quicknode.testnet.arc.io` |

**Diferença notável:** o endpoint primário da Circle para **mainnet é HTTP-only**; o endpoint primário de **testnet suporta HTTP e WS**. `NetworkProfile.ws_rpc_url` deve ficar `None` para o provider primário de mainnet.

Fonte: `https://docs.arc.io/arc/references/rpc-endpoints` — verificado 2026-09-18.

### B.4 Explorers oficiais

- Mainnet: **`https://explorer.arc.io`** (Blockscout)
- Testnet: **`https://explorer.testnet.arc.io`**

Fonte: `https://docs.arc.io/arc/references/connect-to-arc`, `https://docs.arc.io/arc/references/rpc-endpoints` — verificado 2026-09-18.

**Não confirmado / não usar:** "Arcscan" (`arc-scan.org`) apareceu em agregadores de terceiros, sem confirmação em fonte oficial da Circle — **NÃO usar como explorer padrão**.

### B.5 Moeda nativa de gas

- **USDC é o token nativo de gas** (não é ETH nem um token "wrapped").
- Símbolo: `USDC`.
- **Decimais na interface nativa (gas, `msg.value`, `eth_getBalance`): 18** — diferente dos 6 decimais usuais do USDC.

Fonte: `https://docs.arc.io/arc/references/evm-compatibility`, `https://docs.arc.io/arc/references/connect-to-arc`, `https://www.arc.io/blog/building-with-usdc-on-arc-one-token-two-interfaces` — verificado 2026-09-18.

### B.6 USDC — desenho de interface dupla (crítico para o SDK)

Isto **não é um ERC-20 comum**. É um desenho de interface dupla sobre o mesmo saldo:

- **Interface nativa** (como ETH): usada para gas, `msg.value`, `eth_getBalance`. **18 decimais.**
- **Interface ERC-20 opcional**, em endereço fixo de precompile, com os **6 decimais** convencionais de USDC, para compatibilidade com ferramentas ERC-20 existentes (`balanceOf`, `approve`, `transferFrom`, `allowance`).
- **Endereço da interface ERC-20 (idêntico em mainnet e testnet):** `0x3600000000000000000000000000000000000000`
- Um contrato precompilado mantém as duas visões sincronizadas — não existe wrapper token (não há equivalente a WETH).
- **Implicação crítica de design:** nunca misturar as duas escalas decimais. Saldo nativo/gas = 18 decimais (`from_wei(..., "ether")`); `balanceOf` via ERC-20 = 6 decimais. Isso afeta diretamente `StablecoinToken._to_atomic()`/`_from_atomic()` em `stablecoins/token.py`, que hoje assume 6 decimais para tudo relacionado a USDC — precisa de uma via separada e claramente nomeada para ler o saldo nativo (18 decimais) sem confundir com o saldo ERC-20 (6 decimais).

Fonte: `https://docs.arc.io/arc/references/contract-addresses`, `https://docs.arc.io/arc/references/evm-compatibility`, `https://www.arc.io/blog/building-with-usdc-on-arc-one-token-two-interfaces` — verificado 2026-09-18.

### B.7 Endereços de contrato oficiais — verificados byte a byte

Todos os endereços abaixo foram extraídos diretamente do HTML da página oficial e confirmados contra os links `href` que amarram cada um à rede correta (`explorer.arc.io` = mainnet, `explorer.testnet.arc.io` = testnet). Todos têm exatamente 40 caracteres hex (comprimento válido).

| Contrato | Mainnet | Testnet |
|---|---|---|
| USDC (interface ERC-20) | `0x3600000000000000000000000000000000000000` | igual |
| EURC | `0xbEf5f6d51CB62b58e6A8f77868681825C6fe21c1` | `0x89B50855Aa3bE2F677cD6303Cec089B5F319D72a` |
| USYC | `0x8a5D989Bbb96929F689B0200f435f53dA42bF490` | `0xe9185F0c5F296Ed1797AaE4238D26CCaBEadb86C` |
| USYC Entitlements | `0xb69ecb156Dc0028198028c501340d5367845ca72` | `0xcc205224862c7641930c87679e98999d23c26113` |
| USYC Teller | `0x51A8CE47dC08ba5CD19c7aa84EA6fD6664f60f9b` | `0x9fdF14c5B14173D74C08Af27AebFf39240dC105A` |
| CCTP TokenMessengerV2 (domain **26**) | `0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d` | `0x8FE6B999Dc680CcFDD5Bf7EB0974218be2542DAA` |
| CCTP MessageTransmitterV2 | `0x81D40F21F12A8F0E3252Bccb954D722d4c464B64` | `0xE737e5cEBEEBa77EFE34D4aa090756590b1CE275` |
| CCTP TokenMinterV2 | `0xfd78EE919681417d192449715b2594ab58f5D002` | `0xb43db544E2c27092c107639Ad201b3dEfAbcF192` |
| CCTP MessageV2 | `0xec546b6B005471ECf012e5aF77FBeC07e0FD8f78` | `0xbaC0179bB358A8936169a63408C8481D582390C4` |
| Gateway Wallet | `0x77777777Dcc4d5A8B6E418Fd04D8997ef11000eE` | `0x0077777d7EBA4688BDeF3E311b846F25870A19B9` |
| Gateway Minter | `0x2222222d7164433c4C09B0b0D809a9b52C04C205` | `0x0022222ABE238Cc2C7Bb1f21003F0a260052475B` |
| FxEscrow (StableFX) | `0xe2E5F173576B513d994073CCbDaCBE027d43DFe6` | `0x867650F5eAe8df91445971f14d89fd84F0C9a9f8` |
| Memo | `0x5294E9927c3306DcBaDb03fe70b92e01cCede505` | igual |
| Multicall3From | `0x522fAf9A91c41c443c66765030741e4AaCe147D0` | igual |
| CREATE2 Factory (Arachnid) | `0x4e59b44847b379578588920cA78FbF26c0B4956C` | igual |
| Multicall3 (padrão) | `0xcA11bde05977b3631167028862bE2a173976CA11` | igual |
| Permit2 (padrão) | `0x000000000022D473030F116dDEE9F6B43aC78BA3` | igual |

Fonte: `https://docs.arc.io/arc/references/contract-addresses` — extraído e verificado byte a byte em 2026-09-18.

### B.8 Bridges oficiais

- **Circle CCTP v2** — mecanismo de bridging oficialmente documentado. Arc tem **domain 26**. Endereços publicados para ambas as redes (ver B.7).
- **Circle Gateway** — saldos de USDC "chain-abstracted"; endereços publicados para ambas as redes (ver B.7).
- Nenhum outro bridge oficial (token bridge nativo, bridge de terceiros) foi encontrado em fonte oficial — qualquer coisa além de CCTP/Gateway = **NÃO CONFIRMADO**.

Fonte: `https://docs.arc.io/arc/references/contract-addresses` — verificado 2026-09-18.

### B.9 Faucet — apenas testnet

- **`https://faucet.circle.com`** (selecionar "Arc testnet") — distribui USDC de teste diretamente, sem necessidade de compra ou bridge.
- **Não existe faucet de mainnet** (esperado).
- A URL atualmente documentada no SDK (`https://faucet.arc.io`, em `docs/getting-started.md`) está desatualizada e deve ser substituída por `https://faucet.circle.com`.

Fonte: `https://docs.arc.io/arc/references/connect-to-arc` — verificado 2026-09-18.

### B.10 EVM compatibility

- **Fork base: Osaka**, com features do fork futuro **Amsterdam** portadas antecipadamente (notavelmente **EIP-7708**, emissão de log `Transfer` em transferências nativas).
- **Desvios em relação ao Ethereum padrão:**
  - `PREVRANDAO` sempre retorna `0` — sem fonte de aleatoriedade on-chain.
  - `SELFDESTRUCT` segue EIP-6780 + regras específicas da Arc; **reverte** ao mover valor para endereço zero, para si mesmo, ou para uma conta já destruída (diferente do Ethereum padrão).
  - `parentBeaconBlockRoot` retorna o **hash do bloco de execução pai**, não um oráculo de beacon-root funcional — não depender de leituras EIP-4788.
  - Withdrawals (EIP-4895) sempre vazios.
  - Transferências nativas de valor revertem para: endereço zero (valor não-zero), sender/recipient bloqueados, ou precompiles como destinatário.
  - Timestamps de bloco são não-decrescentes, não estritamente crescentes.
  - Base fee é pago ao beneficiário do bloco, **não é queimado** (diferente do modelo de burn do EIP-1559).
  - **Base fee mínimo: 20 Gwei** — transações abaixo disso são descartadas silenciosamente do mempool.

Fonte: `https://docs.arc.io/arc/references/evm-compatibility` — verificado 2026-09-18.

### B.11 Tipos de transação suportados

- Legacy — suportado
- EIP-1559 (type-2) — suportado
- EIP-2930 (access lists, type-1) — suportado
- EIP-7702 (set-code, type-4) — suportado
- **EIP-4844 (blob, type-3) — NÃO suportado**; mempool rejeita. `BLOBHASH` retorna `0`, `BLOBBASEFEE` retorna `1`.

Fonte: `https://docs.arc.io/arc/references/evm-compatibility` — verificado 2026-09-18.

### B.12 Particularidades / limitações do RPC

- A documentação oficial lista apenas categorias padrão de métodos (State, Transactions, Blocks, Gas, Subscriptions) — **não há menção ao namespace `debug_*`** para os endpoints Circle-hospedados (mainnet ou testnet).
- Nenhum limite de rate limit concreto documentado oficialmente — **NÃO CONFIRMADO**.
- Alegações de terceiros (ex.: Chainstack) sobre suporte a `debug_traceTransaction`/`trace_*` referem-se ao **produto próprio deles** ("Global Node" com add-on de debug/trace), não ao RPC padrão da Circle. **Recomendação:** manter o comportamento defensivo já existente em `trace_transaction()` (`supported=False` com mensagem clara) também em mainnet, até confirmação oficial.

Fonte: `https://docs.arc.io/arc/references/rpc-endpoints` — verificado 2026-09-18.

### B.13 Configuração recomendada de wallet

**Mainnet:**

| Campo | Valor |
|---|---|
| Network Name | Arc |
| RPC URL | `https://rpc.mainnet.arc.io` |
| Chain ID | `5042` |
| Currency Symbol | USDC |
| Decimals | 18 |
| Block Explorer | `https://explorer.arc.io` |

**Testnet:**

| Campo | Valor |
|---|---|
| Network Name | Arc Testnet |
| RPC URL | `https://rpc.testnet.arc.io` |
| Chain ID | `5042002` |
| Currency Symbol | USDC |
| Decimals | 18 |
| Block Explorer | `https://explorer.testnet.arc.io` |

Aviso oficial: wallets sem suporte a exibição de token de gas customizado com 18 decimais ainda funcionam para transações, mas podem exibir saldos de forma enganosa.

Fonte: `https://docs.arc.io/arc/references/connect-to-arc` — verificado 2026-09-18.

### B.14 `debug_traceTransaction` em mainnet

**NÃO CONFIRMADO** via fonte oficial. Manter o fallback defensivo existente (`supported=False`) como comportamento padrão também em mainnet.

### B.15 Diferenças conhecidas entre Testnet e Mainnet

1. Chain ID: `5042002` (testnet) → `5042` (mainnet).
2. RPC primário: `rpc.testnet.arc.io` → `rpc.mainnet.arc.io`; **mainnet primário é HTTP-only**, testnet primário suporta HTTP+WS.
3. Explorer: `explorer.testnet.arc.io` → `explorer.arc.io`.
4. Validadores: mainnet roda com um conjunto de validadores nomeado e permissionado (BlackRock, DTCC, Galaxy, Global Payments/Worldpay, ICE, Mastercard, MoneyGram, SBI, Standard Chartered, Sumitomo Corporation, Visa, Circle — fonte: press release da Circle) — distinto do conjunto de validadores da testnet.
5. Faucet: existe só em testnet; sem faucet em mainnet (esperado).
6. Endereços de contrato diferem por rede para EURC, USYC (+ Entitlements/Teller) e todos os contratos CCTP/Gateway; USDC (ERC-20), Memo, Multicall3From, CREATE2 Factory, Multicall3 e Permit2 são idênticos nas duas redes.
7. Acesso de desenvolvedor é permissionless em ambas as redes; apenas participação como validador é permissionada.

Fonte: `https://docs.arc.io/arc/references/rpc-endpoints`, `https://docs.arc.io/arc/references/connect-to-arc`, `https://docs.arc.io/arc/concepts/deployment-model`, press release da Circle — verificado 2026-09-18.

---

## Resumo executivo — ações prioritárias

1. Corrigir o fallback silencioso de `config.py:117` (nunca cair para `5042002` sem aviso explícito).
2. Substituir os três usos hardcoded de `USDC_ARC_TESTNET_ADDRESS` que ignoram `networks.py` (`core/gas.py`, `agents/payment_agent.py`, `bridge/cctp.py`) por resolução via `settings.network.contracts.usdc`.
3. Preencher `NETWORKS["mainnet"]` (e corrigir `NETWORKS["testnet"]`) com os valores verificados na Parte B.
4. Resolver a questão dos 18 vs. 6 decimais do USDC (nativo vs. ERC-20) explicitamente na abstração de saldo — este é o achado técnico mais importante desta auditoria e não estava presente em nenhuma suposição anterior do SDK.
5. Remover/parametrizar strings hardcoded "Arc Testnet" em `cli/flat.py`, `cli/main.py`, `api/main.py`, `analytics/portfolio.py`, `core/connection.py`.
6. Adicionar confirmação pré-broadcast (rede + aviso de fundos reais) em `arc send --broadcast` e `PaymentAgent.execute(enviar=True)`.
7. Atualizar `copilot/agent.py:39` (system prompt desatualizado).
8. Atualizar RPC/faucet/explorer desatualizados em toda a documentação (`arc-testnet.drpc.org` → `rpc.testnet.arc.io`; `faucet.arc.io` → `faucet.circle.com`).
9. Endurecer o default de endereço zero em `USDCToken()`.
10. Reforçar guardrails de gasto/whitelist antes de qualquer uso real em mainnet.
