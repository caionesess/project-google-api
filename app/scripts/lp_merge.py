import re
import sqlite3
from pathlib import Path
import pandas as pd
import numpy as np


def _find_project_root() -> Path:
    current = Path(__file__).resolve()
    if current.parent.name == "app":
        return current.parents[1]
    return current.parents[2]


ROOT_DIR = _find_project_root()


# Dicionários de mapeamento para materiais e projetos STM
de_para_materiais = {
    "Geography Booklet - 6º ano": "Geography | G6",
    "STEAM Booklet - 9º ano": "STEAM | G9",
    "Science Booklet - 2º Ano 2026": "Science | G2",
    "Expeditions 2": "Expeditions 2",
    "STEAM Booklet - 8º ano": "STEAM | G8",
    "Geography Booklet - 7° ano": "Geography | G7",
    "First Steps - K2 ( 5 aulas)": "K2 | 5 aulas",
    "Geography Booklet - 8° ano": "Geography | G8",
    "Discoveries 3 - K5 - 2026": "Discoveries 3 | 3 aulas",
    "Discoveries 3 - K5": "Discoveries 3 | 5 aulas",
    "First Steps - K2 (3 aulas)": "K2 | 3 aulas",
    "Expeditions 1": "Expeditions 1",
    "Science Booklet - 1° Ano": "Science | G1",
    "Expeditions Foundations": "Expeditions Foundation",
    "Expeditions 4": "Expeditions 4",
    "Expeditions 3": "Expeditions 3",
    "STEAM Booklet - 6º ano": "STEAM | G6",
    "Science Booklet K4 - 2026": "Science | K4 2026",
    "STEAM Booklet - 7º ano": "STEAM | G7",
    "Explorations 4 - G5": "Explorations 4 | 5 aulas",
    "Explorations 4 (3 aulas)": "Explorations 4 | 3 aulas",
    "Explorations 3 - G4": "Explorations 3 | 5 aulas",
    "Explorations 2 - G3": "Explorations 2 | 5 aulas",
    "Explorations 2 (3 aulas)": "Explorations 2 | 3 aulas",
    "Explorations 1 - G2": "Explorations 1 | 5 aulas",
    "Explorations 1 (3 aulas)": "Explorations 1 | 3 aulas",
    "First Steps - Fichas K3": "First Steps | K3",
    "Science Booklet K5 - 2026": "Science | K5 2026",
    "Geography Booklet - 9° ano": "Geography | G9",
    "STEAM Booklet - 1º ano": "STEAM | G1",
    "STEAM Booklet - 2º ano": "STEAM | G2",
    "Adventures 3 - G5": "Adventures 3 | 5 aulas",
    "First Steps - Fichas K4": "First Steps | K4",
    "STEAM Booklet - 3º ano": "STEAM | G3",
    "STEAM Booklet - 4º ano": "STEAM | G4",
    "STEAM Booklet - 5º ano": "STEAM | G5",
    "Adventures 1 - G3": "Adventures 1 | 5 aulas",
    "Adventures 2 - G4": "Adventures 2 | 5 aulas",
    "Explorations Starter (3 aulas)": "Explorations Starter | 3 aulas",
    "First Steps - Fichas K5": "First Steps | K5",
    "Discoveries 2 - K4": "Discoveries 2 | 5 aulas",
    "Explorations Starter - G1": "Explorations Starter | 5 aulas",
    "Discoveries 1 - K3": "Discoveries 1 | 5 aulas",
    "21st CC 1 - 2nd ed.": "21CC Book 1 |  2nd edition",
    "Discoveries 1 - K3 - 2026": "Discoveries 1 | 3 aulas",
    "21st CC 2 - 1st ed.": "21CC Book 2 | 1st edition",
    "Science Booklet K3 - 2026": "Science | K3 2026",
    "21st CC 2 - 2nd ed.": "21CC Book 2 |  2nd edition",
    "21st CC 3 - 2nd ed.": "21CC Book 3 |  2nd edition",
    "21st CC 4 - 2nd ed.": "21CC Book 4 |  2nd edition",
    "Explorations 3 (3 aulas)": "Explorations 3 | 3 aulas"
}

