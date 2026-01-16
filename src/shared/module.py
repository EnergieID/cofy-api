from src.cofy.app import Cofy
from fastapi import APIRouter
from abc import ABC, abstractmethod

class Module(ABC):
    cofy: Cofy
    settings: dict

    def __init__(self, settings: dict):
        self.settings = settings

    def update_settings(self, new_settings: dict):
        self.settings.update(new_settings)
    
    @abstractmethod
    def get_router(self) -> APIRouter:
        pass
