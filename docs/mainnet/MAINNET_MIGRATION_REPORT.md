# Arc Mainnet Migration Report

**Date:** 2026-09-18
**Version:** `0.8.0` → `0.9.0`
**Scope:** Add native, first-class Arc Mainnet support to Arc DevKit, following [`MAINNET_IMPLEMENTATION_PLAN.md`](MAINNET_IMPLEMENTATION_PLAN.md), built on [`MIGRATION_AUDIT.md`](MIGRATION_AUDIT.md) and [`ARC_DEVKIT_ARCHITECTURE.md`](ARC_DEVKIT_ARCHITECTURE.md).

## Resumo

Arc DevKit agora trata a Arc Mainnet como rede de primeira classe: `arc_devkit/networks.py` tem configuração completa e verificada para mainnet e testnet (chain ID, RPC, WS RPC, explorer, e endereços de contrato para USDC/EURC/USYC/CCTP V2/Gateway/Multicall3/Permit2), o default do SDK passou de testnet para mainnet, e uma nova fachada `arc_devkit.Arc` oferece a experiência de entrada pedida (`Arc.mainnet()`, `arc.get_balance()`, `arc.debug_transaction()`, etc.) sem duplicar lógica dos módulos existentes. Nada foi reescrito — a arquitetura por módulo já era, em grande parte, agnóstica de rede; o trabalho real foi preencher `networks.py`, corrigir três lugares que ignoravam essa abstração com um endereço de teste hardcoded, endurecer `config.py` contra um fallback silencioso perigoso, e adicionar as camadas de segurança/documentação/exemplos pedidas.

## Arquitetura anterior

- `NETWORKS["testnet"]` preenchido; `NETWORKS["mainnet"]` com todos os campos `None` (placeholder explícito).
- `DEFAULT_NETWORK = "testnet"`.
- `USDCToken()` default para `0x000...000` (endereço zero, placeholder).
- `core/gas.py`, `agents/payment_agent.py`, `bridge/cctp.py` importavam `USDC_ARC_TESTNET_ADDRESS` diretamente, ignorando `settings.network`.
- `config.py` caía silenciosamente em chain ID `5042002` (testnet) se nenhum outro valor fosse resolvido.
- CLI (`arc status`, `arcdevkit status`) exibia "Arc Testnet" hardcoded, independente da rede configurada.
- System prompt do Copilot afirmava "mainnet expected Summer 2026" como fato.
- Nenhuma confirmação antes de broadcast de transação real.
- Nenhuma fachada única — só módulos individuais.

## Arquitetura atual

- `NETWORKS["mainnet"]` e `NETWORKS["testnet"]` totalmente preenchidos e verificados byte a byte contra `docs.arc.io` (2026-09-18) — ver `MIGRATION_AUDIT.md` Parte B.
- `DEFAULT_NETWORK = "mainnet"` (mudança de comportamento deliberada e aprovada).
- `USDCToken()` default para o endereço ERC-20 real (`0x3600...0000`, idêntico nas duas redes).
- Novo `native_usdc_balance()` para o saldo nativo (18 decimais) — distinto do saldo ERC-20 (6 decimais).
- `core/gas.py`, `agents/payment_agent.py`, `bridge/cctp.py` resolvem o endereço USDC via `settings.network.contracts.usdc`.
- `config.py` levanta `OSError` claro em vez de cair silenciosamente em outro chain ID.
- CLI reflete a rede ativa, com destaque visual (vermelho) e aviso de fundos reais em mainnet.
- `arc send --broadcast` / `arcdevkit bridge send` exigem confirmação (ou `--yes`) em mainnet.
- Novo `arc_devkit.Arc` (fachada aditiva) e `arc_devkit.health` (compartilhado entre `Arc.health_check()` e `arc doctor`/`arcdevkit doctor`).
- `docs/mainnet/` completo; `examples/mainnet/` com 10 scripts (7 validados ao vivo contra mainnet real).

## Arquivos modificados (principais)

