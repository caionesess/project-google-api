import logging
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from app.core.config import settings
from app.google_docs.transform import GoogleDocsTransformer

logger = logging.getLogger("uvicorn.error")


def _find_project_root() -> Path:
    current = Path(__file__).resolve()
    if current.parent.name == "app":
        return current.parents[1]
    return current.parents[2]


ROOT_DIR = _find_project_root()
METADATA_JSON_PATH = ROOT_DIR / "metadados.json"
STATIC_DIR = ROOT_DIR / "static"


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

    async def _render_document_html(self, document_id: str) -> str:
        try:
            logger.info(f"Buscando documento: {document_id}")
            response = self.client.documents().get(documentId=document_id).execute()
            if not response:
                raise ValueError("Documento não encontrado")

            return self.transformer.convert_to_html(response)
        except Exception as e:
            logger.error(f"Erro ao buscar documento: {str(e)}")
            raise e

    async def get_document_as_html(self, document_id: str) -> str:
        return await self._render_document_html(document_id)