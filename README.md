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
uv run python app/main.py --print "[https://docs.google.com/document/d/ID_DO_SEU_DOCUMENTO/edit]"
```

#### B. Gerar HTML Individual

Extrai a estrutura do Google Docs, cria o diretório de destino `output/html-data-hora/` e gera o arquivo `.html` local.

```powershell
uv run python app/main.py --web "[https://docs.google.com/document/d/ID_DO_SEU_DOCUMENTO/edit]"
```

### 2. Batch (Pasta do Google Drive)

Ao passar o link de uma **pasta** do Google Drive, o sistema listará todos os documentos contidos nela e processará em lote.

#### A. Gerar PDFs em Batch

Converte todos os documentos encontrados na pasta do Google Drive em arquivos PDF individuais dentro de `app/pdf-data-hora/`.

```powershell
uv run python app/main.py --print "[https://drive.google.com/drive/folders/ID_DA_SUA_PASTA]"
```

#### B. Gerar HTMLs em Batch

Extrai e gera os arquivos `.html` correspondentes para todos os documentos da pasta informada dentro de `app/html-data-hora/`.

```powershell
uv run python app/main.py --web "[https://drive.google.com/drive/folders/ID_DA_SUA_PASTA]"
```

## Migração: Do `xhtml2pdf` para o `Playwright`

O sistema utilizava a biblioteca `xhtml2pdf` (baseada no ReportLab). Essa abordagem causava graves problemas visuais:
* **Problema:** O layout saía totalmente desfragmentado, pois o `xhtml2pdf` ignora CSS moderno (`display: flex`, `gap`, `flex-wrap`, etc.). Além disso, fontes dinâmicas da web (como a fonte Montserrat via Google Fonts) eram ignoradas, forçando fontes padrão do sistema e estourando os limites de espaçamento.
* **Solução:** Substituição pelo **Playwright (Chromium Headless)**. Agora, o HTML é aberto dentro de uma instância real de um navegador em segundo plano, injetando as fontes de forma idêntica à web e gerando um PDF com paridade visual absoluta de 100%.