`arc_devkit/networks.py`, `config.py`, `stablecoins/token.py`, `core/gas.py`, `core/connection.py`, `agents/payment_agent.py`, `bridge/cctp.py`, `debugger/tx_analyzer.py`, `cli/flat.py`, `cli/main.py`, `cli/commands/network.py`, `cli/commands/bridge.py`, `cli/commands/debug.py`, `api/main.py`, `copilot/agent.py`, `playground/arc_explorer.py`, `README.md`, `CLAUDE.md`, `CHANGELOG.md`, `MAINNET_CHECKLIST.md`, `pyproject.toml`, `.env.example`, `docs/getting-started.md`, `docs/index.md`, `docs/migration-rpc.md`, `tests/conftest.py` + ~10 test files.

## Funcionalidades adicionadas

- `arc_devkit.Arc` — fachada (`client.py`, novo).
- `arc_devkit.health` — health check compartilhado (novo).
- `arc doctor` / `arcdevkit doctor` (CLI, novo, via `cli/doctor.py`).
- `native_usdc_balance()` e `USDCToken.transfer_from()` (`stablecoins/token.py`).
- Confirmação de mainnet antes de broadcast (`arc send`, `arcdevkit bridge send`), com flag `--yes`.
- Campo `network` em todo resultado de `TxAnalyzer.analyze()`.
- Suporte a CCTP V2 (`depositForBurn` com `destinationCaller`/`maxFee`/`minFinalityThreshold`) em `CCTPBridge`.
- 8 novos campos em `ContractAddresses` (CCTP message transmitter/token minter/message/domain, Gateway wallet/minter separados, multicall3, permit2) + `ws_rpc_url`/`native_currency_symbol`/`native_currency_decimals` em `NetworkProfile`.
- `examples/mainnet/` (10 scripts) e `docs/mainnet/` (12 documentos).

## Funcionalidades reaproveitadas sem mudança

`contracts/loader.py`, `events/listener.py`, `deploy/deployer.py`, `core/signer.py`, `oracle/price_feed.py`, `privacy/view_key.py`, `agents/identity.py`/`jobs.py` (ERC-8004/8183), `paymaster/detector.py`, `arcdevkit network list|show|check-mainnet` — todos já eram agnósticos de rede por design e não precisaram de nenhuma alteração estrutural.

## Breaking changes

**Uma:** o default de `ARC_NETWORK` mudou de `testnet` para `mainnet`. Qualquer `.env` existente sem `ARC_NETWORK` explícito agora aponta para mainnet real na próxima execução. Documentado em `CHANGELOG.md` e `docs/mainnet/MIGRATION_FROM_TESTNET.md`, mitigado pelos novos prompts de confirmação de mainnet no CLI.

Nenhuma outra API pública foi removida ou teve assinatura alterada de forma incompatível — `USDCToken()` sem argumento continua funcionando (só que agora aponta para um endereço real em vez de zero), `USDC_ARC_TESTNET_ADDRESS` continua importável (alias depreciado).

## Compatibilidade com Testnet

Total. `Arc.testnet()`, `ARC_NETWORK=testnet`, e todo import por módulo (`from arc_devkit.debugger import TxAnalyzer`, etc.) continuam funcionando exatamente como antes. Testes unitários usam `ARC_NETWORK=testnet` explicitamente por padrão (`tests/conftest.py`) para permanecerem determinísticos independente do default do pacote.

## Arc Mainnet configuration

Chain ID `5042`, RPC `https://rpc.mainnet.arc.io`, explorer `https://explorer.arc.io` — todos verificados ao vivo (ver seção de validação abaixo). Endereços de contrato extraídos byte a byte do HTML oficial de `docs.arc.io/arc/references/contract-addresses` e cruzados contra os links `explorer.arc.io`/`explorer.testnet.arc.io` embutidos na própria página. Fonte completa: `MIGRATION_AUDIT.md` Parte B.

## USDC support

USDC tem interface dupla na Arc (nativo, 18 decimais / ERC-20, 6 decimais, mesmo saldo). Implementado e testado: `arc.get_balance()` (nativo), `arc.usdc.balance()` (ERC-20), `native_usdc_balance()`, `USDCToken` completo (`balance`, `transfer`, `transfer_from`, `approve`, `allowance`). Validado ao vivo contra mainnet (endereço zero, saldo 0 em ambas as interfaces, contrato confirmado deployado via `eth_getCode`).

