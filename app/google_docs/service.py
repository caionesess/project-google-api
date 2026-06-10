import logging
import os
import json
import asyncio
from google.oauth2 import service_account
from googleapiclient.discovery import build
from app.core.config import settings
from app.google_docs.transform import GoogleDocsTransformer

logger = logging.getLogger("uvicorn.error")

metadata_lock = asyncio.Lock()

class GoogleDocsService:
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/documents.readonly']
        self.credentials = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_APPLICATION_CREDENTIALS, 
            scopes=self.scopes
        )
        self.client = build('docs', 'v1', credentials=self.credentials)
        self.transformer = GoogleDocsTransformer()

    def _extract_objectives(self, document_response: dict) -> list[str]:
        """
        Varre a estrutura do Google Doc procurando por tabelas que contenham
        a palavra 'objective' ou 'objetivo' e extrai os itens em formato bullet list
        """
        objectives = []
        body_content = document_response.get("body", {}).get("content", [])

        for element in body_content:
            if "table" in element:
                table = element["table"]
                table_text_lower = str(table).lower()
                
                if "objective" in table_text_lower or "objetivo" in table_text_lower:
                    for row in table.get("tableRows", []):
                        for cell in row.get("tableCells", []):
                            for cell_element in cell.get("content", []):
                                if "paragraph" in cell_element:
                                    paragraph = cell_element["paragraph"]
                                    if "bullet" in paragraph:
                                        text_pieces = [
                                            el.get("textRun", {}).get("content", "")
                                            for el in paragraph.get("elements", [])
                                        ]
                                        full_text = "".join(text_pieces).strip()
                                        if full_text:
                                            objectives.append(full_text)
        return objectives

    async def _update_metadata_json(self, doc_id: str, doc_name: str, objectives: list[str]):
        """
        Atualiza incrementalmente o arquivo metadados.json na raiz do projeto
        """
        json_path = os.path.abspath("metadados.json")
        
        async with metadata_lock:
            data = []
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
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
                "objetivos": objectives
            })

            try:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                logger.info(f"Metadados do documento {doc_id} salvos com sucesso.")
            except Exception as e:
                logger.error(f"Erro ao gravar no arquivo metadados.json: {e}")

    async def get_document_as_html(self, document_id: str) -> str:
        try:
            logger.info(f"Buscando documento: {document_id}")
            response = self.client.documents().get(documentId=document_id).execute()
            if not response:
                raise ValueError("Documento não encontrado")
            
            doc_name = response.get("title", f"documento-{document_id}")
            objectives = self._extract_objectives(response)
            
            await self._update_metadata_json(document_id, doc_name, objectives)

            return self.transformer.convert_to_html(response)
        except Exception as e:
            logger.error(f"Erro ao buscar documento: {str(e)}")
            raise e

    async def get_document_as_pdf(self, document_id: str, output_path: str) -> None:
        """
        Gera o PDF renderizando o HTML através de um navegador Chromium headless (Playwright).
        Garante fidelidade total a fontes web (Google Fonts), margens e regras de tabelas.
        """
        import os
        from playwright.async_api import async_playwright

        html_content = await self.get_document_as_html(document_id)
        absolute_static_path = os.path.abspath("static").replace("\\", "/")
        html_content = html_content.replace("../../static/", f"file:///{absolute_static_path}/")

        target_dir = os.path.dirname(output_path)
        temp_html_path = os.path.join(target_dir, f"temp_{document_id}.html")
        
        with open(temp_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        try:
            async with async_playwright() as p:
                # Inicializa o navegador Chromium
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Abre o arquivo HTML local
                await page.goto(f"file:///{os.path.abspath(temp_html_path)}")
                
                # Aguarda o carregamento completo da rede (garante download de fontes do Google)
                await page.wait_for_load_state("networkidle")
                
                # Gera o PDF preservando o layout e as cores de fundo do CSS
                await page.pdf(
                    path=output_path,
                    format="A4",
                    print_background=True,
                    margin={
                        "top": "2cm",
                        "bottom": "2cm",
                        "left": "2cm",
                        "right": "2cm"
                    }
                )
                await browser.close()
        finally:
            # Remove o arquivo temporário criado para a renderização
            if os.path.exists(temp_html_path):
                os.remove(temp_html_path)