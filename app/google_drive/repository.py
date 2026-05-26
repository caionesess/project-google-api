import io
import json
import logging
from typing import Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from app.core.config import settings
from app.google_drive.models import DriveFileSummary, UpdateDriveFileMetadataParams

DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive']
logger = logging.getLogger("uvicorn.error")

class GoogleDriveFilesRepository:
    def __init__(self):
        self.credentials = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_APPLICATION_CREDENTIALS,
            scopes=DRIVE_SCOPES
        )
        self.drive = build('drive', 'v3', credentials=self.credentials)

    async def upload(self, buffer: bytes, file_name: str, mime_type: str, parents: Optional[list[str]] = None) -> DriveFileSummary:
        logger.info(json.dumps({
            "msg": "drive.upload.start",
            "fileName": file_name,
            "mimeType": mime_type,
            "sizeBytes": len(buffer),
            "parentsCount": len(parents) if parents else 0
        }))

        request_body = {"name": file_name}
        if parents:
            request_body["parents"] = parents

        fh = io.BytesIO(buffer)
        media = MediaIoBaseUpload(fh, mimetype=mime_type, resumable=True)

        response = self.drive.files().create(
            body=request_body,
            media_body=media,
            fields='id, name, mimeType, parents',
            supportsAllDrives=True
        ).execute()

        if not response.get("id") or not response.get("name"):
            raise ValueError("Resposta inválida do Google Drive ao criar arquivo")

        return DriveFileSummary(**response)

    async def update_metadata(self, file_id: str, params: UpdateDriveFileMetadataParams) -> DriveFileSummary:
        logger.info(json.dumps({"msg": "drive.updateMetadata.start", "fileId": file_id}))

        request_body = {}
        if params.name is not None:
            request_body["name"] = params.name
        if params.description is not None:
            request_body["description"] = params.description

        response = self.drive.files().update(
            fileId=file_id,
            body=request_body,
            fields='id, name, mimeType, parents',
            supportsAllDrives=True
        ).execute()

        if not response.get("id") or not response.get("name"):
            raise ValueError("Resposta inválida do Google Drive ao atualizar arquivo")

        return DriveFileSummary(**response)

    async def move_to_folder(self, file_id: str, target_folder_id: str) -> DriveFileSummary:
        logger.info(json.dumps({"msg": "drive.move.start", "fileId": file_id, "targetFolderId": target_folder_id}))

        current = self.drive.files().get(
            fileId=file_id,
            fields='parents',
            supportsAllDrives=True
        ).execute()

        previous_parents = ",".join(current.get("parents", []))

        response = self.drive.files().update(
            fileId=file_id,
            addParents=target_folder_id,
            removeParents=previous_parents if previous_parents else None,
            fields='id, name, mimeType, parents',
            supportsAllDrives=True
        ).execute()

        if not response.get("id") or not response.get("name"):
            raise ValueError("Resposta inválida do Google Drive ao mover arquivo")

        return DriveFileSummary(**response)

    async def delete(self, file_id: str) -> None:
        logger.info(json.dumps({"msg": "drive.delete.start", "fileId": file_id}))
        self.drive.files().delete(
            fileId=file_id,
            supportsAllDrives=True
        ).execute()

    def list_docs_in_folder(self, folder_id: str) -> list:
        """Lista todos os Google Docs contidos em uma pasta do Drive"""
        query = f"'{folder_id}' in parents and mimeType = 'application/vnd.google-apps.document' and trashed = false"
        response = self.drive.files().list(
            q=query,
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        return response.get("files", [])