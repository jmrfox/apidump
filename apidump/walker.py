from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType

from .models import ImportErrorInfo, WalkResult


def _safe_import(
    module_name: str,
) -> tuple[ModuleType | None, ImportErrorInfo | None]:
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        # Handle pytest skip exceptions (optional dependencies in test files)
        error_type = type(exc).__name__
        if error_type == "Skipped":
            error_type = "OptionalDependencyMissing"
        error = ImportErrorInfo(
            module_name=module_name,
            error_type=error_type,
            message=str(exc),
        )
        return None, error
    return module, None


def walk_package(
    package_name: str,
    include_private: bool = False,
    exclude_tests: bool = True,
) -> WalkResult:
    root_module, root_error = _safe_import(package_name)
    if root_module is None:
        error_type = root_error.error_type if root_error is not None else "ImportError"
        message = root_error.message if root_error is not None else ""
        raise ImportError(
            f"Failed to import package '{package_name}': " f"{error_type}: {message}"
        )

    modules: list[ModuleType] = [root_module]
    import_errors: list[ImportErrorInfo] = []

    if root_error is not None:
        import_errors.append(root_error)

    package_path = getattr(root_module, "__path__", None)
    if not package_path:
        return WalkResult(
            package_name=package_name,
            modules=tuple(modules),
            import_errors=tuple(import_errors),
        )

    discovered_names = sorted(
        module_info.name
        for module_info in pkgutil.walk_packages(
            package_path,
            prefix=f"{package_name}.",
        )
        if (
            include_private
            or all(not part.startswith("_") for part in module_info.name.split("."))
        )
        and (not exclude_tests or not _is_test_module(module_info.name))
    )

    for module_name in discovered_names:
        module, error = _safe_import(module_name)
        if module is not None:
            modules.append(module)
        elif error is not None:
            import_errors.append(error)

    return WalkResult(
        package_name=package_name,
        modules=tuple(modules),
        import_errors=tuple(import_errors),
    )


def _is_test_module(module_name: str) -> bool:
    """Check if a module is a test module (named 'test' or 'tests')."""
    parts = module_name.split(".")
    return any(part in ("test", "tests") for part in parts)
