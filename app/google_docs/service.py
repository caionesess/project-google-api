import logging
import os
import json
import asyncio
import re
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from app.core.config import settings
from app.core.database import SqliteDatabase
from app.google_docs.transform import GoogleDocsTransformer
from app.scripts.json2csv import determinar_componente

logger = logging.getLogger("uvicorn.error")

metadata_lock = asyncio.Lock()


def _find_project_root() -> Path:
    current = Path(__file__).resolve()
    if current.parent.name == "app":
        return current.parents[1]
    return current.parents[2]


ROOT_DIR = _find_project_root()
METADATA_JSON_PATH = ROOT_DIR / "metadados.json"
STATIC_DIR = ROOT_DIR / "static"


def get_componente_from_response(document_response: dict) -> str:
    return determinar_componente(document_response.get("title", ""))


def get_material_from_response(document_response: dict) -> str:
    """Retorna o campo `material` a ser persistido (stub)."""
    return ""


def get_unidade_from_response(document_response: dict) -> str:
    """Retorna o campo `unidade` a ser persistido (stub)."""
    return ""

class GoogleDocsService:
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/documents.readonly']
        self.credentials = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_APPLICATION_CREDENTIALS, 
            scopes=self.scopes
        )
        self.client = build('docs', 'v1', credentials=self.credentials)
        self.transformer = GoogleDocsTransformer()
        self.database = SqliteDatabase()

    def _clean_text(self, text: str) -> str:
        clean = text.replace('"', '').replace('\"', '').replace('\\', '')
        clean = clean.strip("• \t\r\n")
        return clean

    def _is_stop_header(self, text: str) -> bool:
        normalized = text.strip().upper()
        stop_keywords = [
            "SDG", "SDG LINK", "PROJECT", "PROJECT OUTCOME", "AREA OF STUDY", 
            "RESOURCES", "RELEVANT LANGUAGE", "BEFORE THE LESSON", 
            "SUGGESTED PROCEDURES", "PROCEDIMENTOS SUGERIDOS", "TEACHING TIPS",
            "ANSWER KEY", "ADDITIONAL PRACTICE", "DESFECHO DO PROJETO", 
            "PRÓXIMOS PASSOS", "DIRETRIZES GERAIS", "POSSIBILIDADES",
            "LESSON 1", "LESSON 2", "LESSON 3", "LESSON 4", "LESSON 5",
            "LIÇÃO 1", "LIÇÃO 2", "LIÇÃO 3", "LIÇÃO 4", "LIÇÃO 5", "PASSO 1"
        ]
        for kw in stop_keywords:
            if normalized == kw or normalized.startswith(kw + " ") or normalized.startswith(kw + "\n"):
                return True
        return False

    def _is_objective_header(self, text: str) -> bool:
        normalized = text.strip().upper()
        headers = [
            "PROJECT OBJECTIVE", "PROJECT OBJECTIVES",
            "LESSON OBJECTIVE", "LESSON OBJECTIVES",
            "OBJETIVO DO PROJETO", "OBJETIVOS DO PROJETO"
        ]
        return any(h == normalized or normalized.startswith(h) for h in headers)

    def _extract_objectives(self, document_response: dict) -> list[str]:
        """
        Varre a estrutura do Google Doc procurando por tabelas que contenham
        a palavra 'objective' ou 'objetivo' e extrai os itens em formato bullet list
        """
        objectives = []
        seen = set()
        body_content = document_response.get("body", {}).get("content", [])
        in_objective_section = False

        def process_element_text(text: str):
            nonlocal in_objective_section
            if not text or not text.strip():
                return

            if self._is_objective_header(text):
                in_objective_section = True
                return

            if in_objective_section:
                if self._is_stop_header(text) or "BNCC" in text.upper():
                    in_objective_section = False
                    return

                clean = self._clean_text(text)
                if clean and clean not in seen and len(clean) > 3:
                    seen.add(clean)
                    objectives.append(clean)

        for element in body_content:
            if "paragraph" in element:
                p_text = self._get_paragraph_text(element["paragraph"])
                process_element_text(p_text)

            elif "table" in element:
                table_texts = self._extract_texts_from_table(element["table"])
                for text in table_texts:
                    process_element_text(text)

        return objectives

    def _get_paragraph_text(self, paragraph: dict) -> str:
        text_pieces = [
            el.get("textRun", {}).get("content", "")
            for el in paragraph.get("elements", [])
        ]
        return "".join(text_pieces).strip()

    def _extract_texts_from_table(self, table: dict) -> list[str]:
        texts = []
        for row in table.get("tableRows", []):
            for cell in row.get("tableCells", []):
                for cell_element in cell.get("content", []):
                    if "paragraph" in cell_element:
                        paragraph = cell_element["paragraph"]
                        paragraph_text = self._get_paragraph_text(paragraph)
                        if paragraph_text:
                            texts.append(paragraph_text)
        return texts

    def _extract_bncc_links(self, document_response: dict) -> list[str]:
        bncc_links = []
        seen = set()
        body_content = document_response.get("body", {}).get("content", [])
        in_bncc_section = False

        headers_to_ignore = [
            "BNCC LINK", "BNCC", "COMPETÊNCIAS GERAIS", "COMPETENCIAS GERAIS",
            "COMPETÊNCIAS DA COMPUTAÇÃO", "PREMISSAS DA COMPUTAÇÃO", 
            "DIREITOS DE APRENDIZAGEM"
        ]

        def process_element_text(text: str):
            nonlocal in_bncc_section
            if not text or not text.strip():
                return

            upper_text = text.strip().upper()
            if "BNCC" in upper_text or "BNCC LINK" in upper_text:
                in_bncc_section = True
                return

            if in_bncc_section:
                if self._is_stop_header(text):
                    in_bncc_section = False
                    return

                clean = self._clean_text(text)
                if clean and clean not in seen:
                    if clean.upper() in headers_to_ignore:
                        return
                    seen.add(clean)
                    bncc_links.append(clean)

        for element in body_content:
            if "paragraph" in element:
                p_text = self._get_paragraph_text(element["paragraph"])
                process_element_text(p_text)

            elif "table" in element:
                table_texts = self._extract_texts_from_table(element["table"])
                for text in table_texts:
                    process_element_text(text)

        return bncc_links

    async def _update_metadata_json(self, doc_id: str, doc_name: str, objectives: list[str], bncc_links: list[str]):
        async with metadata_lock:
            data = []
            if METADATA_JSON_PATH.exists():
                try:
                    with METADATA_JSON_PATH.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                        if not isinstance(data, list):
                            data = []
                except Exception as e:
                    logger.warning(f"Erro ao ler metadados.json existente, reiniciando arquivo: {e}")
                    data = []

            data = [item for item in data if item.get("id") != doc_id]

            data.append({
                "id": doc_id,
                "nome": doc_name,
                "objetivos": objectives,
                "bncc_links": bncc_links
            })

            try:
                with METADATA_JSON_PATH.open("w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                logger.info(f"Metadados do documento {doc_id} salvos com sucesso.")
            except Exception as e:
                logger.error(f"Erro ao gravar no arquivo metadados.json: {e}")

    def _save_document_in_sqlite(
        self,
        material: str | None = None,
        componente: str | None = None,
        unidade: str | None = None,
        nome: str | None = None,
        conteudo_html: str | None = None,
        bncc_link: list[str] | str | None = None,
        lesson_objectives: list[str] | str | None = None,
    ) -> None:
        try:
            bncc_str = json.dumps(bncc_link, ensure_ascii=False) if isinstance(bncc_link, list) else bncc_link
            objectives_str = json.dumps(lesson_objectives, ensure_ascii=False) if isinstance(lesson_objectives, list) else lesson_objectives

            self.database.upsert_document(
                material=material,
                componente=componente,
                unidade=unidade,
                nome=nome,
                conteudo_html=conteudo_html,
                bncc_link=bncc_str,
                lesson_objectives=objectives_str,
            )
            logger.info(f"Documento {nome} atualizado no SQLite com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao salvar documento no SQLite: {e}")

    async def get_document_as_html(self, document_id: str) -> str:
        try:
            logger.info(f"Buscando documento: {document_id}")
            response = self.client.documents().get(documentId=document_id).execute()
            if not response:
                raise ValueError("Documento não encontrado")
            
            doc_name = response.get("title", f"documento-{document_id}")
            objectives = self._extract_objectives(response)
            bncc_links = self._extract_bncc_links(response)
            
            html_content = self.transformer.convert_to_html(response)

            await self._update_metadata_json(document_id, doc_name, objectives, bncc_links)

            material = get_material_from_response(response)
            componente = get_componente_from_response(response)
            unidade = get_unidade_from_response(response)

            self._save_document_in_sqlite(
                material=material,
                componente=componente,
                unidade=unidade,
                nome=doc_name,
                conteudo_html=html_content,
                bncc_link=bncc_links,
                lesson_objectives=objectives,
            )

            return html_content
        except Exception as e:
            logger.error(f"Erro ao buscar documento: {str(e)}")
            raise e

    async def get_document_as_pdf(self, document_id: str, output_path: str) -> None:
        """
        Gera o PDF renderizando o HTML através de um navegador Chromium headless (Playwright).
        Garante fidelidade total a fontes web (Google Fonts), margens e regras de tabelas.
        """
        from playwright.async_api import async_playwright

        html_content = await self.get_document_as_html(document_id)
        absolute_static_path = str(STATIC_DIR.resolve()).replace("\\", "/")
        html_content = html_content.replace("../../static/", f"file:///{absolute_static_path}/")

        output_path_obj = Path(output_path)
        target_dir = output_path_obj.parent
        target_dir.mkdir(parents=True, exist_ok=True)
        temp_html_path = target_dir / f"temp_{document_id}.html"

        with temp_html_path.open("w", encoding="utf-8") as f:
            f.write(html_content)

        try:
            async with async_playwright() as p:
                # Inicializa o navegador Chromium
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(temp_html_path.resolve().as_uri())
                await page.wait_for_load_state("networkidle")
                
                # Gera o PDF preservando o layout e as cores de fundo do CSS
                await page.pdf(
                    path=str(output_path_obj),
                    format="A4",
                    print_background=True,
                    margin={"top": "2cm", "bottom": "2cm", "left": "2cm", "right": "2cm"}
                )
                await browser.close()
        finally:
            # Remove o arquivo temporário criado para a renderização
            if os.path.exists(temp_html_path):
                os.remove(temp_html_path)