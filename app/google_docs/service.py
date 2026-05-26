import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from app.core.config import settings
from app.google_docs.transform import GoogleDocsTransformer

logger = logging.getLogger("uvicorn.error")

class GoogleDocsService:
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/documents.readonly']
        self.credentials = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_APPLICATION_CREDENTIALS, 
            scopes=self.scopes
        )
        self.client = build('docs', 'v1', credentials=self.credentials)
        self.transformer = GoogleDocsTransformer()

    async def get_document_as_html(self, document_id: str) -> str:
        try:
            logger.info(f"Buscando documento: {document_id}")
            response = self.client.documents().get(documentId=document_id).execute()
            if not response:
                raise ValueError("Documento não encontrado")
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