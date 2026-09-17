from fastapi import FastAPI

from .api.allowed_modules import AllowedModulesRouter
from .api.communities import CommunitiesRouter
from .api.modules import ModulesRouter
from .errors import add_exception_handlers
from .persitance.file.communities import FileCommunitiesPersistence
from .persitance.file.modules import FileModulesPersistence

app = FastAPI(title="Cofy Management API", version="0.1.0", description="Management API for Cofy")
add_exception_handlers(app)

app.include_router(CommunitiesRouter(FileCommunitiesPersistence()).router)
app.include_router(ModulesRouter(FileModulesPersistence()).router)
app.include_router(AllowedModulesRouter().router)
