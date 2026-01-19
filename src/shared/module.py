from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.cofy.app import Cofy
    from fastapi import APIRouter

from abc import ABC, abstractmethod


class Module(ABC):
    cofy: Cofy
    settings: dict

    def __init__(self, settings: dict):
        self.settings = settings

    @abstractmethod
    def get_router(self) -> APIRouter:
        pass
