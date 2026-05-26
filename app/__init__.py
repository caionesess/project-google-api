"""
App Core Module

Exposes routers and setup configs through a unified lazy-loaded interface.
"""
from typing import TYPE_CHECKING
from importlib import import_module

if TYPE_CHECKING:
    from .main import app

__all__ = [
    "app",
]

_LAZY_IMPORTS = {
    "app": "main",
}

_module_cache = {}

def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_name = _LAZY_IMPORTS[name]
        if module_name not in _module_cache:
            _module_cache[module_name] = import_module(f".{module_name}", package=__package__)
        return getattr(_module_cache[module_name], name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")