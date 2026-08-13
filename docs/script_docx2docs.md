## Documentação do Script `docx2docs.py`

Este documento descreve o funcionamento do script `docx2docs.py`, uma ferramenta para converter arquivos DOC/DOCX armazenados em Google Drive em Google Docs (formato `application/vnd.google-apps.document`), mantendo a estrutura de pastas e realizando a conversão de forma recursiva.

---

## Finalidade

- **Conversão em lote:** Varre recursivamente uma pasta no Google Drive, encontra arquivos DOC/DOCX e os converte em Google Docs quando ainda não existem versões convertidas com o mesmo nome.
- **Preservação de estrutura:** Mantém os arquivos convertidos na mesma pasta (parents) onde os originais estão.
- **Relatórios de execução:** Registra contagens de pastas processadas, arquivos encontrados, convertidos, já existentes, ignorados e erros.

## Como funciona (visão geral)

- Conecta-se à API do Google Drive usando credenciais de conta de serviço.
- Lista arquivos e subpastas de uma pasta fornecida (recursivamente).
- Filtra arquivos por mimeType para identificar DOC/DOCX.
- Verifica se já existe um Google Doc com o mesmo nome.
- Quando não existe, usa `files().copy()` com `mimeType: 'application/vnd.google-apps.document'` para criar a cópia convertida.
- Atualiza contadores e imprime o resumo ao final.

## Uso

- Opção 1 — editar o valor de `PASTA_RAIZ_ID` no arquivo e executar diretamente:

```bash
python app/scripts/docx2docs.py
```

- Opção 2 — importar e chamar `main()` passando o ID da pasta programaticamente:

```python
from app.scripts.docx2docs import main
main(pasta_raiz_id='ID_DA_PASTA_RAIZ')
```
