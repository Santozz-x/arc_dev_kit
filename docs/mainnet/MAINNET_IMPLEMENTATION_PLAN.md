# Mainnet Implementation Plan

Baseado em [`MIGRATION_AUDIT.md`](./MIGRATION_AUDIT.md). Este plano evolui a arquitetura existente — não a reescreve. `networks.py`, `config.py`, e a maioria dos módulos já são network-agnostic por design; o trabalho é majoritariamente preencher placeholders, corrigir os poucos pontos que ignoram essa abstração, e adicionar camadas de segurança para mainnet.

Achado que molda todo o plano: **USDC na Arc tem interface dupla** — nativo (18 decimais, usado para gas/`msg.value`) e ERC-20 via precompile (6 decimais, endereço `0x3600...0000`, idêntico em mainnet/testnet). `StablecoinToken` hoje assume 6 decimais para tudo relacionado a USDC; isso precisa de uma via explícita e separada para saldo nativo.

---

## Phase 1 — Audit

**Status: concluída.** Ver `MIGRATION_AUDIT.md`.

---

## Phase 2 — Network Architecture

**Objetivo:** corrigir e completar `arc_devkit/networks.py` como fonte única de verdade, sem introduzir uma segunda abstração paralela (a estrutura `NetworkProfile`/`ContractAddresses`/`NETWORKS`/`get_network()` já existe e está correta — só falta preenchê-la e estendê-la).

**Arquivos afetados:** `arc_devkit/networks.py`, `arc_devkit/config.py`.

**Implementação:**
- Preencher `NETWORKS["mainnet"]`: `chain_id=5042`, `rpc_url="https://rpc.mainnet.arc.io"`, `ws_rpc_url=None` (primário Circle é HTTP-only), `explorer_url="https://explorer.arc.io"`.
- Corrigir `NETWORKS["testnet"]`: `rpc_url="https://rpc.testnet.arc.io"` (era `arc-testnet.drpc.org`), adicionar `ws_rpc_url="wss://rpc.testnet.arc.io"`, `explorer_url="https://explorer.testnet.arc.io"`.
- Preencher `ContractAddresses` para ambas as redes com os valores verificados em `MIGRATION_AUDIT.md` Parte B.7 (`usdc`, `eurc`, `cctp_token_messenger`, `cctp_message_transmitter`, `gateway_wallet`, `gateway_minter`, `multicall3`, `permit2` — estender o dataclass conforme necessário; hoje só tem 4 campos).
- Adicionar `native_currency_decimals: int = 18` ao `NetworkProfile` (ou constante de módulo), para que qualquer código que leia saldo nativo saiba a escala correta sem hardcode espalhado.
- Corrigir `config.py:117` — remover o fallback silencioso para `5042002`; se não houver `ARC_CHAIN_ID` explícito nem `profile.chain_id`, levantar `OSError` claro (mesmo padrão já usado para `ANTHROPIC_API_KEY`/`ARC_RPC_URL` ausentes).
- Confirmar/documentar que `ARC_NETWORK` default deve virar `"mainnet"` (mudança de comportamento — ver Phase 8 para o plano de compatibilidade).

**Riscos:** mudar o default de `ARC_NETWORK` de testnet para mainnet é uma breaking change de comportamento para qualquer `.env` existente que não defina `ARC_NETWORK` explicitamente (hoje herda testnet implicitamente via ausência de RPC mainnet; depois de preenchido, herdaria mainnet). Mitigação: exigir `ARC_RPC_URL` OU confirmação explícita antes de qualquer operação de escrita quando a rede resolvida for mainnet sem `ARC_NETWORK` ter sido setado (ver Phase 8).

**Testes:** `tests/test_networks.py` (novo/estendido) cobrindo `get_network("mainnet")`, valores de `NETWORKS["mainnet"]`, e o novo comportamento de erro de `config.py` quando chain ID não pode ser resolvido.

**Critério de conclusão:** `arcdevkit network show mainnet` e `arcdevkit network check-mainnet` passam sem placeholders `None` restantes exceto os campos genuinamente não publicados (nenhum, após esta fase).

