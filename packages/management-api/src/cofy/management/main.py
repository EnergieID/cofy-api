import os

import httpx
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from .api.allowed_modules import AllowedModulesRouter
from .api.allowed_resources import AllowedResourcesRouter
from .api.communities import CommunitiesRouter
from .api.grants import GrantsRouter
from .api.modules import ModulesRouter
from .api.resources import ResourcesRouter
from .api.secrets import SecretsRouter
from .api.status import StatusRouter
from .auth.config import OidcConfig
from .auth.router import AuthRouter
from .auth.session import install_session
from .auth.user import install_users
from .community_api import CommunityApi
from .errors import add_exception_handlers
from .persitance.file.base import data_dir
from .persitance.file.communities import FileCommunitiesPersistence
from .persitance.file.grants import FileGrantsPersistence
from .persitance.file.modules import FileModulesPersistence
from .persitance.file.resources import FileResourcesPersistence
from .persitance.file.secrets import FileSecretsPersistence
from .persitance.file.users import FileUsersPersistence

STATIC_DIR_ENV_VAR = "COFY_MANAGEMENT_STATIC_DIR"
COMMUNITIES_URL_ENV_VAR = "COFY_MANAGEMENT_COMMUNITIES_URL"

#: Each `OidcConfig` field, and the environment variable it is read from.
OIDC_ENV_VARS = {
    "issuer": "COFY_MANAGEMENT_OIDC_ISSUER",
    "client_id": "COFY_MANAGEMENT_OIDC_CLIENT_ID",
    "client_secret": "COFY_MANAGEMENT_OIDC_CLIENT_SECRET",
    "scopes": "COFY_MANAGEMENT_OIDC_SCOPES",
    "session_secret": "COFY_MANAGEMENT_SESSION_SECRET",
    "session_lifetime": "COFY_MANAGEMENT_SESSION_LIFETIME",
    "secure_cookies": "COFY_MANAGEMENT_SECURE_COOKIES",
}


def oidc_config_from_env() -> OidcConfig:
    """The login configuration, from the environment; there is no running without one."""
    values = {field: os.environ[var] for field, var in OIDC_ENV_VARS.items() if os.environ.get(var)}
    try:
        return OidcConfig.model_validate(values)
    except ValidationError as exc:
        fields = ", ".join(OIDC_ENV_VARS[str(error["loc"][0])] for error in exc.errors())
        raise RuntimeError(f"Login is not configured correctly, check {fields}") from exc


def community_api_from_env() -> CommunityApi:
    """The communities' APIs, served each under its slug at the URL in the environment."""
    url = os.environ.get(COMMUNITIES_URL_ENV_VAR)
    if not url:
        raise RuntimeError(f"{COMMUNITIES_URL_ENV_VAR} must be set to where the communities' APIs are served")
    # Short, so an API that hangs is reported unavailable rather than making the console slow.
    return CommunityApi(httpx.Client(base_url=url, timeout=2.0))


oidc_config = oidc_config_from_env()
community_api = community_api_from_env()
users_file = data_dir() / "access" / "users.yaml"
users = FileUsersPersistence(users_file)
grants = FileGrantsPersistence(users_file)

app = FastAPI(title="Cofy Management API", version="0.1.0", description="Management API for Cofy")
add_exception_handlers(app)
install_session(app, oidc_config)
install_users(app, users)

app.include_router(AuthRouter(oidc_config, users, FileCommunitiesPersistence()).router)
app.include_router(CommunitiesRouter(FileCommunitiesPersistence(), grants, community_api).router)
app.include_router(ModulesRouter(FileModulesPersistence()).router)
app.include_router(AllowedModulesRouter().router)
app.include_router(ResourcesRouter(FileResourcesPersistence(), FileModulesPersistence()).router)
app.include_router(SecretsRouter(FileSecretsPersistence(), FileModulesPersistence(), FileResourcesPersistence()).router)
app.include_router(AllowedResourcesRouter().router)
app.include_router(GrantsRouter(grants, FileCommunitiesPersistence()).router)
app.include_router(StatusRouter(FileCommunitiesPersistence(), community_api).router)

# Serving the console's built assets is optional and off by default, so the API stays usable
# on its own (e.g. behind the Vite dev server's proxy). A deployment that wants a single
# origin - so the console's API client needs no base URL and there is no CORS to configure -
# sets this to the console's build output; it is mounted last so it never shadows the routers
# above, and `html=True` serves `index.html` for the app shell while leaving `/management/...` and `/auth/...`
# to the API (the console itself routes client-side by URL hash, so no other paths ever reach
# the server).
static_dir = os.environ.get(STATIC_DIR_ENV_VAR)
if static_dir:
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="console")