## Transaction Debugger

`TxAnalyzer.analyze()`/`arc.debug_transaction()` testados ao vivo contra uma transação real de mainnet (hash `0xc4ccf6...`, status `success`, custo `0.010980517392` USDC) com `use_ai=False`. O campo `network` no resultado agora identifica corretamente a rede. Análise de IA (com `use_ai=True`, requer `ANTHROPIC_API_KEY` real) **não foi exercida nesta sessão** — o caminho de código é o mesmo já testado por `tests/test_debugger.py`, mas a chamada real ao Claude não foi validada ao vivo aqui.

## CLI

`arc status`/`arcdevkit status`/`arc doctor`/`arcdevkit doctor`/`arcdevkit network show|list|check-mainnet` testados ao vivo contra mainnet e testnet reais (via `CliRunner`, não apenas mocks). `arc send --broadcast` com confirmação de mainnet testado com mocks (não foi executado com fundos reais — nenhuma transação de teste foi enviada nesta sessão).

## Security protections

Ver `docs/mainnet/SECURITY.md`. Implementado: prompt de confirmação pré-broadcast em mainnet (CLI), correção do fallback silencioso de chain ID, endurecimento do default de `USDCToken()`. **Não implementado nesta sessão:** varredura de segurança (`bandit`/`pip-audit`) contra o código alterado, flag `--network` por comando.

## Tests

525 testes passam (era ~499 antes desta migração — 26 novos, incluindo `tests/test_client.py`, `tests/test_health.py`, `tests/test_cli_doctor.py`), 8 skipped (integration, requerem rede — não rodados em CI por padrão), cobertura 84.72% (mínimo exigido: 80%). `ruff check`/`ruff format --check` limpos. `mypy arc_devkit`: 23 erros — **idênticos, byte a byte, aos 23 erros já presentes antes desta migração** (confirmado via `git stash` + comparação direta); nenhum erro novo foi introduzido, e nenhum dos pré-existentes foi corrigido (fora de escopo desta migração — não relacionados a rede/mainnet).

Nenhum teste automatizado envia fundos reais ou faz deploy real. Validação ao vivo contra mainnet real (fora da suíte pytest, manual, read-only) está documentada na checklist abaixo.

## Known limitations

