"""Maya Python plugin entry for Pipeline Inspector."""
from __future__ import annotations

PLUGIN_VENDOR = "Pipeline Inspector"
PLUGIN_VERSION = "0.5.0"
PLUGIN_NAME = "pipeline_inspector"


def maya_useAPIVersion() -> None:
    """Declare the Maya API version used by this plugin."""


def initializePlugin(mobject: object) -> None:
    """Load Pipeline Inspector UI entrypoints when the plugin is enabled."""

    import maya.OpenMayaMPx as OpenMayaMPx  # type: ignore[import-not-found]

    plugin = OpenMayaMPx.MFnPlugin(mobject, PLUGIN_VENDOR, PLUGIN_VERSION, "Any")
    _ = plugin

    def _install_ui_deferred() -> None:
        import pipeline_inspector_bootstrap

        pipeline_inspector_bootstrap.install_ui()

    def _enforce_panel_dock_deferred() -> None:
        try:
            import pipeline_inspector_bootstrap as bootstrap

            bootstrap._ensure_source_path()
            from pipeline_inspector.maya.ui_launcher import enforce_startup_panel_layout

            enforce_startup_panel_layout()
        except Exception:
            pass

    try:
        from maya import cmds  # type: ignore[import-not-found]

        cmds.evalDeferred(_install_ui_deferred)
        cmds.evalDeferred(_enforce_panel_dock_deferred)
    except Exception:
        _install_ui_deferred()


def uninitializePlugin(mobject: object) -> None:
    """Remove Pipeline Inspector UI entrypoints when the plugin is disabled."""

    import maya.OpenMayaMPx as OpenMayaMPx  # type: ignore[import-not-found]

    plugin = OpenMayaMPx.MFnPlugin(mobject)
    _ = plugin

    import pipeline_inspector_bootstrap

    pipeline_inspector_bootstrap.uninstall_ui()
