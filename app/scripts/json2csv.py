import csv
import json
from pathlib import Path


def _find_project_root() -> Path:
    current = Path(__file__).resolve()
    if current.parent.name == "app":
        return current.parents[1]
    return current.parents[2]


ROOT_DIR = _find_project_root()
INPUT_DIR = ROOT_DIR / "input"
OUTPUT_DIR = ROOT_DIR / "output"
METADATA_JSON_PATH = ROOT_DIR / "metadados.json"


def determinar_componente(nome_documento):
    """Determina o componente com base no nome do documento."""
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

    headers = ["nome do documento", "id do documento", "componente", "objetivos"]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / nome_arquivo_saida

    with output_path.open(mode="w", encoding="utf-8-sig", newline="") as arquivo_csv:
        escritor = csv.writer(arquivo_csv, delimiter=",", quoting=csv.QUOTE_ALL)
        escritor.writerow(headers)

        for item in dados:
            nome = item.get("nome", "").strip()
            id_doc = item.get("id", "").strip()
            componente = determinar_componente(nome)

            lista_objetivos = item.get("objetivos", [])

            if lista_objetivos:
                objetivos_formatados = ", ".join([f'"{obj}"' for obj in lista_objetivos])
                objetivos = f"[{objetivos_formatados}]"
            else:
                objetivos = "[]"

            escritor.writerow([nome, id_doc, componente, objetivos])

    print(f"Arquivo CSV gerado com sucesso: '{output_path}'")


def main() -> None:
    with METADATA_JSON_PATH.open("r", encoding="utf-8") as f:
        dados_do_arquivo = json.load(f)
        converter_json_para_csv(dados_do_arquivo)


if __name__ == "__main__":
    main()