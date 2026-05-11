# gdoc-poc: contexto e continuidade

Documento de handoff: **objetivo da POC**, **o que o código já faz**, **visão de produto** (planos de aula no Drive) e **referência técnica** para evolução com Google Drive e versionamento.

## 1. Objetivo de negócio

Processo interno em que **professores elaboram planos de aula em Google Docs**, organizados em **hierarquia de pastas** no Google Drive (convenção de “path” por pastas, não um path de filesystem).

Esta POC valida **extrair conteúdo** de um documento conhecido pelo **ID**, com autenticação adequada, como base para monitoramento, versionamento e eventual conversão (ex.: Markdown) em etapas futuras.

## 2. O que o projeto já implementa

| Aspecto | Detalhe |
|--------|---------|
| **Stack** | NestJS 11, TypeScript, `@nestjs/config`, `googleapis`. |
| **Auth** | **Service Account** via `GOOGLE_APPLICATION_CREDENTIALS` (JSON). |
| **API usada** | **Google Docs API v1** (`documents.get`), escopo `https://www.googleapis.com/auth/documents.readonly`. |
| **Saída** | Conversão **própria** do JSON do documento (corpo estruturado) para **HTML** (parágrafos, headings, negrito/itálico/sublinhado/riscado, links, tabelas simples, `sectionBreak` vira `<hr>`). **Não** usa `files.export` do Drive. |
| **HTTP** | `GET /google-docs/:documentId` devolve HTML no navegador; `GET /google-docs/:documentId/html` faz download com `Content-Disposition: attachment`. |
| **Erros** | Mensagens orientadas quando o Doc **não foi compartilhado** com o e-mail da Service Account (403). |
| **Config** | `.env` / `.env.example`: `GOOGLE_APPLICATION_CREDENTIALS`, `PORT` (opcional). |

**Arquivos principais:** `src/google-docs/google-docs.service.ts`, `src/google-docs/google-docs.controller.ts`, `src/google-docs/google-docs.module.ts`.

**Pré-requisito operacional:** cada documento acessado deve estar **compartilhado** com a Service Account (ex.: leitor), conforme `README.md`.

## 3. O que ainda não está no escopo do código

- **Google Drive API** (listar pastas, `files.list`, `parents`, montar path, buscar por nome, Shared drives).
- **Monitoramento** (`files.watch`, `changes.list` / `startPageToken`).
- **Revisões** (`revisions.list`, persistir `headRevisionId` / diff de conteúdo).
- **Export Drive** (`files.export` com `text/html`): caminho alternativo ao parser atual da Docs API.
- **Markdown**, persistência em banco, filas, OAuth de usuário (hoje só Service Account).

Isso está alinhado à evolução desejada do processo (pastas, nomes duplicados, “o que mudou”), descrita abaixo.

## 4. Modelo mental: Drive vs Docs (para quem continua)

- **Drive** organiza **arquivos e pastas** por **IDs** e relação `parents` (um arquivo pode ter **várias** pastas pai). “Path” é **derivado** subindo a hierarquia até uma raiz (ou pasta âncora do programa).
- **Docs API** entrega o **conteúdo estruturado** do documento; esta POC **gera HTML** a partir desse modelo. Para listar “todos os planos sob MK3/Turma X”, será necessário **Drive** (ou convenção + IDs gravados no seu sistema).

## 5. Referência técnica: monitoramento e pastas (resumo)

### 5.1 Monitorar alterações

| Abordagem | Ideia | Prós | Contras |
|-----------|--------|------|---------|
| **Push** | `files.watch` registra URL; Google envia **POST** ao mudar. | Quase tempo real. | HTTPS público, validação de canal, **renovação** (canais expiram). |
| **Polling** | Guardar `startPageToken`; periodicamente `changes.list` pergunta o que mudou desde o token. | Simples com **cron** / jobs. | Latência; mudanças são do **Drive** (filtrar depois por pasta/arquivo relevante). |

### 5.2 Pastas e “path”

- Listar filhos de uma pasta: `files.list` com `q` do tipo `'PASTA_ID' in parents`.
- **Path** não vem pronto: montar subindo `parents` até a raiz ou até uma pasta conhecida do produto.

### 5.3 Obter arquivo por nome

- `files.list` com `q`, ex.: nome + `'ID_PASTA' in parents`.
- Pode haver **vários** arquivos com o mesmo nome na mesma pasta; tratar lista e regra de desambiguação.

### 5.4 Versionamento (lado Drive)

- `revisions.list` por arquivo.
- Boas práticas: persistir identificador de revisão “atual” (ex.: `headRevisionId` em `files.get` quando aplicável) e comparar após detecção de mudança para saber se houve **edição de conteúdo** relevante.

### 5.5 Export HTML (alternativa à Docs API)

- Em fluxos baseados só no Drive: `files.export` com MIME `text/html` para Google Docs.
- **HTML para Markdown** costuma ser **aproximado** (tabelas, layouts complexos); avaliar também texto simples ou normalização própria.

### 5.6 Armadilhas comuns

- `changes.list` cobre o **escopo** da credencial (usuário vs shared drive); combinar com filtros por `fileId` / pasta raiz do programa.
- **Shared drives**: parâmetros e permissões diferem de “My Drive” (`supportsAllDrives`, etc.).
- Nem todo “evento” implica mudança de conteúdo pedagógico; definir critério (ex.: só reexportar se revisão mudou).

## 6. Sugestão de linha evolutiva (curta)

1. Ativar **Drive API**, ampliar escopos e módulo de **listagem / resolução de path** (pasta âncora fixa por ambiente).
2. Job ou webhook para **detecção de mudança**; tabela com `fileId`, última revisão processada, path materializado (opcional).
3. Reutilizar ou substituir o HTML atual: manter parser **Docs API** ou migrar para **export** do Drive, conforme qualidade desejada e esforço de conversão para Markdown.

## 7. Documentação oficial (links)

- [Google Drive API, overview](https://developers.google.com/drive/api/guides/about-sdk)
- [Google Docs API](https://developers.google.com/docs/api/how-tos/overview)
- [Manage changes](https://developers.google.com/drive/api/guides/manage-changes) (tokens / `changes.list`)
- [Push notifications](https://developers.google.com/drive/api/guides/push) (`files.watch`)

## 8. Onde achar detalhes de execução local

Instalação, credenciais Google Cloud, endpoints de exemplo e extração do **documentId** da URL do Docs: ver **`README.md`** na raiz do repositório.