de_para_stm = {
    "G1 STM + Projeto 1": "G1 STM+ Project 1 | Lesson Plans",
    "G1 STM + Projeto 2": "G1 STM+ Project 2 | Lesson Plans",
    "G1 STM + Projeto 3": "G1 STM+ Project 3 | Lesson Plans",
    "G1 STM + Projeto 4": "G1 STM+ Project 4 | Lesson Plans",
    "G1 STM + Projeto 5": "G1 STM+ Project 5 | Lesson Plans",
    "G1 STM + Projeto 6": "G1 STM+ Project 6 | Lesson Plans",
    "G2 STM + Projeto 1": "G2 STM+ Project 1 | Lesson Plans",
    "G2 STM + Projeto 2": "G2 STM+ Project 2 | Lesson Plans",
    "G2 STM + Projeto 3": "G2 STM+ Project 3 | Lesson Plans",
    "G2 STM + Projeto 4 ": "G2 STM+ Project 4 | Lesson Plans",
    "G2 STM + Projeto 5": "G2 STM+ Project 5 | Lesson Plans",
    "G2 STM +Projeto 6": "G2 STM+ Project 6 | Lesson Plans",
    "G3 STM + Projeto 1": "G3 STM+ Project 1 | Lesson Plans",
    "G3 STM + Projeto 2": "G3 STM+ Project 2 | Lesson Plans",
    "G3 STM + Projeto 3": "G3 STM+ Project 3 | Lesson Plans",
    "G3 STM + Projeto 4": "G3 STM+ Project 4 | Lesson Plans",
    "G3 STM + Projeto 5": "G3 STM+ Project 5 | Lesson Plans",
    "G3 STM + Projeto 6": "G3 STM+ Project 6 | Lesson Plans",
    "G4 STM + Projeto 1": "G4 STM+ Project 1 | Lesson Plans",
    "G4 STM + Projeto 2": "G4 STM+ Project 2 | Lesson Plans",
    "G4 STM + Projeto 3": "G4 STM+ Project 3 | Lesson Plans",
    "G4 STM + Projeto 4": "G4 STM+ Project 4 | Lesson Plans",
    "G4 STM + Projeto 5": "G4 STM+ Project 5 | Lesson Plans",
    "G4 STM + Projeto 6": "G4 STM+ Project 6 | Lesson Plans",
    "G5 STM + Projeto 1": "G5 STM+ Project 1 | Lesson Plans",
    "G5 STM + Projeto 2 ": "G5 STM+ Project 2 | Lesson Plans",
    "G5 STM + Projeto 3": "G5 STM+ Project 3 | Lesson Plans",
    "G5 STM + Projeto 4": "G5 STM+ Project 4 | Lesson Plans",
    "G5 STM + Projeto 5 ": "G5 STM+ Project 5 | Lesson Plans",
    "G5 STM + Projeto 6": "G5 STM+ Project 6 | Lesson Plans",
    "G6 STM + Projeto 1": "G6 STM+ Project 1 | Lesson Plans",
    "G6 STM + Projeto 2": "G6 STM+ Project 2 | Lesson Plans",
    "G6 STM + Projeto 3": "G6 STM+ Project 3 | Lesson Plans",
    "G6 STM + Projeto 4": "G6 STM+ Project 4 | Lesson Plans",
    "G6 STM + Projeto 5": "G6 STM+ Project 5 | Lesson Plans",
    "G6 STM + Projeto 6": "G6 STM+ Project 6 | Lesson Plans",
    "G7 STM + Projeto 1": "G7 STM+Project 1 | Lesson Plans",
    "G7 STM + Projeto 2": "G7 STM+ Project 2 | Lesson Plans",
    "G7 STM + Projeto 3": "G7 STM+ Project 3 | Lesson Plans",
    "G7 STM + Projeto 4": "G7 STM+ Project 4 | Lesson Plans",
    "G7 STM + Projeto 5": "G7 STM+ Project 5 | Lesson Plans",
    "G7 STM + Projeto 6": "G7 STM+ Project 6 | Lesson Plans",
    "G8 STM + Projeto 1": "G8 STM+ Project 1 | Lesson Plans",
    "G8 STM + Projeto 2": "G8 STM+ Project 2 | Lesson Plans",
    "G8 STM + Projeto 3": "G8 STM+ Project 3 | Lesson Plans",
    "G8 STM + Projeto 4": "G8 STM+ Project 4 | Lesson Plans",
    "G8 STM + Projeto 5": "G8 STM+ Project 5 | Lesson Plans",
    "G8 STM + Projeto 6": "G8 STM+ Project 6 | Lesson Plans",
    "G9 STM + Projeto 1": "G9 STM+ Project 1 | Lesson Plans",
    "G9 STM + Projeto 2": "G9 STM+ Project 2 | Lesson Plans",
    "G9 STM + Projeto 3": "G9 STM+ Project 3 | Lesson Plans",
    "G9 STM + Projeto 4 ": "G9 STM+ Project 4 | Lesson Plans",
    "G9 STM + Projeto 5": "G9 STM+ Project 5 | Lesson Plans",
    "G9 STM + Projeto 6": "G9 STM+ Project 6 | Lesson Plans"
}


