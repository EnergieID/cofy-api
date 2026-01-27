from fastapi import FastAPI

from src.cofy.docs_router import DocsRouter
from src.cofy.modules_router import ModulesRouter
from src.shared.module import Module


class Cofy:
    settings: dict
    fastApi: FastAPI
    modulesRouter: ModulesRouter

    def __init__(self, settings: dict):
        self.modules: dict[str, dict[str, Module]] = {}
        self.settings = settings
        self.fastApi = FastAPI(
            title=settings.get("title", "Cofy cloud API"),
            version=settings.get("version", "0.1.0"),
            description=settings.get(
                "description",
                "Modular cloud API for energy data",
            ),
            dependencies=settings.get("dependencies", []),
            docs_url=None,
            redoc_url=None,
            openapi_url=None,
        )
        self.modulesRouter = ModulesRouter(self)
        self.fastApi.include_router(self.modulesRouter)
        self.fastApi.include_router(
            DocsRouter(
                title=self.fastApi.title,
                version=self.fastApi.version,
                routes=self.fastApi.routes,
            )
        )

    def register_module(self, module: Module):
        if module.type not in self.modules:
            self.modules[module.type] = {}
        self.modules[module.type][module.name] = module
        module.cofy = self

        if module.router:
            self.fastApi.include_router(
                module.router,
                prefix=self.modulesRouter.module_endpoint(module),
            )

    def get_module(self, module_type: str, module_name: str) -> Module | None:
        return self.modules.get(module_type, {}).get(module_name)

    def get_modules_by_type(self, module_type: str) -> dict[str, Module]:
        return self.modules.get(module_type, {})
