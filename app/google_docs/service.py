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


def get_unidade_from_response(document_response: dict) -> str:
    """Retorna o campo `unidade` a ser persistido (stub)."""
    return ""

class GoogleDocsService:
    def __init__(self):
        self.scopes = [
            'https://www.googleapis.com/auth/documents.readonly',
            'https://www.googleapis.com/auth/drive.readonly'
        ]
        self.credentials = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_APPLICATION_CREDENTIALS, 
            scopes=self.scopes
        )
        self.client = build('docs', 'v1', credentials=self.credentials)
        self.drive_client = build('drive', 'v3', credentials=self.credentials)
        self.transformer = GoogleDocsTransformer()
        self.database = SqliteDatabase()

    def get_material_from_drive(self, document_id: str, local_output_path: str | Path | None = None) -> str:
        """
        Consulta o Google Drive para obter o nome da pasta pai (material).
        """
        try:
            file_metadata = self.drive_client.files().get(
                fileId=document_id,
                fields="parents",
                supportsAllDrives=True
            ).execute()

            parents = file_metadata.get("parents")
            if parents:
                parent_id = parents[0]
                folder_metadata = self.drive_client.files().get(
                    fileId=parent_id,
                    fields="name",
                    supportsAllDrives=True
                ).execute()
                
                material_name = folder_metadata.get("name", "").strip()
                if material_name:
                    return material_name

        except Exception as e:
            logger.warning(f"Não foi possível obter pasta pai via Google Drive API ({e}). Usando fallback local...")

        if local_output_path:
            return Path(local_output_path).resolve().parent.name

        return ""

    def _clean_text(self, text: str) -> str:
        clean = text.replace('"', '').replace('\"', '').replace('\\', '')
        clean = clean.strip("• \t\r\n")
        return clean

    def _get_paragraph_text(self, paragraph: dict) -> str:
        text_pieces = [
            el.get("textRun", {}).get("content", "")
            for el in paragraph.get("elements", [])
        ]
        return "".join(text_pieces).strip()

    def _is_list_item(self, paragraph: dict) -> bool:
        """
        Verifica se o parágrafo é um item de lista (bullet points ou numeração).
        """
        if "bullet" in paragraph:
            return True
        
        text = self._get_paragraph_text(paragraph).strip()
        list_patterns = r'^([•\-*▪➢>]|\d+[\.\)]|[a-zA-Z][\.\)])\s+'
        return bool(re.match(list_patterns, text))

    def _extract_items_by_title(self, document_response: dict, target_titles: list[str]) -> list[str]:
        """
        Busca seções no documento com base nos títulos informados e extrai os itens.
        Exceção: extrai bullet points/numerados OU qualquer texto contido em células de tabela.
        """
        items = []
        seen = set()
        body_content = document_response.get("body", {}).get("content", [])
        
        normalized_targets = [t.strip().upper() for t in target_titles]
        in_target_section = False

        def is_target_header(text: str) -> bool:
            norm_text = text.strip().upper()
            return any(target == norm_text or norm_text.startswith(target) for target in normalized_targets)

        def is_any_header(paragraph: dict) -> bool:
            style_type = paragraph.get("paragraphStyle", {}).get("namedStyleType", "")
            if style_type.startswith("HEADING_"):
                return True
            
            elements = paragraph.get("elements", [])
            full_text = self._get_paragraph_text(paragraph).strip()
            if full_text and len(full_text) < 80:
                is_all_bold = all(
                    elem.get("textRun", {}).get("textStyle", {}).get("bold", False)
                    for elem in elements if elem.get("textRun", {}).get("content", "").strip()
                )
                if is_all_bold or full_text.isupper():
                    return True
            return False

        def add_item(text: str):
            clean = self._clean_text(text)
            if clean and clean not in seen and len(clean) > 2:
                seen.add(clean)
                items.append(clean)

        def process_elements(elements_list: list, inside_table: bool = False):
            nonlocal in_target_section

            for element in elements_list:
                if "paragraph" in element:
                    paragraph = element["paragraph"]
                    text = self._get_paragraph_text(paragraph)
                    if not text:
                        continue

                    if is_target_header(text):
                        in_target_section = True
                        continue

                    if in_target_section:
                        if is_any_header(paragraph) and not is_target_header(text):
                            in_target_section = False
                            return

                        if self._is_list_item(paragraph) or inside_table:
                            add_item(text)

                elif "table" in element:
                    for row in element["table"].get("tableRows", []):
                        for cell in row.get("tableCells", []):
                            process_elements(cell.get("content", []), inside_table=True)

        process_elements(body_content, inside_table=False)
        return items

    def _extract_objectives(self, document_response: dict) -> list[str]:
        target_titles = [
            "PROJECT OBJECTIVE", "PROJECT OBJECTIVES",
            "LESSON OBJECTIVE", "LESSON OBJECTIVES",
            "OBJETIVO DO PROJETO", "OBJETIVOS DO PROJETO",
            "OBJETIVO DA AULA", "OBJETIVOS DA AULA"
        ]
        return self._extract_items_by_title(document_response, target_titles)

    def _extract_bncc_links(self, document_response: dict) -> list[str]:
        target_titles = [
            "BNCC LINK", "BNCC", "COMPETÊNCIAS GERAIS", "COMPETENCIAS GERAIS",
            "COMPETÊNCIAS DA COMPUTAÇÃO", "PREMISSAS DA COMPUTAÇÃO", 
            "DIREITOS DE APRENDIZAGEM"
        ]
        return self._extract_items_by_title(document_response, target_titles)

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
        doc_id: str | None = None,
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
                doc_id=doc_id,
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

            material = self.get_material_from_drive(document_id)
            componente = get_componente_from_response(response)
            unidade = get_unidade_from_response(response)

            self._save_document_in_sqlite(
                doc_id=document_id,
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