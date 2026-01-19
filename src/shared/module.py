from __future__ import annotations
from abc import ABC, abstractmethod
from fastapi import APIRouter

class Module(ABC):
    cofy: src.cofy.app.Cofy
    settings: dict

    def __init__(self, settings: dict):
        self.settings = settings

    def update_settings(self, new_settings: dict):
        self.settings.update(new_settings)
    
    @abstractmethod
    def get_router(self) -> APIRouter:
        pass
