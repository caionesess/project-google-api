from typing import List, Optional
from pydantic import BaseModel, Field

class DriveFileSummary(BaseModel):
    id: str
    name: str
    mimeType: str
    parents: Optional[List[str]] = None

class UpdateDriveFileMetadataParams(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None

class MoveFileParams(BaseModel):
    targetFolderId: str = Field(..., min_length=1)