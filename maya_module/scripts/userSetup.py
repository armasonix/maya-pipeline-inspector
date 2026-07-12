"""Maya startup hook for Pipeline Inspector development module."""
from __future__ import annotations


def _install_pipeline_inspector_ui() -> None:
    """Load Pipeline Inspector via dual-install detection: native .mll, then .py, then bootstrap."""

    try:
        import pipeline_inspector_bootstrap as bootstrap
        from maya import cmds  # type: ignore[import-not-found]

        maya_year = bootstrap.resolve_maya_year(lambda: cmds.about(version=True))

        try:
            if cmds.pluginInfo(bootstrap.PLUGIN_NAME, query=True, loaded=True):
                return
        except Exception:
            pass

        for plugin_file in bootstrap.plugin_load_candidates(maya_year):
            try:
                cmds.loadPlugin(plugin_file, quiet=True)
                return
            except Exception:
                continue
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

    cmds.evalDeferred(_install_pipeline_inspector_ui)
except Exception:
    # Importing this module outside Maya should stay harmless.
    pass
