"""Maya startup hook for Shader Health Inspector development module."""
from __future__ import annotations


def _install_shader_health_ui() -> None:
    try:
        import shader_health_inspector_bootstrap

        shader_health_inspector_bootstrap.install_ui()
    except Exception as exc:  # pragma: no cover - Maya startup visibility only.
        try:
            from maya import cmds  # type: ignore[import-not-found]

            cmds.warning(f"Shader Health Inspector UI install failed: {exc}")
        except Exception:
            raise


try:
    from maya import cmds  # type: ignore[import-not-found]

    cmds.evalDeferred(_install_shader_health_ui)
except Exception:
    # Importing this module outside Maya should stay harmless.
    pass
