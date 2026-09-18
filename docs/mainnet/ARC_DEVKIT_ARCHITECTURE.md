# Arc DevKit — Architecture Map (Mainnet-ready)

## Arquitetura atual (0.8.0)

O SDK hoje é organizado por módulo, sem uma fachada única — cada funcionalidade é uma classe/função importada diretamente (`DevCopilot`, `PaymentAgent`, `TxAnalyzer`, `USDCToken`, `EventListener`, etc.), todas lendo a rede ativa a partir do singleton `arc_devkit.config.settings`, que por sua vez resolve `arc_devkit.networks.NETWORKS[ARC_NETWORK]`.

```
Developer
   │
   ▼
arc_devkit.config.settings (singleton, lido de env/.env)
   │
   ├──→ arc_devkit.networks.NETWORKS["testnet" | "mainnet"]
   │        (NetworkProfile: chain_id, rpc_url, ws_rpc_url, explorer_url, contracts)
   │
   ├──→ core.connection.get_web3()      → web3.py + PoA middleware
   ├──→ core.wallet / core.signer       → assinatura local ou pluggable
   ├──→ core.gas.quote_fee()            → cotação de fee (nativo/USDC)
   │
   ├──→ debugger.TxAnalyzer             → eth_getTransaction/Receipt + IA
   ├──→ analytics.PortfolioAnalyzer     → snapshots de saldo + histórico
   ├──→ stablecoins.USDCToken/EURCToken → ERC-20 (6 decimais)
   ├──→ contracts.loader                → load_abi/call_view/send_tx/decode_events
   ├──→ events.EventListener            → polling de eth_getLogs
   ├──→ deploy.ContractDeployer         → deploy ABI+bytecode ou Solidity
   ├──→ bridge.CCTPBridge               → CCTP burn→attestation→mint
   ├──→ paymaster.detect_paymaster      → ERC-4337 (ainda não publicado na Arc)
   ├──→ oracle.PriceOracle              → Chainlink AggregatorV3Interface
   ├──→ privacy.view_key                → ECIES (funcional, genérico)
   ├──→ agents.BaseAgent / PaymentAgent / MonitorAgent / JobAgent / CoordinatorAgent
   ├──→ agents.identity.AgentRegistry / agents.jobs.JobRegistry (ERC-8004/8183)
   ├──→ copilot.DevCopilot               → wrapper do Claude, ferramentas read-only
   │
   ├──→ api/  (FastAPI: copilot, agents/monitor WS, fees, bridge, jobs)
   │
   └──→ cli/
          ├── flat.py   (`arc ...`)
          ├── main.py   (`arcdevkit ...`, agrupado)
          └── commands/ (agent, copilot, debug, network, fees, bridge, mcp, oracle, privacy)
                 │
                 ▼
            Arc Network (RPC HTTP/WS)
```

**Ponto central de verdade:** `arc_devkit/networks.py`. Qualquer módulo que precise de chain ID, RPC, explorer ou endereço de contrato deve ler de `settings.network` (via `NetworkProfile`), nunca hardcodar. Hoje três módulos violam essa regra (`core/gas.py`, `agents/payment_agent.py`, `bridge/cctp.py` — ver `MIGRATION_AUDIT.md` §A.3); corrigi-los é a mudança estrutural mais importante do plano.

## O que muda para suportar Mainnet como cidadã de primeira classe

Nenhum módulo listado acima muda de forma. O que muda:

1. **`networks.py`** deixa de ter `None` em `NETWORKS["mainnet"]` — passa a ter valores reais e verificados (chain ID `5042`, RPC `rpc.mainnet.arc.io`, explorer `explorer.arc.io`, endereços de contrato — ver `MIGRATION_AUDIT.md` Parte B).
2. **`config.py`** — `ARC_NETWORK` passa a default para `"mainnet"` em vez de `"testnet"` (ver Phase 8 do plano para as proteções que acompanham essa mudança); o fallback silencioso de chain ID é removido.
3. **USDC ganha uma segunda via de leitura** — saldo nativo (18 decimais, é o próprio gas token) separado do saldo ERC-20 (6 decimais, endereço `0x3600...0000`). Isso é uma característica real da Arc, não uma escolha de design do SDK, e afeta diretamente `stablecoins/token.py`.
4. **CLI e mensagens de IA passam a refletir a rede ativa** em vez de textos hardcoded "Arc Testnet".
5. **Uma camada de segurança pré-broadcast** é adicionada nos caminhos que assinam/enviam transações reais (`arc send`, `PaymentAgent.execute`, `CCTPBridge`).

