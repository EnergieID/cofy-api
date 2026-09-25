from fastapi import FastAPI

from .api.modules import ModulesRouter
from .errors import add_exception_handlers
from .persitance.file.modules import FileModulesPersistence

app = FastAPI(title="Cofy Management API", version="0.1.0", description="Management API for Cofy")
add_exception_handlers(app)

app.include_router(ModulesRouter(FileModulesPersistence()).router)
