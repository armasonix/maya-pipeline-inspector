"""Maya startup hook for Pipeline Inspector development module."""
from __future__ import annotations

import os
from typing import Any

_DEFERRED_FLAG = "_pipeline_inspector_deferred"
_STARTUP_FLAG = "_pipeline_inspector_startup_done"


def _log_bootstrap(bootstrap: Any, *args: object, **kwargs: object) -> None:
    logger = getattr(bootstrap, "_debug_log", None)
    if logger is None:
        return
    try:
        logger(*args, **kwargs)
    except Exception:
        return


def _install_pipeline_inspector_ui() -> None:
    """Load Pipeline Inspector via dual-install detection: native .mll, then .py, then bootstrap."""

    import __main__

    if getattr(__main__, _STARTUP_FLAG, False):
        return

    bootstrap = None
    try:
        import pipeline_inspector_bootstrap as bootstrap
        from maya import cmds  # type: ignore[import-not-found]

        maya_year = bootstrap.resolve_maya_year(lambda: cmds.about(version=True))
        diagnostics: dict[str, object] = {"maya_year": maya_year}
        describe = getattr(bootstrap, "describe_dual_install", None)
        if callable(describe):
            diagnostics.update(describe(maya_year))
        module_root = getattr(bootstrap, "module_root", None)
        _log_bootstrap(
            bootstrap,
            "userSetup.py:_install_pipeline_inspector_ui",
            "deferred install started",
            {
                "MAYA_MODULE_PATH": os.environ.get("MAYA_MODULE_PATH"),
                "module_root": str(module_root() if callable(module_root) else ""),
                **diagnostics,
            },
            "A",
        )

        try:
            if cmds.pluginInfo(bootstrap.PLUGIN_NAME, query=True, loaded=True):
                _log_bootstrap(
                    bootstrap,
                    "userSetup.py:_install_pipeline_inspector_ui",
                    "plugin already loaded",
                    {"plugin_name": bootstrap.PLUGIN_NAME},
                    "D",
                )
                setattr(__main__, _STARTUP_FLAG, True)
                return
        except Exception as exc:
            _log_bootstrap(
                bootstrap,
                "userSetup.py:_install_pipeline_inspector_ui",
                "pluginInfo check failed",
                {"error": str(exc)},
                "D",
            )

        load_failures: list[dict[str, str]] = []
        for plugin_file in bootstrap.plugin_load_candidates(maya_year):
            try:
                cmds.loadPlugin(plugin_file, quiet=True)
                autoload_set = bootstrap.enable_plugin_autoload(plugin_file, cmds)
                _log_bootstrap(
                    bootstrap,
                    "userSetup.py:_install_pipeline_inspector_ui",
                    "loadPlugin succeeded",
                    {"plugin_file": plugin_file, "autoload_set": autoload_set},
                    "C",
                )
                setattr(__main__, _STARTUP_FLAG, True)
                return
            except Exception as exc:
                load_failures.append(
                    {"plugin_file": plugin_file, "error": str(exc)},
                )
                continue
        _log_bootstrap(
            bootstrap,
            "userSetup.py:_install_pipeline_inspector_ui",
            "all loadPlugin candidates failed",
            {"failures": load_failures},
            "C",
        )
    except Exception as exc:
        if bootstrap is not None:
            _log_bootstrap(
                bootstrap,
                "userSetup.py:_install_pipeline_inspector_ui",
                "plugin load loop failed",
                {"error": str(exc)},
                "B",
            )

    try:
        import pipeline_inspector_bootstrap as bootstrap

        bootstrap.install_ui()
        _log_bootstrap(
            bootstrap,
            "userSetup.py:_install_pipeline_inspector_ui",
            "module-only fallback succeeded",
            {},
            "E",
        )
        setattr(__main__, _STARTUP_FLAG, True)
    except Exception as exc:  # pragma: no cover - Maya startup visibility only.
        try:
            import pipeline_inspector_bootstrap as bootstrap

            _log_bootstrap(
                bootstrap,
                "userSetup.py:_install_pipeline_inspector_ui",
                "module-only fallback failed",
                {"error": str(exc)},
                "E",
            )
        except Exception:
            pass
        try:
            from maya import cmds  # type: ignore[import-not-found]

            cmds.warning(f"Pipeline Inspector UI install failed: {exc}")
        except Exception:
            raise


try:
    from maya import cmds  # type: ignore[import-not-found]

    try:
        import pipeline_inspector_bootstrap as bootstrap

        _log_bootstrap(
            bootstrap,
            "userSetup.py:module_import",
            "userSetup imported",
            {"MAYA_MODULE_PATH": os.environ.get("MAYA_MODULE_PATH")},
            "A",
        )
    except Exception:
        pass

    import __main__

    if not getattr(__main__, _DEFERRED_FLAG, False):
        setattr(__main__, _DEFERRED_FLAG, True)
        cmds.evalDeferred(_install_pipeline_inspector_ui)
except Exception:
    # Importing this module outside Maya should stay harmless.
    pass
