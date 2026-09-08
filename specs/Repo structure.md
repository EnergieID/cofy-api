```sh
cofy-cloud/                    # Monorepo root for CoFy Cloud platform
    .github/                   # CI/CD workflows (test, release, packaging, container pipelines)
    specs/                     # Product and architecture specs (requirements, structure, design decisions)
    docs/                      # Long-form documentation (API docs, ops guides, onboarding, ADRs)
    schemas/                   # Versioned JSON/YAML schemas for config and service contracts
    migrations/                # Config, module, and SQL migrations between versions

    packages/                  # Reusable packages and deployable core services
        api/                       # Python runtime API package (module execution and public API)
            src/
                cofy_api/              # API source code (app, modules, auth, runtime, settings)
            tests/                     # Package-level tests for API behavior and boundaries

        management-api/            # Python management API package (config CRUD and validation)
            src/
                cofy_management_api/   # Routers, domain services, persistence adapters
            tests/                     # Package-level tests for management API contracts

        orchestrator/              # Control-plane reconciler service (desired -> actual infrastructure state)
            src/
                cofy_orchestrator/     # Reconcilers, drivers, planning, runtime state handling
            tests/                     # Orchestrator unit/integration tests

        shared-py/                 # Shared Python contracts/utilities used across Python packages
            src/
                cofy_shared/           # Shared models, versioning helpers, common errors
            tests/                     # Tests for shared libraries

        web-components/            # Reusable Lit component library for CoFy frontends
            src/                      # Components, theming, shared UI primitives
            stories/                  # Storybook or component examples/documentation
            tests/                    # Component-level tests

        frontend-sdk/              # TypeScript SDK for API clients and generated types
            src/                      # API client, generated models, typed helpers

    apps/                      # End-user applications built from packages
        management-web/            # Default management interface (uses web-components + frontend-sdk)
            src/                      # App shell, pages, features, state integration
            public/                   # Static assets
            tests/                    # App-level UI and integration tests

        demo-sandbox/              # Local demo environment for showcasing and manual validation
            sample-config/            # Example configs for demo deployments
            seed-data/                # Seed data for local development and demos

    services/                  # Service-specific provisioning assets (not application logic)
        emqx/                      # MQTT broker config templates and bootstrap materials
        grafana/                   # Grafana provisioning and dashboard definitions
        postgres/                  # Postgres initialization, roles, and schema assets

    deploy/                    # Deployment compositions and environment overlays
        compose/                   # Docker Compose base stack and environment profiles
        k8s/                       # Kubernetes base manifests and dev/prod overlays

    tools/                     # Developer and automation scripts
        scripts/                   # Cross-package automation (generation, validation, build helpers)
        dev/                       # Local development convenience scripts

    testkits/                  # Cross-package/system test assets
        contract/                  # Contract tests between services and packages
        fixtures/                  # Shared test input data, payloads, and config fixtures
        integration/               # Full-stack integration test setups

    data/                      # Repository-level example and seed datasets
        examples/                  # Example data for docs, demos, and quickstarts
        seeds/                     # Seed data grouped by target service

    .vscode/                   # Workspace tasks, launch configs, and local editor settings
```