---

## Phase 3 — RPC

**Objetivo:** garantir que toda operação RPC (`get_block`, `get_transaction`, `get_transaction_receipt`, `get_balance`, `get_code`, `eth_call`, `estimate_gas`, `send_raw_transaction`, `get_logs`) funcione contra mainnet com tratamento de erro claro, e que `core/connection.py` não carregue mais comentários testnet-específicos incorretos.

**Arquivos afetados:** `arc_devkit/core/connection.py`, `arc_devkit/core/wallet.py`, `arc_devkit/core/gas.py`.

**Implementação:**
- Atualizar comentários de `connection.py` sobre PoA middleware (não é exclusivo de testnet — mainnet também roda validadores permissionados).
- Adicionar mensagens de erro específicas quando o RPC rejeitar por: base fee abaixo do mínimo de 20 Gwei (mempool derruba silenciosamente — Audit B.10), tipo de transação não suportado (EIP-4844/blob — B.11), ou `debug_*` desabilitado (já tratado em `tx_analyzer.py`, confirmar que se aplica igualmente a mainnet).
- Não implementar suporte a EIP-4844 (blobs) em lugar nenhum — Arc não suporta.

**Riscos:** baixo — são mudanças aditivas de tratamento de erro, não de comportamento de assinatura.

**Testes:** testes unitários mockando respostas de erro do RPC (base fee rejeitado, tipo de tx rejeitado); manter testes de integração existentes marcados `@pytest.mark.integration`.

**Critério de conclusão:** chamadas RPC básicas (`arcdevkit status`, `arc balance`) funcionam contra `rpc.mainnet.arc.io` real (validação manual, read-only).

---

## Phase 4 — USDC

**Objetivo:** resolver a questão nativo (18 decimais) vs. ERC-20 (6 decimais) e remover os hardcodes de endereço.

**Arquivos afetados:** `arc_devkit/stablecoins/token.py`, `arc_devkit/usdc/token.py`, `arc_devkit/core/gas.py`, `arc_devkit/agents/payment_agent.py`, `arc_devkit/bridge/cctp.py`.

**Implementação:**
- Remover `USDC_ARC_TESTNET_ADDRESS` como constante de import direto em `core/gas.py`, `agents/payment_agent.py`, `bridge/cctp.py` — substituir por resolução via `settings.network.contracts.usdc` (ou o `NetworkProfile` recebido explicitamente).
- `USDCToken.__init__`: remover o default de endereço zero; exigir `contract_address` explícito ou resolver automaticamente de `settings.network.contracts.usdc` quando omitido (nunca cair silenciosamente em `0x000...000`).
- Adicionar um método/propriedade explícito para saldo **nativo** (18 decimais) distinto de `balance()` (que continua sendo o saldo ERC-20, 6 decimais) — nome sugerido: `native_balance()` ou equivalente, documentando a diferença de escala no docstring.
- Manter `_to_atomic()`/`_from_atomic()` (6 decimais) como estão para a via ERC-20; criar conversão separada para a via nativa (18 decimais) — não reutilizar a mesma função para as duas escalas.

**Riscos:** alto impacto se a distinção 18/6 decimais não for feita corretamente — erro aqui causa leitura de saldo incorreta (não perda de fundos diretamente, mas decisões erradas baseadas em saldo errado). Testar exaustivamente contra valores conhecidos antes de expor a API.

**Testes:** testes unitários com mocks de `eth_getBalance` (18 decimais) vs. `balanceOf` (6 decimais) verificando que a conversão nunca mistura as escalas; teste de regressão garantindo que nenhum código legado que espera 6 decimais receba um valor de 18 decimais sem conversão.

**Critério de conclusão:** `arc.usdc.balance(address)` (ERC-20) e o equivalente nativo retornam valores corretos e claramente distintos contra mainnet real (validação manual read-only).

---

## Phase 5 — Transaction Debugger

**Objetivo:** `TxAnalyzer` funcionando contra mainnet, com qualquer comportamento Arc-específico identificado (ex.: `SELFDESTRUCT` revertendo em vez de suceder, ausência de `debug_*`).

