## Description

Pipeline automatizado em Python que converte documentos do Google Docs em arquivos HTML e PDF via Google API e Playwright.
## Configuração

#### 1. Credenciais do Google Cloud

Para usar esta aplicação, você precisa de credenciais de Service Account do Google Cloud:

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um novo projeto ou selecione um existente
3. Ative as APIs do Google Cloud:
   - Vá em "APIs & Services" > "Library"
   - Ative **Google Docs API** e **Google Drive API**
4. Crie uma Service Account:
   - Vá em "APIs & Services" > "Credentials"
   - Clique em "Create Credentials" > "Service Account"
   - Crie a conta e baixe o arquivo JSON de credenciais
5. Compartilhe documentos e pastas com o email da Service Account:
   - Para **ler** documentos: permissão de **Visualizador** no Google Docs
   - Para **upload, mover, editar metadados ou excluir** arquivos no Drive: permissão adequada (**Editor** ou **Gerenciador de conteúdo** nas pastas/arquivos envolvidos)

#### 2. Variáveis de Ambiente

Copie o arquivo `.env.example` para `.env` e configure:

```bash
cp .env.example .env
```

Edite o arquivo `.env` e defina o caminho para o arquivo JSON de credenciais:

```
GOOGLE_APPLICATION_CREDENTIALS=./credentials/google-service-account.json
```

Coloque o arquivo JSON de credenciais na pasta `credentials/` do projeto.

## Project setup

O `uv` é um instalador e gerenciador de pacotes extremamente rápido para Python, projetado para substituir o `pip` e o `poetry`. 
#### 1. Instalação do `uv` no Sistema Operacional 
Execute o comando apropriado no terminal do seu sistema para instalar o `uv` globalmente:

* **No Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

- **No Linux / macOS:**
```
curl -LsSf [https://astral.sh/uv/install.sh](https://astral.sh/uv/install.sh) | sh
```

Após a instalação, reinicie o terminal para garantir que o comando `uv` esteja disponível no seu `PATH`.

#### 2. Sincronização e Criação da VM (.venv)

```
uv sync
```

Este comando lê o arquivo `pyproject.toml`, cria automaticamente a pasta `.venv` (ambiente virtual/VM) e instala todas as dependências listadas de forma isolada.

#### 3. Instalação das Dependências do Navegador (Playwright)

```
uv run playwright install chromium
```

O Playwright precisa dos binários nativos do Chromium instalados dentro do contexto do ambiente virtual para realizar a impressão dos PDFs.

Por fim, configure as variáveis de ambiente conforme descrito na seção de Configuração acima.

## Compile and run the project

### 1. Individual (Um único Google Doc)

#### A. Gerar PDF Individual

Abre o documento do Google Docs, cria o diretório de destino `output/pdf-data-hora/` e gera o PDF final via Playwright.

```powershell
uv run python -m app.main --print "[https://docs.google.com/document/d/ID_DO_SEU_DOCUMENTO/edit]"
```

#### B. Gerar HTML Individual

Extrai a estrutura do Google Docs, cria o diretório de destino `output/html-data-hora/` e gera o arquivo `.html` local.

```powershell
uv run python -m app.main --web "https://docs.google.com/document/d/ID_DO_SEU_DOCUMENTO/edit"
```

### 2. Batch (Pasta do Google Drive)

Ao passar o link de uma **pasta** do Google Drive, o sistema listará todos os documentos contidos nela e processará em lote.

#### A. Gerar PDFs em Batch

Converte todos os documentos encontrados na pasta do Google Drive em arquivos PDF individuais dentro de `output/NOME_DA_SUA_PASTA/`.

```powershell
uv run python -m app.main --print "[https://drive.google.com/drive/folders/ID_DA_SUA_PASTA]"
```

#### B. Gerar HTMLs em Batch

Extrai e gera os arquivos `.html` correspondentes para todos os documentos da pasta informada dentro de `output/NOME_DA_SUA_PASTA/`.

```powershell
uv run python -m app.main --web "[https://drive.google.com/drive/folders/ID_DA_SUA_PASTA]"
```

### 3. Executar como Servidor Web (API FastAPI & Swagger)
Além do modo CLI focado em scripts locais, a aplicação pode ser executada como um servidor HTTP contínuo expondo uma API REST completa.

Para inicializar o servidor em modo de desenvolvimento com recarregamento automático (auto-reload), execute:

```powershell
uv run uvicorn app.main:app --reload
```
O que é possível fazer no modo Servidor Web:
* Documentação Interativa (Swagger UI): Acesse `http://127.0.0.1:8000/docs` no navegador para visualizar e testar todos os endpoints da aplicação de forma gráfica.

* Conversão via Requisições HTTP: Disparar chamadas para os módulos de `/google-docs` e `/google-drive` para extrair dados ou gerenciar arquivos dinamicamente.

* Testes em Tempo Real ("Try it out"): Enviar IDs de documentos e pastas diretamente pela interface web do Swagger e inspecionar imediatamente as estruturas JSON de resposta, os payloads e os códigos de status retornados pelo pipeline.


## Mineração de Dados e Persistência de Metadados

Para enriquecer o pipeline de conversão sem comprometer a performance, o projeto realiza um processo de **Data Mining** (Mineração de Texto) diretamente na estrutura do Google Doc antes de sua renderização final. A extração foi isolada no módulo de serviço (`service.py`), desvinculando as regras de negócio analíticas do motor de transformações visuais (`transform.py`). 

O script varre o documento de forma estruturada em busca de seções de objetivos pedagógicos organizadas em tabelas e listas de marcadores (*bullet points*). Ao final do processamento de cada arquivo, o sistema atualiza de forma incremental um catálogo unificado chamado `metadados.json` localizado na raiz do diretório de exportação.


## Migração: Do `Playwright` para o `WeasyPrint`

O sistema utilizava anteriormente uma abordagem baseada em **Playwright (Chromium Headless)**. Embora o Playwright entregasse alta fidelidade visual, ele exigia a execução de uma instância inteira de um navegador web em segundo plano, resultando em alto consumo de memória RAM, inicialização mais lenta e maior complexidade de infraestrutura.

Para otimizar o desempenho, reduzir o footprint da aplicação e manter a fidelidade visual sem depender de um navegador *headless*, o sistema adotou o **WeasyPrint**.

### Comparativo: `Playwright` vs. `WeasyPrint`

| Característica | Playwright (Chromium Headless) | WeasyPrint |
| :--- | :--- | :--- |
| **Arquitetura** | Abre um navegador Chromium completo em segundo plano para "printar" a página. | Motor de renderização direto em Python/C otimizado para *CSS Paged Media*. |
| **Consumo de Memória** | **Alto** (~150MB a 500MB+ por instância de browser). | **Baixo** (~20MB a 50MB por conversão). |
| **Velocidade de Execução** | Mais lento (tempo de boot do browser + navegação + rede). | Muito mais rápido (compilação direta do documento em memória). |
| **Dependências de Sistema** | Binários pesados do Chromium/WebKit. | Bibliotecas nativas leves de renderização gráfica (Cairo, Pango, Fontconfig). |
| **Padrões de CSS** | Suporta CSS Web moderno (`display: flex`, `grid`, Animações, JS). | Focado em normas W3C de impressão (`@page`, quebras de página, margens nativas). |
| **Texto/Seleção no PDF** | Renderização baseada no layout de tela do browser. | Geração vetorial nativa de PDF com excelente precisão tipográfica. |

---

### Requisitos e Configuração do Ambiente

Por utilizar chamadas nativas às bibliotecas C/C++ (*Cairo* e *Pango*), o WeasyPrint requer a instalação de dependências do sistema operacional antes da execução no ambiente Python.

#### 1. Configuração no Windows

No Windows, é necessário instalar o runtime do **GTK3** para fornecer as DLLs nativas de renderização.

1. **Baixar o Instalador:** Baixe o executável do GTK3 na página de *releases* do [GTK for Windows Runtime Environment](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases) (exemplo: `gtk3-runtime-x.x.x-x64.exe`).
2. **Instalação:** Execute o instalador e **certifique-se de marcar a opção `"Set up PATH environment variable"`** para que as DLLs fiquem acessíveis globalmente pelo sistema.
3. **Variáveis e Terminal:** Após finalizar a instalação, reinicie o terminal, o VS Code ou o ambiente onde o projeto está sendo executado.

#### 2. Configuração no Linux (Ubuntu / Debian)

No Linux, as bibliotecas nativas devem ser instaladas via gerenciador de pacotes do sistema (`apt`).

1. **Instalar Dependências Nativas do Sistema Operacional:**
   ```bash
   sudo apt-get update && sudo apt-get install -y \
       build-essential \
       python3-dev \
       python3-cffi \
       libcairo2 \
       libpango-1.0-0 \
       libpangocairo-1.0-0 \
       libgdk-pixbuf2.0-0 \
       libffi-dev \
       shared-mime-info
   ```