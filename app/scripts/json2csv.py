import csv
import json
import os


pasta_do_script = os.path.dirname(os.path.abspath(__file__))

caminho_json = os.path.abspath(
    os.path.join(pasta_do_script, "..", "..", "metadados.json")
)

def determinar_modulo(nome_documento):
    """Determina o módulo com base no nome do documento."""
    nome_upper = nome_documento.upper()

    if "PT_PJE 2026" in nome_upper:
        return "PJE 2026"
    elif "FST" in nome_upper:
        return "First Steps"
    elif "STM+" in nome_upper:
        return "STEAM Plus"
    elif (
        "EXPEDITIONS" in nome_upper
        or "EXPLORATIONS" in nome_upper
        or "ADVENTURES" in nome_upper
        or "LGG" in nome_upper
    ):
        return "Language"
    elif "SCI" in nome_upper or "SCIENCE" in nome_upper:
        return "Science"
    elif "GEO" in nome_upper:
        return "Geography"
    elif "STM" in nome_upper:
        return "STEAM"
    else:
        return "Outros"


def converter_json_para_csv(dados_json, nome_arquivo_saida="metadados.csv"):
    if isinstance(dados_json, str):
        dados = json.loads(dados_json)
    else:
        dados = dados_json

    headers = ["nome do documento", "id do documento", "módulo", "objetivos"]

    with open(
        nome_arquivo_saida, mode="w", encoding="utf-8-sig", newline=""
    ) as arquivo_csv:
        escritor = csv.writer(
            arquivo_csv, delimiter=";", quoting=csv.QUOTE_MINIMAL
        )

        escritor.writerow(headers)

        for item in dados:
            nome = item.get("nome", "").strip()
            id_doc = item.get("id", "").strip()
            modulo = determinar_modulo(nome)

            lista_objetivos = item.get("objetivos", [])
            objetivos = " ; ".join(lista_objetivos) if lista_objetivos else ""

            escritor.writerow([nome, id_doc, modulo, objetivos])

    print(f"Arquivo CSV gerado com sucesso: '{nome_arquivo_saida}'")


with open(caminho_json, 'r', encoding='utf-8') as f:
    dados_do_arquivo = json.load(f)
    converter_json_para_csv(dados_do_arquivo)