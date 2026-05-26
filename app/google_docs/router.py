from fastapi import APIRouter, Path, HTTPException, status
from fastapi.responses import HTMLResponse, Response
from app.google_docs.service import GoogleDocsService

router = APIRouter(prefix="/google-docs", tags=["Google Docs"])
google_docs_service = GoogleDocsService()

@router.get("/{documentId}/html", response_class=HTMLResponse)
async def download_as_html(
    documentId: str = Path(..., description="ID do documento do Google Docs")
):
    if not documentId:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID do documento é obrigatório")
    
    try:
        html_content = await google_docs_service.get_document_as_html(documentId)
        headers = {
            "Content-Type": "text/html; charset=utf-8",
            "Content-Disposition": f'attachment; filename="documento-{documentId}.html"'
        }
        return Response(content=html_content, headers=headers)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e) or "Erro ao processar documento"
        )

@router.get("/{documentId}", response_class=HTMLResponse)
async def view_as_html(
    documentId: str = Path(..., description="ID do documento do Google Docs")
):
    if not documentId:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID do documento é obrigatório")
    
    try:
        html_content = await google_docs_service.get_document_as_html(documentId)
        return HTMLResponse(content=html_content, media_type="text/html; charset=utf-8")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e) or "Erro ao processar documento"
        )