**Arquivos afetados:** `arc_devkit/debugger/tx_analyzer.py`.

**Implementação:**
- Confirmar que `analyze()` e `trace_transaction()` funcionam sem alteração estrutural contra mainnet (já são network-agnostic — recebem `rpc_url`/`w3`).
- Garantir que o relatório inclua o nome da rede (mainnet/testnet) explicitamente, não apenas o chain ID cru, para que o usuário nunca confunda os dois.
- Adicionar ao prompt de análise de IA (`DevCopilot.ask()` via `tx_analyzer.py`) contexto sobre os desvios EVM da Arc (B.10 do audit) para que a análise de erros de transação não presuma comportamento Ethereum padrão.

**Riscos:** baixo — mudanças aditivas de contexto/apresentação.

**Testes:** `tests/test_debugger.py` com casos mockados incluindo uma tx de mainnet (fixture nova) além das existentes de testnet.

**Critério de conclusão:** `arcdevkit debug tx <hash>` produz relatório correto e identificado por rede contra uma tx real de mainnet.

---

## Phase 6 — Contracts

**Objetivo:** validar que `contracts/loader.py`, `events/listener.py`, `deploy/deployer.py` funcionam sem alteração contra mainnet (já são agnósticos de rede) e documentar isso.

**Arquivos afetados:** nenhuma mudança de código esperada; apenas validação e exemplos novos (Phase 9).

**Riscos:** nenhum — módulos já corretos por design.

**Testes:** exemplo `examples/mainnet/07_contract_read.py` / `08_contract_write.py` como teste de fumaça manual.

**Critério de conclusão:** leitura de um contrato conhecido em mainnet (ex.: Multicall3 em `0xcA11bde0...`) funciona via `contract.call(...)`.

---

## Phase 7 — CLI

**Objetivo:** CLI reflete a rede ativa em vez de assumir "Arc Testnet" hardcoded, e adiciona os comandos novos pedidos (`arc doctor`, comandos read-only equivalentes já existem em boa parte via `network`/`status`/`debug`).

**Arquivos afetados:** `arc_devkit/cli/flat.py`, `arc_devkit/cli/main.py`, `arc_devkit/cli/commands/network.py`, novo `arc_devkit/cli/commands/doctor.py`.

**Implementação:**
- `arc status`/`arcdevkit status`: substituir texto hardcoded "Arc Testnet" por `settings.arc_network`/`settings.network.name`, exibido com destaque visual diferenciando mainnet de testnet (ex.: cor/badge diferente).
- Implementar `arcdevkit doctor` / `arc doctor`: RPC reachability, chain ID match (RPC reportado vs. `settings.arc_chain_id`), latência, bloco mais recente, checagem do contrato USDC, explorer configurado — formato de saída conforme especificado na Phase 8/seção de safety.
- `--network testnet|mainnet` como flag global do CLI, sobrepondo `ARC_NETWORK` para a invocação (não persiste em `.env`).
- Não remover nenhum comando existente; apenas parametrizar textos hardcoded.

**Riscos:** médio — mudança de UX visível para usuários existentes de testnet (vão ver "Arc Mainnet" onde antes viam "Arc Testnet" fixo, mesmo que a rede real não tenha mudado, porque hoje o texto ignora a config).

**Testes:** `tests/test_cli.py`, `tests/test_cli_network.py` — asserts sobre o texto de rede exibido variando com `ARC_NETWORK`; novo `tests/test_cli_doctor.py`.

**Critério de conclusão:** `arc status` e `arcdevkit status` exibem a rede correta em ambos os valores de `ARC_NETWORK`; `arc doctor` roda e reporta `READY`/`NOT READY` com base em checagens reais.

---

## Phase 8 — Safety

**Objetivo:** proteções de mainnet — confirmação antes de operações de fundo real, diferenciação visual clara, validação de chain ID, flags de automação.

