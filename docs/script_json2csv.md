## Documentação do Script `json2csv.py`

O script `json2csv.py` é uma ferramenta de automação voltada para o processamento de dados estruturados. Sua principal finalidade é a leitura de um arquivo de origem contendo metadados (`metadados.json`), o enriquecimento dessas informações através de regras lógicas de negócio e a posterior extração em lote para um arquivo tabular padronizado no formato CSV.

---

## Finalidade

* **Classificação Dinâmica por Módulo:** Analisa o nome do documento com base em palavras-chave predefinidas, mapeando-o automaticamente para os componentes (como PJE 2026, STEAM Plus, Science, Geography, etc.).
* **Sanitização e Padronização Textual:** Aplica regras de remoção de espaçamentos residuais nas extremidades das strings coletadas do JSON (.strip()), prevenindo inconsistências nos registros tabulares finais.