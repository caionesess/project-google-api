"""
Google Drive Module

Provides unified interface for Google Drive file management (Upload, Update, Move, Delete).
Uses lazy imports to optimize FastAPI application startup and memory allocation.
"""
from typing import TYPE_CHECKING
from importlib import import_module

if TYPE_CHECKING:
    from .models import DriveFileSummary, UpdateDriveFileMetadataParams, MoveFileParams
    from .repository import GoogleDriveFilesRepository
    from .service import GoogleDriveFilesService
    from .router import router

__all__ = [
    "DriveFileSummary",
    "UpdateDriveFileMetadataParams",
    "MoveFileParams",
    "GoogleDriveFilesRepository",
    "GoogleDriveFilesService",
    "router",
]

_LAZY_IMPORTS = {
    "DriveFileSummary": "models",
    "UpdateDriveFileMetadataParams": "models",
    "MoveFileParams": "models",
    "GoogleDriveFilesRepository": "repository",
    "GoogleDriveFilesService": "service",
    "router": "router",
}

_module_cache = {}

def __getattr__(name: str):
    """
    Mechanism for lazy-importing core elements of the google_drive module.
    Delays the execution of heavy dependencies until real HTTP traffic triggers them.
    """
    if name in _LAZY_IMPORTS:
        module_name = _LAZY_IMPORTS[name]
        if module_name not in _module_cache:
            _module_cache[module_name] = import_module(f".{module_name}", package=__package__)
        return getattr(_module_cache[module_name], name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")