**Arquivos afetados:** `arc_devkit/cli/flat.py` (`arc send`), `arc_devkit/agents/payment_agent.py`, `arc_devkit/bridge/cctp.py`, `arc_devkit/config.py`.

**Implementação:**
- `arc send --broadcast`: antes de assinar, imprimir `Network: ARC MAINNET` (ou TESTNET) + `WARNING: This transaction uses real funds.` quando a rede resolvida for mainnet, e exigir confirmação interativa (`typer.confirm`) a menos que `--yes`/`--force` seja passado.
- Mesmo padrão para `PaymentAgent.execute()` quando chamado fora de modo agente automatizado — expor um parâmetro `confirm: bool = True` (ou equivalente) que a CLI usa, mas que agentes/automação podem desabilitar explicitamente via `--yes`.
- `CCTPBridge.start_transfer()`: mesmo aviso antes de queimar USDC cross-chain.
- Validar chain ID do RPC ao vivo (`w3.eth.chain_id`) contra `settings.arc_chain_id` resolvido no boot da aplicação (não só em `config.py`), levantando erro claro em caso de divergência — evita conexão acidental na rede errada.
- Não alterar comportamento de `.env`/guardrails automaticamente; apenas fortalecer a documentação (Phase 10) para desencorajar guardrails vazios em produção — mudar o default de comportamento de `Guardrails` é fora de escopo (quebraria automações legítimas silenciosamente).

**Riscos:** este é o phase de maior risco de regressão de UX — confirmações demais quebram automação legítima. Mitigação: toda confirmação nova tem flag de bypass (`--yes`/`--force`), documentada explicitamente.

**Testes:** `tests/test_cli.py` — cenário de `arc send --broadcast` sem `--yes` em mainnet aborta sem broadcast; com `--yes` prossegue; testnet não exige confirmação (ou exige uma versão mais branda — decidir com o usuário se testnet também deve pedir confirmação).

**Critério de conclusão:** nenhum caminho de código envia transação real em mainnet sem confirmação explícita (interativa ou via flag).

---

## Phase 9 — Examples

**Objetivo:** `examples/mainnet/` com os 10 scripts pedidos, cada um com aviso claro quando envolver fundos reais.

**Arquivos afetados:** novo diretório `examples/mainnet/`.

**Implementação:** `01_connect.py` … `10_deploy_contract.py` conforme especificado no pedido original, todos usando `Arc.mainnet()` (ou API equivalente da Phase 2/arquitetura — ver `ARC_DEVKIT_ARCHITECTURE.md`), com comentário de aviso em todo exemplo que assina/envia (`05_transaction.py`, `08_contract_write.py`, `09_send_transaction.py`, `10_deploy_contract.py`).

**Riscos:** baixo.

**Testes:** smoke test que importa cada exemplo (sem executar chamadas de rede reais em CI) para garantir que não há erro de sintaxe/import.

**Critério de conclusão:** todos os 10 exemplos existem, rodam contra testnet como validação segura, e têm avisos claros de mainnet.

---

## Phase 10 — Documentation

**Objetivo:** `docs/mainnet/*.md` completo conforme lista do pedido original, e correção de toda menção desatualizada de testnet/RPC/faucet identificada na Parte A do audit.

**Arquivos afetados:** `docs/mainnet/` (novos arquivos), `README.md`, `docs/getting-started.md`, `docs/index.md`, `docs/migration-rpc.md`, `docs/cli-guide.md`, `docs/modules/*.md`, `copilot/agent.py` (system prompt).

**Implementação:** cada um dos arquivos listados no pedido (`README.md`, `GETTING_STARTED.md`, `NETWORK_CONFIG.md`, `USDC.md`, `TRANSACTIONS.md`, `GAS_AND_FEES.md`, `SMART_CONTRACTS.md`, `WALLETS.md`, `TRANSACTION_DEBUGGER.md`, `CLI.md`, `SECURITY.md`, `MIGRATION_FROM_TESTNET.md`) — `MIGRATION_AUDIT.md` já está pronto. Corrigir `copilot/agent.py:39` (system prompt desatualizado — maior prioridade de conteúdo, pois afeta respostas de IA em produção).

