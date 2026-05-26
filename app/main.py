import os
import sys
import re
import argparse
import asyncio
from datetime import datetime
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.config import settings

from app.google_docs.router import router as google_docs_router
from app.google_drive.router import router as google_drive_router
from app.utils.health import router as health_router

app = FastAPI(title="GDocs to HTML Reimplementation", debug=settings.DEBUG)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(health_router)
app.include_router(google_docs_router)
app.include_router(google_drive_router)

def extract_id_from_url(url: str) -> str:
    """Extrai o ID de um documento ou pasta a partir da URL do Google."""
    doc_match = re.search(r"/document/d/([a-zA-Z0-9-_]+)", url)
    if doc_match:
        return doc_match.group(1)
    folder_match = re.search(r"/folders/([a-zA-Z0-9-_]+)", url)
    if folder_match:
        return folder_match.group(1)
    return url

async def handle_cli_execution(target_url: str, output_format: str):
    """Orquestra a extração e download via CLI salvando em pastas com data/hora."""
    from app.google_docs.service import GoogleDocsService
    from app.google_drive.repository import GoogleDriveFilesRepository

    target_id = extract_id_from_url(target_url)
    docs_service = GoogleDocsService()
    drive_repo = GoogleDriveFilesRepository()

    try:
        files = drive_repo.list_docs_in_folder(target_id)
    except Exception:
        files = []

    if not files:
        files = [{"id": target_id, "name": f"documento-{target_id}"}]

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    
    target_dir = os.path.join("output", f"{output_format}-{timestamp}")
    
    os.makedirs(target_dir, exist_ok=True)
    print(f"Diretório de destino criado: {target_dir}")

    for doc in files:
        doc_id = doc["id"]
        doc_name = doc["name"].replace("/", "-").replace("\\", "-").strip()
        print(f"Processando: {doc_name} ({doc_id})")

        if output_format == "html":
            file_path = os.path.join(target_dir, f"{doc_name}.html")
            html_content = await docs_service.get_document_as_html(doc_id)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"Salvo com sucesso em: {file_path}")
        
        elif output_format == "pdf":
            file_path = os.path.join(target_dir, f"{doc_name}.pdf")
            await docs_service.get_document_as_pdf(doc_id, file_path)
            print(f"Salvo com sucesso em: {file_path}")

def run_cli():
    """Parser de argumentos para o modo de linha de comando."""
    parser = argparse.ArgumentParser(description="GDocs to HTML/PDF CLI tool")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--print", help="Exporta o Alvo (Doc/Folder) no formato PDF")
    group.add_argument("--web", help="Exporta o Alvo (Doc/Folder) no formato HTML")
    
    args = parser.parse_args()
    target_url = args.print if args.print else args.web
    output_format = "pdf" if args.print else "html"
    
    asyncio.run(handle_cli_execution(target_url, output_format))

if __name__ == "__main__":
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)
    else:
        run_cli()