import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from app.core.config import settings


def _find_project_root() -> Path:
    current = Path(__file__).resolve()
    if current.parent.name == "app":
        return current.parents[1]
    return current.parents[2]


ROOT_DIR = _find_project_root()


class SqliteDatabase:
    def __init__(self, db_path: str | None = None):
        self.db_path = str((ROOT_DIR / (db_path or settings.SQLITE_DB_PATH)).resolve())
        self._ensure_directory_exists()
        self._initialize_database()

    def _ensure_directory_exists(self) -> None:
        directory = Path(self.db_path).parent
        if directory and not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _initialize_database(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    material TEXT,
                    componente TEXT,
                    unidade TEXT,
                    nome TEXT,
                    conteudo_html TEXT,
                    bncc_link TEXT,
                    lesson_objectives TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def upsert_document(
        self,
        material: str | None = None,
        componente: str | None = None,
        unidade: str | None = None,
        nome: str | None = None,
        conteudo_html: str | None = None,
        bncc_link: str | list[str] | None = None,
        lesson_objectives: str | list[str] | None = None,
    ) -> None:
        created_at = datetime.now().isoformat()
        updated_at = created_at

        bncc_str = json.dumps(bncc_link, ensure_ascii=False) if isinstance(bncc_link, list) else bncc_link
        objectives_str = json.dumps(lesson_objectives, ensure_ascii=False) if isinstance(lesson_objectives, list) else lesson_objectives

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO documents (
                    material, componente, unidade, nome,
                    conteudo_html, bncc_link, lesson_objectives,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    material,
                    componente,
                    unidade,
                    nome,
                    conteudo_html,
                    bncc_str,
                    objectives_str,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()

    def get_document(self, doc_id: int) -> dict | None:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, material, componente, unidade, nome,
                       conteudo_html, bncc_link, lesson_objectives,
                       created_at, updated_at
                FROM documents WHERE id = ?
                """,
                (doc_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            def _parse_json_or_text(val):
                if not val:
                    return None
                try:
                    return json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    return val

            return {
                "id": row[0],
                "material": row[1],
                "componente": row[2],
                "unidade": row[3],
                "nome": row[4],
                "conteudo_html": row[5],
                "bncc_link": _parse_json_or_text(row[6]),
                "lesson_objectives": _parse_json_or_text(row[7]),
                "created_at": row[8],
                "updated_at": row[9],
            }