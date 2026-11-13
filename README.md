## Description

Este projeto é uma solução em Python para automatizar a conversão de documentos do Google Docs em arquivos HTML estruturados, utilizando a Google API para leitura do conteúdo e transformação em HTML pronto para uso em aplicações web, documentos estáticos ou exportação local.

Além da extração e transformação de conteúdo, o sistema também oferece uma interface de linha de comando (CLI) e suporte para execução via API REST com FastAPI, tornando o fluxo de conversão útil tanto para automações locais quanto para integrações com outros serviços ou aplicações.

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

## Compile and run the project

### 1. Individual (Um único Google Doc)

#### Gerar HTML Individual

Extrai a estrutura do Google Docs, cria o diretório de destino `output/html-data-hora/` e gera o arquivo `.html` local.

```powershell
uv run python -m app.main --web "https://docs.google.com/document/d/ID_DO_SEU_DOCUMENTO/edit"
```

### 2. Batch (Pasta do Google Drive)

Ao passar o link de uma **pasta** do Google Drive, o sistema listará todos os documentos contidos nela e processará em lote.

#### Gerar HTMLs em Batch

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