1. **CCTP V2 ABI não validado ao vivo.** `depositForBurn`/`receiveMessage` foram atualizados para a assinatura V2 documentada publicamente pela Circle, mas nunca foram exercidos contra um contrato CCTP real da Arc nesta sessão (exigiria fundos de teste e um segundo chain de destino).
2. **API de attestation do CCTP tem um problema público conhecido não resolvido** para o domain 26 da Arc Testnet ([circlefin/evm-cctp-contracts#110](https://github.com/circlefin/evm-cctp-contracts/issues/110), aberto 2026-06-15, sem resposta visível). Não corrigível pelo SDK — depende da Circle.
3. **Sem flag `--network` por comando no CLI** — troca de rede exige mudar `ARC_NETWORK` no ambiente.
4. **`debug_traceTransaction` em mainnet/testnet: não confirmado** via fonte oficial se o RPC padrão da Circle expõe o namespace `debug_*`. Comportamento defensivo (`supported=False`) mantido.
5. **`mypy arc_devkit` já falhava antes desta migração** (23 erros pré-existentes, não relacionados a rede) — não corrigido, fora de escopo.
6. **`docs/cli-guide.md`, `docs/modules/agent-starter-kit.md`, `docs/modules/analytics.md`, `docs/cookbook.md`, e todo o site em `website/`** ainda contêm referências a testnet/RPC antigas que não foram varridas nesta sessão — o núcleo do pacote Python e sua documentação principal (`README.md`, `docs/getting-started.md`, `docs/index.md`, `docs/mainnet/`) foram completamente atualizados; essas páginas secundárias não foram.
7. **Análise de IA do Transaction Debugger** (`use_ai=True`) não foi exercida ao vivo nesta sessão — só o caminho `use_ai=False` foi validado contra mainnet real.
8. **Nenhuma transação real foi enviada** durante esta migração — todo teste de escrita (`arc send --broadcast`, deploy, CCTP) foi validado apenas via mocks/testes unitários, nunca contra fundos reais.

## Future improvements

- Implementar flag `--network` por comando no CLI.
- Validar CCTP V2 end-to-end em testnet com fundos reais pequenos, incluindo a etapa de attestation (ou documentar um workaround caso o issue #110 continue sem solução).
- Rodar `bandit -r arc_devkit -ll` e `pip-audit` como parte desta migração (não feito).
- Varrer `docs/cli-guide.md`, `docs/modules/*.md`, `docs/cookbook.md`, e `website/` (site Next.js separado) pelas mesmas referências desatualizadas corrigidas no core.
- Corrigir os 23 erros pré-existentes de `mypy` (não relacionados a esta migração).

## Status geral

**Pronto para uso em mainnet no modo read-only e para desenvolvimento de integrações.** Operações de escrita (envio de pagamento, bridge CCTP, deploy de contrato) têm as proteções de segurança implementadas e testadas via mocks, mas **nenhuma foi exercida contra fundos reais nesta sessão** — a recomendação em `docs/mainnet/SECURITY.md` (testar em testnet antes de mainnet) se aplica também ao próprio código desta migração.

## Checklist final

```text
[x] Arc Mainnet RPC funcionando — validado ao vivo (chain ID 5042, bloco real, latência ~190ms)
[x] Chain ID validado — RPC confirma 5042 (mainnet) / 5042002 (testnet), config.py nunca cai em fallback errado
[x] SDK default = Mainnet — ARC_NETWORK default é "mainnet" em networks.py
[x] Testnet ainda suportada — Arc.testnet()/ARC_NETWORK=testnet totalmente funcionais, validado ao vivo
[x] Transaction Debugger funcionando — validado ao vivo contra tx real de mainnet (use_ai=False)
    NOT VALIDATED: caminho use_ai=True (chamada real ao Claude) não testado nesta sessão
[x] USDC funcionando — native + ERC-20, validado ao vivo (saldo, endereço de contrato confirmado deployado)
[x] Gas/fees funcionando — quote_fee() corrigido para resolver endereço USDC pela rede ativa; não testado ao vivo com valores reais de transferência (só leitura de gas price)
[x] Contracts funcionando — validado ao vivo (Multicall3.getBlockNumber()/getChainId() via arc.contract())
[x] CLI funcionando — arc status/doctor/send, arcdevkit status/doctor/network validados (status/doctor ao vivo; send via mocks)
[x] arc doctor funcionando — validado ao vivo contra mainnet e testnet reais (READY nas duas)
[x] Exemplos funcionando — 01-07 validados ao vivo contra mainnet real; 08-10 escritos e gated por CONFIRM=yes, NÃO executados (exigiriam fundos reais)
[x] Testes passando — 525 passed, 8 skipped (integration), cobertura 84.72%
[x] README atualizado
[x] Docs atualizadas — README, CLAUDE.md, docs/getting-started.md, docs/index.md, docs/mainnet/ completos
    NOT VALIDATED: docs/cli-guide.md, docs/modules/*.md, docs/cookbook.md, website/ não varridos (ver Known Limitations #6)
[x] Nenhuma secret exposta — nenhuma chave privada, token ou credencial foi commitada; .env.example continua sem valores reais
[x] Nenhuma configuração antiga de testnet usada por engano — grep final não encontrou 5042002 como default de mainnet, nem arc-testnet.drpc.org como default ativo em código-fonte (permanece apenas em contexto histórico/comentários explicativos)
```

Itens marcados `[x]` acima com "NOT VALIDATED" embutido no texto significam: a funcionalidade principal foi implementada e parcialmente validada, mas uma parte específica dela não foi exercida nesta sessão — não deve ser lida como 100% coberta sem essa ressalva.
