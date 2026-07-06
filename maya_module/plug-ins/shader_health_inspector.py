"""Maya Python plugin entry for Shader Health Inspector."""
from __future__ import annotations

PLUGIN_VENDOR = "Shader Health Inspector"
PLUGIN_VERSION = "0.3.0"
PLUGIN_NAME = "shader_health_inspector"


def maya_useAPIVersion() -> None:
    """Declare the Maya API version used by this plugin."""


def initializePlugin(mobject: object) -> None:
    """Load Shader Health UI entrypoints when the plugin is enabled."""

    import maya.OpenMayaMPx as OpenMayaMPx  # type: ignore[import-not-found]

    plugin = OpenMayaMPx.MFnPlugin(mobject, PLUGIN_VENDOR, PLUGIN_VERSION, "Any")
    _ = plugin

    def _install_ui_deferred() -> None:
        import shader_health_inspector_bootstrap

        shader_health_inspector_bootstrap.install_ui()

    try:
        from maya import cmds  # type: ignore[import-not-found]

        cmds.evalDeferred(_install_ui_deferred)
    except Exception:
        _install_ui_deferred()


def uninitializePlugin(mobject: object) -> None:
    """Remove Shader Health UI entrypoints when the plugin is disabled."""

    import maya.OpenMayaMPx as OpenMayaMPx  # type: ignore[import-not-found]

    plugin = OpenMayaMPx.MFnPlugin(mobject)
    _ = plugin

    import shader_health_inspector_bootstrap

    shader_health_inspector_bootstrap.uninstall_ui()