**Riscos:** baixo, mas alto volume — risco principal é inconsistência entre documentos (ex.: um doc atualizado, outro esquecido). Mitigação: grep final por `testnet`, `arc-testnet.drpc.org`, `faucet.arc.io`, `5042002` como único valor, `summer 2026` antes de fechar a fase.

**Testes:** não aplicável (documentação); validação manual + grep de varredura final (Phase 19 do pedido original).

**Critério de conclusão:** nenhuma ocorrência de informação de rede desatualizada sobrevive a uma varredura grep final.

---

## Phase 11 — Tests

**Objetivo:** cobertura para o caminho mainnet sem nunca enviar dinheiro real em CI.

**Arquivos afetados:** `tests/` (novos arquivos e extensões), `.github/workflows/ci.yml`.

**Implementação:**
- Testes unitários: mockar `NETWORKS["mainnet"]` preenchido, `config.py` resolvendo mainnet corretamente, `get_network("mainnet")`.
- Testes de integração read-only (marcados `@pytest.mark.integration`, skip por padrão): chain ID real, latest block, lookup de tx conhecida, leitura de contrato conhecido (Multicall3), saldo USDC — todos contra `rpc.mainnet.arc.io` real, sem nenhuma operação de escrita.
- Nenhum teste deve fazer broadcast de transação real ou mover fundos reais, em nenhum ambiente de CI.
- Separar claramente no `README`/`CONTRIBUTING` (ou neste plano) a distinção unit vs. integration vs. mainnet-read-only.

**Riscos:** testes de integração contra mainnet real introduzem flakiness dependente de rede externa — devem ficar fora do CI padrão (mesma convenção já usada para testnet).

**Testes:** meta-nível — este é o próprio phase de testes.

**Critério de conclusão:** suíte completa passa (`pytest`), cobertura ≥ 80% mantida, nenhum teste novo requer fundos reais ou chave privada real.

---

## Phase 12 — Release

**Objetivo:** nova versão SemVer, `CHANGELOG.md` atualizado, relatório final.

**Arquivos afetados:** `pyproject.toml`, `CHANGELOG.md`, `docs/mainnet/MAINNET_MIGRATION_REPORT.md`.

**Implementação:**
- Versão: projeto está em `0.8.0`, ainda `Alpha`. Mudar o `ARC_NETWORK` default para mainnet e adicionar suporte oficial a mainnet é uma mudança de comportamento default (não quebra API pública em si, mas muda o que acontece sem configuração explícita) — recomenda-se **`0.9.0`** (MINOR, não MAJOR, porque o pacote ainda está em Alpha pré-1.0 onde MINOR já pode carregar mudanças de comportamento por convenção SemVer 0.x; MAJOR fica reservado para quando o pacote sair de Alpha). Decisão final cabe ao usuário — não escolher arbitrariamente sem confirmar.
- `CHANGELOG.md`: nova seção "Arc Mainnet Support" listando as mudanças reais implementadas (não a lista aspiracional do pedido original).
- Gerar `MAINNET_MIGRATION_REPORT.md` ao final, com a checklist de validação honesta (marcar `NOT VALIDATED` onde aplicável).

**Riscos:** nenhum além dos já cobertos.

**Critério de conclusão:** `pytest` verde, `ruff check .` limpo, CHANGELOG e versão atualizados, relatório final publicado.

---

## Ordem de dependência entre phases

```
Phase 2 (Networks) ──┬─→ Phase 3 (RPC) ──┬─→ Phase 5 (Debugger)
                      ├─→ Phase 4 (USDC) ─┤
                      ├─→ Phase 6 (Contracts)
                      └─→ Phase 7 (CLI) ──→ Phase 8 (Safety)
                                                  │
Phase 9 (Examples) ←──────────────────────────────┘
Phase 10 (Docs) ← todas as anteriores
Phase 11 (Tests) ← todas as anteriores
Phase 12 (Release) ← todas as anteriores
```

Phase 2 é bloqueante para praticamente tudo — é o trabalho a ser priorizado primeiro na implementação real.