## Proposta: fachada `Arc` (nova, aditiva, opcional)

O pedido original descreve uma experiência de entrada do tipo:

```python
from arc_devkit import Arc

arc = Arc.mainnet()
balance = arc.get_balance("0x...")
tx = arc.get_transaction("0x...")
receipt = arc.wait_for_transaction("0x...")
```

Isso **não existe hoje** — o SDK atual não tem uma classe de fachada única; o padrão atual é `from arc_devkit.debugger import TxAnalyzer`, `from arc_devkit.stablecoins.token import USDCToken`, etc., cada um instanciado separadamente com sua própria config de rede.

Proposta: adicionar `arc_devkit.Arc` como uma **camada de conveniência aditiva** sobre os módulos existentes — não uma reescrita:

```
Arc (nova classe fachada)
   │
   ├── Arc.mainnet(rpc_url=None)   → constrói com NETWORKS["mainnet"], override opcional de RPC
   ├── Arc.testnet(rpc_url=None)   → idem para testnet
   ├── Arc(network="mainnet"|"testnet"|NetworkProfile)
   │
   ├── .network            → NetworkProfile ativo
   ├── .get_balance(addr)  → delega a core.wallet / w3.eth.get_balance
   ├── .get_transaction(h) → delega a w3.eth.get_transaction
   ├── .wait_for_transaction(h) → delega a w3.eth.wait_for_transaction_receipt
   ├── .latest_block()     → delega a w3.eth.get_block("latest")
   ├── .debug_transaction(h) → delega a debugger.TxAnalyzer (instanciado internamente)
   ├── .usdc                → StablecoinToken/USDCToken já configurado com a rede ativa
   ├── .gas                 → wrapper fino sobre core.gas.quote_fee
   ├── .contract(address, abi) → wrapper fino sobre contracts.loader
   └── .health_check()      → mesma lógica de `arcdevkit doctor`
```

Cada método de `Arc` é um wrapper fino que instancia e delega para as classes já existentes (`TxAnalyzer`, `USDCToken`, `get_web3()`, etc.) — **não duplica lógica**. Isso mantém 100% de compatibilidade retroativa: quem já usa `from arc_devkit.debugger import TxAnalyzer` continua funcionando sem nenhuma mudança; `Arc` é só uma porta de entrada mais simples para quem está começando.

**Esta é uma decisão de escopo, não uma obrigação técnica** — a auditoria não encontrou nenhuma razão estrutural para não ter essa fachada, mas ela representa uma superfície de API pública nova que precisa ser mantida daqui para frente. Confirmar com o usuário antes de comprometer a este design antes da implementação.

## Compatibilidade com Testnet

Testnet continua sendo uma opção de primeira classe, nunca removida:

```python
arc = Arc.testnet()
# ou
arc = Arc(network="testnet")
# ou, no padrão atual (continua funcionando sem alteração):
from arc_devkit.debugger import TxAnalyzer
analyzer = TxAnalyzer(rpc_url="https://rpc.testnet.arc.io")
```

O único comportamento que muda é o **default implícito** quando nenhuma rede é especificada (`ARC_NETWORK` não setado) — que passa de testnet para mainnet, seguindo a diretriz do pedido original. Essa mudança de default é a única breaking change de comportamento deste plano, e está documentada explicitamente em `MIGRATION_FROM_TESTNET.md` (Phase 10) e protegida por uma exigência de configuração explícita antes de qualquer operação de escrita (Phase 8).
