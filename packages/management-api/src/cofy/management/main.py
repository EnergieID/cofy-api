import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api.allowed_modules import AllowedModulesRouter
from .api.communities import CommunitiesRouter
from .api.modules import ModulesRouter
from .errors import add_exception_handlers
from .persitance.file.communities import FileCommunitiesPersistence
from .persitance.file.modules import FileModulesPersistence

STATIC_DIR_ENV_VAR = "COFY_MANAGEMENT_STATIC_DIR"

app = FastAPI(title="Cofy Management API", version="0.1.0", description="Management API for Cofy")
add_exception_handlers(app)

app.include_router(CommunitiesRouter(FileCommunitiesPersistence()).router)
app.include_router(ModulesRouter(FileModulesPersistence()).router)
app.include_router(AllowedModulesRouter().router)

# Serving the console's built assets is optional and off by default, so the API stays usable
# on its own (e.g. behind the Vite dev server's proxy). A deployment that wants a single
# origin - so the console's API client needs no base URL and there is no CORS to configure -
# sets this to the console's build output; it is mounted last so it never shadows the routers
# above, and `html=True` serves `index.html` for the app shell while leaving `/management/...`
# to the API (the console itself routes client-side by URL hash, so no other paths ever reach
# the server).
static_dir = os.environ.get(STATIC_DIR_ENV_VAR)
if static_dir:
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="console")
