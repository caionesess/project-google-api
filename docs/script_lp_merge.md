## Documentação do Script `lp_merge.py`

Este documento descreve o funcionamento do script `app/scripts/lp_merge.py`, responsável por cruzar a tabela de Lesson Plans (`lp_table.csv`) com os conteúdos gerados pelos documentos do Google Docs (`gdocs2html`), aplicando mapeamentos de materiais e projetos STM e exportando o resultado em CSV e SQLite.

---

## Finalidade

- **Juntar dados de duas fontes:** combina a tabela de Lesson Plans do Metabase com os conteúdos HTML gerados a partir dos Google Docs.
- **Aplicar mapeamentos:** usa dicionários de conversão para alinhar nomes de materiais e projetos STM.
- **Completar conteúdo:** preenche a coluna `content` da tabela LP com o HTML quando existe correspondência por material e aula ou por projeto STM.
- **Exportar resultados:** gera um CSV processado e um banco SQLite pronto para uso em outras etapas do fluxo.

## Arquivos necessários para rodar o script

A execução do script depende de alguns arquivos e pastas fixas do projeto:

- `app/scripts/lp_merge.py`
  - Script principal.
  - Ele calcula automaticamente a raiz do projeto e usa caminhos relativos a partir dela.

- `lp_table.csv`
  - Arquivo localizado na raiz do projeto.
  - Tabela de entrada contendo os Lesson Plans extraída do Metabase (incluindo as relações com Teachers Guides e Materials).
  - Caminho padrão:
    - `ROOT_DIR / "lp_table.csv"`

- `data/gdocs2html.db`
  - Banco SQLite gerado pela automação que coleta os documentos do Google Docs.
  - O script lê esse banco para obter a tabela de conteúdos HTML e exporta uma cópia em CSV.
  - Caminho padrão:
    - `ROOT_DIR / "data" / "gdocs2html.db"`

- `data/gdocs_table.csv`
  - Arquivo intermediário gerado automaticamente pelo próprio script a partir do banco SQLite.
  - Serve como base para o merge com a tabela `lp_table.csv`.
  - Caminho padrão:
    - `ROOT_DIR / "data" / "gdocs_table.csv"`

- `data/lp_table.db`
  - Banco SQLite de saída contendo a tabela processada.
  - Caminho padrão:
    - `ROOT_DIR / "data" / "lp_table.db"`

## Como funciona

- O script identifica a raiz do projeto a partir de `__file__`.
- Carrega a tabela `lp_table.csv` em um DataFrame do pandas.
- Lê o banco SQLite `data/gdocs2html.db` e converte a primeira tabela disponível para `data/gdocs_table.csv`.
- Aplica dois tipos de mapeamento:
  - `de_para_materiais`: mapeia nomes de materiais para nomes padronizados no projeto.
  - `de_para_stm`: mapeia os projetos STEAM para os nomes esperados no banco de documentos.
- Calcula os números de lição tanto na tabela do LP quanto na tabela de Google Docs por meio de expressões regulares.
- Faz dois merges principais:
  1. por projeto STM (`nome` x `_mapped_stm_nome`)
  2. por material + número da lição (`material` + `_lesson_num`)
- Usa `combine_first()` para priorizar o conteúdo encontrado em um merge sobre o outro.
- Salva o resultado em `data/lp_table_processada.csv` e também exporta para SQLite em `data/lp_table.db`.

## Observações importantes

- O script depende de bibliotecas como `pandas`, `numpy` e `sqlite3`.
- Ele assume que a base de Google Docs já foi gerada anteriormente e está disponível no banco `data/gdocs2html.db`.
- Se o arquivo `lp_table.csv` não existir na raiz do projeto, o script lança um `FileNotFoundError`.
- Se não houver tabela no banco de origem, o script também dispara um erro claro ao tentar converter o banco para CSV.