def extract_lp_lesson_num(val) -> float:
    """Extrai o número inteiro da coluna 'name' da lp_table (ex: 'LP 003' -> 3)."""
    if pd.isna(val):
        return np.nan
    match = re.search(r'\d+', str(val))
    return int(match.group()) if match else np.nan


def extract_gdocs_lesson_num(val) -> float:
    """
    Extrai o número correto da lição na gdocs_table:
    1. Prioriza encontrar 'L' seguido de números (ex: 'FST3 K2 L108' -> 108).
    2. Caso não encontre 'L', busca 'FST' seguido de números (ex: 'FST01 K5 | All About Me' -> 1).
    3. Fallback para os primeiros dígitos da string.
    """
    if pd.isna(val):
        return np.nan
    text = str(val)

    l_match = re.search(r'\bL0*(\d+)', text, re.IGNORECASE)
    if l_match:
        return int(l_match.group(1))

    fst_match = re.search(r'FST\s*(\d+)', text, re.IGNORECASE)
    if fst_match:
        return int(fst_match.group(1))

    match = re.search(r'\d+', text)
    return int(match.group()) if match else np.nan


def processar_lp_e_gdocs(lp_df: pd.DataFrame, gdocs_df: pd.DataFrame, de_para_mat: dict, de_para_stm_dict: dict) -> pd.DataFrame:
    lp = lp_df.copy()
    gdocs = gdocs_df.copy()

    lp['_mapped_stm_nome'] = lp['name'].map(de_para_stm_dict)
    
    gdocs_stm_dedup = gdocs.dropna(subset=['nome']).drop_duplicates(subset=['nome'], keep='first')
    
    merged_stm = pd.merge(
        lp,
        gdocs_stm_dedup[['nome', 'conteudo_html', 'lesson_objectives']],
        left_on='_mapped_stm_nome',
        right_on='nome',
        how='left'
    )

    lp['_mapped_material'] = lp['material_name'].map(de_para_mat)
    lp['_lesson_num'] = lp['name'].apply(extract_lp_lesson_num)
    gdocs['_lesson_num'] = gdocs['nome'].apply(extract_gdocs_lesson_num)

    gdocs_mat_dedup = gdocs.dropna(subset=['material', '_lesson_num']).drop_duplicates(subset=['material', '_lesson_num'], keep='first')

    merged_mat = pd.merge(
        lp,
        gdocs_mat_dedup[['material', '_lesson_num', 'conteudo_html', 'lesson_objectives']],
        left_on=['_mapped_material', '_lesson_num'],
        right_on=['material', '_lesson_num'],
        how='left'
    )

    html_final = merged_stm['conteudo_html'].combine_first(merged_mat['conteudo_html'])

    lp['content'] = html_final.combine_first(lp['content'])

    cols_temp = ['_mapped_stm_nome', '_mapped_material', '_lesson_num']
    resultado = lp.drop(columns=[c for c in cols_temp if c in lp.columns])

    return resultado


