export type Locale = 'pt' | 'en'

export interface Translation {
  pt: string
  en: string
}

const t = (pt: string, en: string): Translation => ({ pt, en })

export function tr(translation: Translation, locale: Locale): string {
  return translation[locale]
}

export const i18n = {
  nav: {
    docs: t('Docs', 'Docs'),
    quickstart: t('Quickstart', 'Quickstart'),
    api: t('API', 'API'),
    cookbook: t('Cookbook', 'Cookbook'),
    demo: t('Demo Mainnet', 'Mainnet Demo'),
    langToggle: t('EN', 'PT'),
  },
  sidebar: {
    start: t('Início', 'Start'),
    modules: t('Módulos', 'Modules'),
    interfaces: t('Interfaces', 'Interfaces'),
    guides: t('Guias', 'Guides'),
    network: t('Arc Mainnet', 'Arc Mainnet'),
  },
  footer: {
    docs: t('Docs', 'Docs'),
    cookbook: t('Cookbook', 'Cookbook'),
    license: t('Licença MIT', 'MIT License'),
  },
  doc: {
    prev: t('Anterior', 'Previous'),
    next: t('Próximo', 'Next'),
  },
  home: {
    heroBadge: t(
      'Arc Mainnet · Chain ID 5042 · Python 3.11+',
      'Arc Mainnet · Chain ID 5042 · Python 3.11+'
    ),
    heroTitle: t('Build on Arc,', 'Build on Arc,'),
    heroAccent: t('faster.', 'faster.'),
    heroSubtitle: t(
      'Arc DevKit é o toolkit Python completo para desenvolvedores na blockchain Arc — a L1 EVM-compatível da Circle com USDC como gas token e finalidade sub-segundo.',
      "Arc DevKit is the complete Python toolkit for developers building on the Arc blockchain — Circle's EVM-compatible L1 with USDC as the gas token and sub-second finality."
    ),
    ctaStart: t('Começar agora', 'Get started'),
    ctaDocs: t('Ver documentação', 'View documentation'),
    terminalInstall: t('# Instalar', '# Install'),
    terminalAskComment: t('# Perguntar ao AI Copilot', '# Ask the AI Copilot'),
    terminalDebugComment: t('# Debugar uma transação', '# Debug a transaction'),
    statModules: t('Módulos', 'Modules'),
    statFinality: t('Finalidade', 'Finality'),
    statGas: t('Gas Token', 'Gas Token'),
    statLicense: t('Licença', 'License'),
    modulesTitle: t('Tudo que você precisa', 'Everything you need'),
    modulesSubtitle: t(
      'Módulos prontos para as operações mais comuns na Arc blockchain.',
      'Ready-made modules for the most common operations on the Arc blockchain.'
    ),
    copilotDesc: t(
      'Assistente IA com Claude Sonnet — contexto Arc embutido, streaming, histórico e cache.',
      'AI assistant with Claude Sonnet — built-in Arc context, streaming, history and cache.'
    ),
    paymentDesc: t(
      'Pagamentos nativos e USDC ERC-20 com estimativa de gas, dry run e batch automático.',
      'Native and USDC ERC-20 payments with gas estimation, dry run and automatic batching.'
    ),
    monitorDesc: t(
      'Monitore carteiras em tempo real com WebSocket, eventos ERC-20 e webhook HTTP.',
      'Monitor wallets in real time with WebSocket, ERC-20 events and HTTP webhooks.'
    ),
    debuggerDesc: t(
      'Decodifica reverts, dados de input e gera diagnóstico em linguagem natural.',
      'Decodes reverts, input data and generates natural language diagnostics.'
    ),
    portfolioDesc: t(
      'Snapshot de saldo, histórico de transações e score de atividade por carteira.',
      'Balance snapshot, transaction history and activity score per wallet.'
    ),
    cliDesc: t(
      'Interface de linha de comando completa e servidor FastAPI com Swagger, SSE e WebSocket.',
      'Full command-line interface and FastAPI server with Swagger, SSE and WebSocket.'
    ),
    codeTitle: t('IA com contexto Arc embutido', 'AI with built-in Arc context'),
    codeSubtitle: t(
      'O DevCopilot já conhece a blockchain Arc — gas em USDC, endpoints RPC, Malachite consensus e o Circle Agent Stack. Sem configuração extra.',
      'DevCopilot already knows the Arc blockchain — USDC gas, RPC endpoints, Malachite consensus, and the Circle Agent Stack. No extra configuration needed.'
    ),
    codeFeatures: [
      t('Histórico de conversa multi-turn', 'Multi-turn conversation history'),
      t('Cache com TTL de 5 minutos', '5-minute TTL cache'),
      t('Streaming token a token', 'Token-by-token streaming'),
      t('Suporte a imagens (PNG, JPEG, WebP)', 'Image support (PNG, JPEG, WebP)'),
      t('Modo offline para CI/CD', 'Offline mode for CI/CD'),
    ],
    codeLinkText: t('Ver documentação completa', 'View full documentation'),
    ctaTitle: t('Pronto para começar?', 'Ready to get started?'),
    ctaSubtitle: t(
      'Instale o Arc DevKit e conecte-se à Arc Mainnet em minutos.',
      'Install Arc DevKit and connect to Arc Mainnet in minutes.'
    ),
    ctaInstall: t('Guia de instalação', 'Installation guide'),
    ctaGithub: t('Ver no GitHub', 'View on GitHub'),
  },
  demo: {
    title: t('Demonstração na Mainnet', 'Mainnet Demo'),
    subtitle: t(
      'O Arc DevKit é um toolkit Python (SDK + CLI). Esta página consulta a Arc Mainnet ao vivo através do backend Python do próprio Arc DevKit — nenhuma chamada de RPC é feita em JavaScript.',
      'Arc DevKit is a Python toolkit (SDK + CLI). This page queries Arc Mainnet live through Arc DevKit’s own Python backend — no RPC calls are made from JavaScript.'
    ),
    liveBadge: t('AO VIVO', 'LIVE'),
    unavailableBadge: t('BACKEND INDISPONÍVEL', 'BACKEND UNAVAILABLE'),
    loadingBadge: t('CARREGANDO', 'LOADING'),
    notConfiguredTitle: t(
      'Backend de demonstração não configurado',
      'Demo backend not configured'
    ),
    notConfiguredBody: t(
      'Esta implantação do site não tem NEXT_PUBLIC_DEMO_API_URL configurada, então esta página não pode consultar a Arc Mainnet ao vivo agora. O código Python abaixo funciona de forma independente — rode-o localmente com o Arc DevKit instalado.',
      'This site deployment has no NEXT_PUBLIC_DEMO_API_URL configured, so this page cannot query Arc Mainnet live right now. The Python code below works independently — run it locally with Arc DevKit installed.'
    ),
    unavailableBody: t(
      'Não foi possível contatar o backend de demonstração agora. Isso não é um erro do Arc DevKit em si — é a disponibilidade deste serviço específico. Nenhum dado falso é mostrado.',
      'Could not reach the demo backend right now. This is not an error in Arc DevKit itself — it reflects this specific service’s availability. No fake data is shown.'
    ),
    statusTitle: t('Status da conexão', 'Connection status'),
    network: t('Rede', 'Network'),
    chainIdExpected: t('Chain ID esperado', 'Expected chain ID'),
    chainIdRpc: t('Chain ID retornado pelo RPC', 'Chain ID returned by RPC'),
    chainIdMatch: t('Chain ID confere', 'Chain ID matches'),
    latency: t('Latência', 'Latency'),
    usdcContract: t('Contrato USDC deployado', 'USDC contract deployed'),
    refresh: t('Atualizar', 'Refresh'),
    blockTitle: t('Bloco mais recente', 'Latest block'),
    blockNumber: t('Número', 'Number'),
    blockHash: t('Hash', 'Hash'),
    blockTimestamp: t('Timestamp', 'Timestamp'),
    blockTxCount: t('Transações', 'Transactions'),
    txTitle: t('Consultar e analisar uma transação', 'Look up and analyze a transaction'),
    txInputPlaceholder: t('Cole um hash de transação (0x...)', 'Paste a transaction hash (0x...)'),
    txLookupButton: t('Consultar', 'Look up'),
    txFindButton: t('Buscar uma transação recente', 'Find a recent transaction'),
    txHash: t('Hash', 'Hash'),
    txStatus: t('Status', 'Status'),
    txBlock: t('Bloco', 'Block'),
    txFrom: t('De', 'From'),
    txTo: t('Para', 'To'),
    txValueNative: t('Valor (USDC nativo, 18 decimais)', 'Value (native USDC, 18 decimals)'),
    txGasCost: t('Custo de gas (USDC nativo, 18 decimais)', 'Gas cost (native USDC, 18 decimals)'),
    txErc20Transfers: t(
      'Transfer(s) ERC-20 de USDC decodificado(s) (6 decimais)',
      'Decoded USDC ERC-20 Transfer log(s) (6 decimals)'
    ),
    txNoErc20: t(
      'Nenhum log de Transfer ERC-20 de USDC nesta transação.',
      'No USDC ERC-20 Transfer log in this transaction.'
    ),
    debugTitle: t(
      'Análise do debugger (use_ai=False, sem IA)',
      'Debugger analysis (use_ai=False, no AI)'
    ),
    debugSummary: t('Resumo', 'Summary'),
    viewExplorer: t('Ver no explorer', 'View on explorer'),
    queriedAt: t('Consultado em', 'Queried at'),
    codeTitle: t('Código Python equivalente', 'Equivalent Python code'),
    installTitle: t('Instalação', 'Installation'),
    recordingTitle: t(
      'Gravação real: instalação até a consulta na mainnet',
      'Real recording: install to a live mainnet query'
    ),
    recordingBody: t(
      'Sessão de terminal genuína — ambiente virtual novo, pip install arc-devkit==0.10.0 do PyPI real, e execução real do script contra a Arc Mainnet. Nenhum trecho foi editado além de limitar tempo ocioso entre comandos.',
      'A genuine terminal session — fresh virtual environment, pip install arc-devkit==0.10.0 from the real PyPI, and a real script run against Arc Mainnet. Nothing was edited besides capping idle time between commands.'
    ),
    recordingFallback: t(
      'Seu navegador não suporta vídeo incorporado.',
      'Your browser does not support embedded video.'
    ),
    recordingDownloadMp4: t('Baixar MP4', 'Download MP4'),
    recordingDownloadCast: t('Baixar .cast (asciinema)', 'Download .cast (asciinema)'),
    historicalTitle: t('Referência histórica gravada', 'Recorded historical reference'),
    historicalBody: t(
      'Os valores abaixo foram registrados em uma execução real passada (ver a página de evidências da demonstração) — não são atualizados ao vivo. Use os controles acima para uma consulta ao vivo.',
      'The values below were recorded from a real past run (see the demo evidence page) — they are not live-updating. Use the controls above for a live query.'
    ),
    historicalLink: t(
      'Ver evidência completa: tutorial, gravação em vídeo/asciinema e transação verificável →',
      'See full evidence: tutorial, video/asciinema recording, and verifiable transaction →'
    ),
    invalidHash: t(
      'Hash de transação inválido (esperado 0x + 64 caracteres hex).',
      'Invalid transaction hash (expected 0x + 64 hex chars).'
    ),
  },
}
