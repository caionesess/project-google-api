import json
from typing import Optional, List
from fastapi import APIRouter, Path, Body, UploadFile, File, Form, HTTPException, status, Response, Depends

from app.google_drive import DriveFileSummary, UpdateDriveFileMetadataParams, MoveFileParams

router = APIRouter(prefix="/google-drive/files", tags=["Google Drive"])

def get_drive_service():
    """
    Função de dependência para isolamento do ciclo de vida do serviço.
    Garante o carregamento lazy do módulo de negócios apenas no runtime da requisição.
    """
    from app.google_drive import GoogleDriveFilesService
    return GoogleDriveFilesService()

@router.post("", response_model=DriveFileSummary)
async def upload(
    file: UploadFile = File(...),
    parents: Optional[str] = Form(None),
    service: str = Depends(get_drive_service)
):
    buffer = await file.read()
    if not buffer or len(buffer) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail='Envie um arquivo no campo multipart "file"'
        )

    parsed_parents: Optional[List[str]] = None
    if parents and parents.strip():
        try:
            parsed = json.loads(parents)
            if not isinstance(parsed, list) or not all(isinstance(p, str) for p in parsed):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="parents deve ser um JSON array de strings (IDs de pastas)"
                )
            parsed_parents = parsed
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail='parents deve ser JSON válido, ex: ["pastaId1"]'
            )

    return await service.upload_file(
        buffer=buffer,
        original_name=file.filename,
        mime_type=file.content_type,
        parents=parsed_parents
    )

@router.patch("/{fileId}", response_model=DriveFileSummary)
async def update_metadata(
    fileId: str = Path(..., description="ID do arquivo no Google Drive"),
    body: UpdateDriveFileMetadataParams = Body(...),
    service: str = Depends(get_drive_service)
):
    return await service.update_metadata(fileId, body)

@router.post("/{fileId}/move", response_model=DriveFileSummary)
async def move(
    fileId: str = Path(..., description="ID do arquivo no Google Drive"),
    body: MoveFileParams = Body(...),
    service: str = Depends(get_drive_service)
):
    return await service.move_to_folder(fileId, body.targetFolderId)

@router.delete("/{fileId}", status_code=status.HTTP_204_NO_CONTENT)
async def remove(
    fileId: str = Path(..., description="ID do arquivo no Google Drive"),
    service: str = Depends(get_drive_service)
):
    await service.delete_file(fileId)
    return Response(status_code=status.HTTP_204_NO_CONTENT)