def exportar_para_sqlite(df: pd.DataFrame, db_filename: str = None, table_name: str = "lp_table"):
    if db_filename is None:
        db_filename = str(ROOT_DIR / "data" / "lp_table.db")

    conn = sqlite3.connect(db_filename)
    
    dtype_mapping = {
        'id': 'INTEGER',
        'name': 'TEXT',
        'id_teachers_guide': 'INTEGER',
        'display_index': 'INTEGER',
        'description': 'TEXT',
        'unit': 'INTEGER',
        'file': 'TEXT',
        'content': 'TEXT',
        'lesson_goals': 'TEXT',
        'created_at': 'TEXT',
        'updated_at': 'TEXT',
        'created_by': 'INTEGER',
        'updated_by': 'INTEGER',
        'deleted': 'BOOLEAN',
        'name_teachers_guide': 'TEXT',
        'material_name': 'TEXT'
    }

    df.to_sql(
        name=table_name,
        con=conn,
        if_exists='replace',
        index=False,
        dtype={k: v for k, v in dtype_mapping.items() if k in df.columns}
    )
    
    conn.close()
    print(f"Banco de dados '{db_filename}' criado com sucesso com a tabela '{table_name}'.")


def exportar_db_para_csv(db_filename: str = None, csv_filename: str = None) -> pd.DataFrame:
    if db_filename is None:
        db_filename = str(ROOT_DIR / "data" / "gdocs2html.db")
    if csv_filename is None:
        csv_filename = str(ROOT_DIR / "data" / "gdocs_table.csv")

    conn = sqlite3.connect(db_filename)

    tabelas = pd.read_sql_query(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;",
        conn
    )

    if tabelas.empty:
        conn.close()
        raise ValueError(f"Nenhuma tabela foi encontrada no banco '{db_filename}'.")

    table_name = tabelas.iloc[0]['name']
    df = pd.read_sql_query(f'SELECT * FROM "{table_name}";', conn)
    df.to_csv(csv_filename, index=False)
    conn.close()

    print(f"Arquivo '{db_filename}' convertido para '{csv_filename}' usando a tabela '{table_name}'.")
    return df


def main(lp_csv_path: str | Path | None = None, gdocs_db_path: str | Path | None = None):
    # Carrega a tabela lp_table.csv do Metabase
    lp_path = Path(lp_csv_path) if lp_csv_path else ROOT_DIR / "lp_table.csv"
    if not lp_path.exists():
        raise FileNotFoundError(f"Arquivo de entrada '{lp_path}' não encontrado.")

    lp_table = pd.read_csv(lp_path)

    # Carrega a tabela gdocs_table.csv do banco gdocs2html.db gerado na automação
    gdocs_table = exportar_db_para_csv(db_filename=str(gdocs_db_path) if gdocs_db_path else None,
                                       csv_filename=str(ROOT_DIR / "data" / "gdocs_table.csv"))
    
    lp_table_processada = processar_lp_e_gdocs(
        lp_table,
        gdocs_table,
        de_para_materiais,
        de_para_stm
    )

    out_csv = ROOT_DIR / "data" / "lp_table_processada.csv"
    lp_table_processada.to_csv(out_csv, index=False)

    exportar_para_sqlite(
        df=lp_table_processada,
        db_filename=str(ROOT_DIR / "data" / "lp_table.db"),
        table_name="lp_table"
    )


if __name__ == "__main__":
    main()
