import os
import re
import sys
import asyncio
import logging
from pathlib import Path


def _find_project_root() -> Path:
    current = Path(__file__).resolve()
    if current.parent.name == "app":
        return current.parents[1]
    return current.parents[2]


ROOT_DIR = _find_project_root()
OUTPUT_DIR = ROOT_DIR / "output"

sys.path.insert(0, str(ROOT_DIR))

from app.google_docs.service import GoogleDocsService
from app.google_drive.repository import GoogleDriveFilesRepository


# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================
DRIVE_URL = "[https://drive.google.com/drive/folders/ID_DA_SUA_PASTA]" # Substitua pela URL da pasta do Google Drive
OUTPUT_FORMAT = "web"  # Opções: "web" (para HTML) ou "print" (para PDF)
# ==============================================================================

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("export_drive")


def extract_id_from_url(url: str) -> str:
    """Extrai o ID de um documento ou pasta a partir da URL do Google."""
    folder_match = re.search(r"/folders/([a-zA-Z0-9-_]+)", url)
    if folder_match:
        return folder_match.group(1)
    doc_match = re.search(r"/document/d/([a-zA-Z0-9-_]+)", url)
    if doc_match:
        return doc_match.group(1)
    return url


async def process_folder_recursively(
    drive_repo: GoogleDriveFilesRepository,
    docs_service: GoogleDocsService,
    folder_id: str,
    current_local_dir: Path,
    output_format: str
):
    """
    Navega pelo Google Drive e cria as pastas locais em tempo real à medida que entra nelas.
    Baixa os documentos encontrados diretamente na pasta correspondente.
    """
    current_local_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"📁 Entrando e sincronizando diretório local: '{current_local_dir}'")

    try:
        docs_query = f"'{folder_id}' in parents and mimeType = 'application/vnd.google-apps.document' and trashed = false"
        docs_resp = drive_repo.drive.files().list(
            q=docs_query,
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        documents = docs_resp.get("files", [])
    except Exception as e:
        logger.error(f"Falha ao listar documentos da pasta {folder_id}: {str(e)}")
        documents = []

    for doc in documents:
        doc_id = doc["id"]
        clean_doc_name = re.sub(r'[\\/*?:"<>|]', "-", doc["name"]).strip()

        if output_format == "web":
            file_path = current_local_dir / f"{clean_doc_name}.html"
            logger.info(f"📄 [HTML] Baixando documento: '{clean_doc_name}'")
            try:
                html_content = await docs_service.get_document_as_html(doc_id)
                with file_path.open("w", encoding="utf-8") as f:
                    f.write(html_content)
            except Exception as e:
                logger.error(f"Erro ao converter {clean_doc_name} para HTML: {str(e)}")

        elif output_format == "print":
            file_path = current_local_dir / f"{clean_doc_name}.pdf"
            logger.info(f"📑 [PDF] Renderizando documento: '{clean_doc_name}'")
            try:
                await docs_service.get_document_as_pdf(doc_id, str(file_path))
            except Exception as e:
                logger.error(f"Erro ao converter {clean_doc_name} para PDF: {str(e)}")

    try:
        folder_query = f"'{folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        subfolders_resp = drive_repo.drive.files().list(
            q=folder_query,
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        subfolders = subfolders_resp.get("files", [])
    except Exception as e:
        logger.error(f"Falha ao listar subpastas da pasta {folder_id}: {str(e)}")
        subfolders = []

    for subfolder in subfolders:
        clean_subfolder_name = re.sub(r'[\\/*?:"<>|]', "-", subfolder["name"]).strip()
        next_local_dir = current_local_dir / clean_subfolder_name

        await process_folder_recursively(
            drive_repo, docs_service, subfolder["id"], next_local_dir, output_format
        )


async def main():
    logger.info("Iniciando o processo de exportação e conversão...")

    drive_repo = GoogleDriveFilesRepository()
    docs_service = GoogleDocsService()

    root_id = extract_id_from_url(DRIVE_URL)

    try:
        raw_root_name = drive_repo.get_folder_name(root_id)
    except Exception:
        raw_root_name = "documento-avulso"

    root_folder_name = re.sub(r'[\\/*?:"<>|]', "-", raw_root_name).strip()
    label = "PDF" if OUTPUT_FORMAT == "print" else "HTML"
    root_folder_name_output = f"({label}) {root_folder_name}" if root_folder_name else f"output_{OUTPUT_FORMAT}"

    base_output_path = OUTPUT_DIR / root_folder_name_output

    output_type = "html" if OUTPUT_FORMAT == "web" else "pdf"
    logger.info(f"Pasta Raiz Detectada: '{root_folder_name}' | Formato de Saída: {output_type.upper()}")

    await process_folder_recursively(
        drive_repo, docs_service, root_id, base_output_path, OUTPUT_FORMAT
    )
    logger.info("🎉 Todo o pipeline de pastas e arquivos foi processado com sucesso!")


if __name__ == "__main__":
    asyncio.run(main())