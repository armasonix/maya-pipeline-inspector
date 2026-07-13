"""Maya startup hook for Pipeline Inspector development module."""
from __future__ import annotations

_DEFERRED_FLAG = "_pipeline_inspector_deferred"
_STARTUP_FLAG = "_pipeline_inspector_startup_done"


def _install_pipeline_inspector_ui() -> None:
    """Load Pipeline Inspector via dual-install detection: native .mll, then .py, then bootstrap."""

    import __main__

    if getattr(__main__, _STARTUP_FLAG, False):
        return
    setattr(__main__, _STARTUP_FLAG, True)

    try:
        import pipeline_inspector_bootstrap as bootstrap
        from maya import cmds  # type: ignore[import-not-found]

        maya_year = bootstrap.resolve_maya_year(lambda: cmds.about(version=True))
        bootstrap.apply_pending_native_plugin_binaries()
        canonical_path = bootstrap.canonical_plugin_path(maya_year)

        try:
            if cmds.pluginInfo(bootstrap.PLUGIN_NAME, query=True, loaded=True):
                if canonical_path:
                    bootstrap.enable_plugin_autoload(canonical_path, cmds)
                return
        except Exception:
            pass

        load_failures: list[dict[str, str]] = []
        for plugin_file in bootstrap.plugin_load_candidates(maya_year):
            try:
                if cmds.pluginInfo(bootstrap.PLUGIN_NAME, query=True, loaded=True):
                    bootstrap.enable_plugin_autoload(canonical_path or plugin_file, cmds)
                    return
                cmds.loadPlugin(plugin_file, quiet=True)
                bootstrap.enable_plugin_autoload(canonical_path or plugin_file, cmds)
                return
            except Exception as exc:
                load_failures.append(
                    {"plugin_file": plugin_file, "error": str(exc)},
                )
                continue
        _ = load_failures
    except Exception:
        pass

    try:
        import pipeline_inspector_bootstrap as bootstrap

        bootstrap.install_ui()
    except Exception as exc:  # pragma: no cover - Maya startup visibility only.
        try:
            from maya import cmds  # type: ignore[import-not-found]

            cmds.warning(f"Pipeline Inspector UI install failed: {exc}")
        except Exception:
            raise


try:
    from maya import cmds  # type: ignore[import-not-found]

    import __main__

    if not getattr(__main__, _DEFERRED_FLAG, False):
        setattr(__main__, _DEFERRED_FLAG, True)
        cmds.evalDeferred(_install_pipeline_inspector_ui)
except Exception:
    # Importing this module outside Maya should stay harmless.
    pass
