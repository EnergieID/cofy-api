from cofy.modules.discovery import discover_all_types

# As the runner's `main` does, so the settings in the tests can use every installed type.
discover_all_types()
