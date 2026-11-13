import sys
import re
import argparse
import asyncio
from pathlib import Path
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.config import settings

from app.google_docs.router import router as google_docs_router
from app.google_drive.router import router as google_drive_router
from app.utils.health import router as health_router
from app.google_docs.service import GoogleDocsService
from app.google_drive.repository import GoogleDriveFilesRepository


def _find_project_root() -> Path:
    current = Path(__file__).resolve()
    if current.parent.name == "app":
        return current.parents[1]
    return current.parents[2]


ROOT_DIR = _find_project_root()
OUTPUT_DIR = ROOT_DIR / "output"

app = FastAPI(title="GDocs to HTML Reimplementation", debug=settings.DEBUG)

app.mount("/static", StaticFiles(directory=str(ROOT_DIR / "static")), name="static")
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
    """Orquestra o processamento: verifica se é um documento único ou uma pasta."""
    target_id = extract_id_from_url(target_url)
    docs_service = GoogleDocsService()
    drive_repo = GoogleDriveFilesRepository()

    base_output_dir = OUTPUT_DIR
    base_output_dir.mkdir(parents=True, exist_ok=True)

    if "document" in target_url:
        print(f"➜ Processando arquivo único ({target_id})...")
        try:
            doc_name = f"documento_{target_id}"

            if output_format == "html":
                file_path = base_output_dir / f"{doc_name}.html"
                html_content = await docs_service.get_document_as_html(target_id)
                with file_path.open("w", encoding="utf-8") as f:
                    f.write(html_content)
                print(f"   ✅ Salvo: {file_path}")

            print("\n🎉 Processamento do documento concluído!")
            return
        except Exception as e:
            print(f"   ❌ Erro ao converter documento {target_id}: {e}")
            return

    try:
        raw_root_name = drive_repo.get_folder_name(target_id)
        root_folder_name = re.sub(r'[\\/*?:"<>|]', "-", raw_root_name).strip()
    except Exception:
        root_folder_name = f"export-{target_id}"

    root_path = base_output_dir / root_folder_name
    root_path.mkdir(parents=True, exist_ok=True)
    print(f"Diretório base de saída: {root_path}")

    async def _process_tree(current_id: str, current_dir: Path):
        docs = drive_repo.list_docs_in_folder(current_id)
        for doc in docs:
            doc_id = doc["id"]
            sanitized_name = re.sub(r'[\\/*?:"<>|]', "-", doc["name"]).strip()
            doc_name = f"{sanitized_name}_{doc_id}"

            print(f"➜ Processando: {doc['name']} ({doc_id}) em '{current_dir}'...")

            try:
                if output_format == "html":
                    file_path = current_dir / f"{doc_name}.html"
                    html_content = await docs_service.get_document_as_html(doc_id)
                    with file_path.open("w", encoding="utf-8") as f:
                        f.write(html_content)
                    print(f"   ✅ Salvo: {file_path}")
            except Exception as e:
                print(f"   ❌ Erro ao converter {doc_name}: {e}")

        subfolders = drive_repo.list_subfolders_in_folder(current_id)
        for subfolder in subfolders:
            folder_name = re.sub(r'[\\/*?:"<>|]', "-", subfolder["name"]).strip()
            new_dir = current_dir / folder_name
            new_dir.mkdir(parents=True, exist_ok=True)

            await _process_tree(subfolder["id"], new_dir)

    await _process_tree(target_id, root_path)
    print("\n🎉 Processamento de todas as pastas concluído!")


def run_cli():
    """Parser de argumentos para o modo de linha de comando."""
    parser = argparse.ArgumentParser(description="GDocs to HTML/PDF CLI tool")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--web", help="Exporta o Alvo (Doc/Folder) no formato HTML")

    args = parser.parse_args()
    target_url = args.web
    output_format = "html"

    asyncio.run(handle_cli_execution(target_url, output_format))


if __name__ == "__main__":
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)
    else:
        run_cli()