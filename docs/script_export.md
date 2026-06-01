## Documentação do Script `export_drive.py`

O script `export_drive.py` é uma ferramenta de automação contida no ecossistema deste projeto. Sua principal finalidade é **sincronizar, exportar e converter de forma recursiva (em batch)** as estruturas de pastas do Google Drive contendo Google Docs, transformando-as localmente em arquivos HTML ou PDF enquanto preserva a exata hierarquia de diretórios original.

---

## Finalidade e Diferencial

Enquanto o arquivo principal `app/main.py` realiza conversões planas em lote (colocando todos os arquivos de uma pasta raiz dentro de uma única pasta local datada), o `export_drive.py` resolve cenários de alta complexidade:
* **Recursividade Total:** Se a sua pasta do Google Drive possuir subpastas, e estas subpastas possuírem outras subpastas, o script navegará por todas elas.
* **Espelhamento de Estrutura:** Cria dinamicamente no diretório `output` o mesmo desenho de pastas do Drive, organizando os arquivos convertidos nos seus devidos lugares.
* **Sanitização de Nomes:** Remove automaticamente caracteres inválidos para sistemas de arquivos locais (como `\ / : * ? " < > |`) dos nomes de pastas e documentos, evitando quebras na execução.

---

## Configuração Interna do Script

Antes de executar, você precisa abrir o arquivo `app/scripts/export_drive.py` e configurar as variáveis no bloco inicial do código:

```python
# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================
DRIVE_URL = "[https://drive.google.com/drive/folders/ID_DA_SUA_PASTA](https://drive.google.com/drive/folders/ID_DA_SUA_PASTA)"
OUTPUT_FORMAT = "web"  # Opções: "web" (para HTML) ou "print" (para PDF)
# ==============================================================================