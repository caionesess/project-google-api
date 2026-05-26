"""
Google Docs Module
"""
from typing import TYPE_CHECKING
from importlib import import_module

if TYPE_CHECKING:
    from .router import router
    from .service import GoogleDocsService
    from .transform import GoogleDocsTransformer

__all__ = [
    "router",
    "GoogleDocsService",
    "GoogleDocsTransformer",
]

_LAZY_IMPORTS = {
    "router": "router",
    "GoogleDocsService": "service",
    "GoogleDocsTransformer": "transform",
}

_module_cache = {}

def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_name = _LAZY_IMPORTS[name]
        if module_name not in _module_cache:
            _module_cache[module_name] = import_module(f".{module_name}", package=__package__)
        module = _module_cache[module_name]
        attr = getattr(module, name)
        globals()[name] = attr
        return attr
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

def __dir__():
    return __all__