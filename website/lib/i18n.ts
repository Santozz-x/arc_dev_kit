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
      'Instale o Arc DevKit e conecte-se ao testnet Arc em minutos.',
      'Install Arc DevKit and connect to the Arc testnet in minutes.'
    ),
    ctaInstall: t('Guia de instalação', 'Installation guide'),
    ctaGithub: t('Ver no GitHub', 'View on GitHub'),
  },
}
