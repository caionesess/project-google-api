import json
import logging
import re
from typing import Optional, List
from fastapi import HTTPException, status
from app.google_drive.repository import GoogleDriveFilesRepository
from app.google_drive.models import DriveFileSummary, UpdateDriveFileMetadataParams

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
logger = logging.getLogger("uvicorn.error")

class GoogleDriveFilesService:
    def __init__(self):
        self.repository = GoogleDriveFilesRepository()

    async def upload_file(self, buffer: bytes, original_name: str, mime_type: str, parents: Optional[List[str]] = None) -> DriveFileSummary:
        if not buffer or len(buffer) == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo vazio ou ausente")

        if len(buffer) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Arquivo excede o limite de {MAX_UPLOAD_BYTES} bytes")

        file_name = self._sanitize_file_name(original_name)
        normalized_parents = self._normalize_parents(parents)

        try:
            summary = await self.repository.upload(
                buffer=buffer,
                file_name=file_name,
                mime_type=mime_type or "application/octet-stream",
                parents=normalized_parents
            )
            logger.info(json.dumps({"msg": "drive.upload.ok", "fileId": summary.id, "fileName": summary.name}))
            return summary
        except Exception as error:
            raise self._map_drive_error(error, "Falha ao enviar arquivo para o Google Drive")

    async def update_metadata(self, file_id: str, params: UpdateDriveFileMetadataParams) -> DriveFileSummary:
        self._assert_file_id(file_id)

        if params.name is None and params.description is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe ao menos name ou description para editar")

        if params.name is not None and not params.name.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name não pode ser vazio")

        if params.name is not None:
            params.name = params.name.strip()

        try:
            summary = await self.repository.update_metadata(file_id, params)
            logger.info(json.dumps({"msg": "drive.updateMetadata.ok", "fileId": summary.id}))
            return summary
        except Exception as error:
            raise self._map_drive_error(error, "Falha ao editar metadados no Google Drive")

    async def move_to_folder(self, file_id: str, target_folder_id: str) -> DriveFileSummary:
        self._assert_file_id(file_id)
        if not target_folder_id or not target_folder_id.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="targetFolderId é obrigatório")

        try:
            summary = await self.repository.move_to_folder(file_id, target_folder_id.strip())
            logger.info(json.dumps({"msg": "drive.move.ok", "fileId": summary.id, "parents": summary.parents}))
            return summary
        except Exception as error:
            raise self._map_drive_error(error, "Falha ao mover arquivo no Google Drive")

    async def delete_file(self, file_id: str) -> None:
        self._assert_file_id(file_id)
        try:
            await self.repository.delete(file_id)
            logger.info(json.dumps({"msg": "drive.delete.ok", "fileId": file_id}))
        except Exception as error:
            raise self._map_drive_error(error, "Falha ao remover arquivo no Google Drive")

    def _assert_file_id(self, file_id: str) -> None:
        if not file_id or not file_id.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID do arquivo é obrigatório")

    def _normalize_parents(self, parents: Optional[List[str]]) -> Optional[List[str]]:
        if not parents:
            return None
        cleaned = [p.strip() for p in parents if p and p.strip()]
        return cleaned if len(cleaned) > 0 else None

    def _sanitize_file_name(self, name: str) -> str:
        base = name.strip() if name else "arquivo"
        base = re.sub(r'[/\\]', '-', base)
        return base[:255]

    def _map_drive_error(self, error: Exception, fallback_message: str) -> HTTPException:
        code = getattr(error, "resp", None) and getattr(error.resp, "status", None)
        if not code and hasattr(error, "content"):
            try:
                data = json.loads(error.content)
                code = data.get("error", {}).get("code")
            except Exception:
                pass

        message = str(error)
        logger.error(json.dumps({"msg": "drive.error", "code": code, "message": message}))

        if code == 404:
            return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo não encontrado no Google Drive")
        if code == 403:
            return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissão negada no Google Drive. Verifique se a Service Account tem acesso ao arquivo ou pasta.")
        if "invalid_grant" in message or "invalid" in message:
            return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Credenciais ou parâmetros inválidos para o Google Drive")

        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message or fallback_message)