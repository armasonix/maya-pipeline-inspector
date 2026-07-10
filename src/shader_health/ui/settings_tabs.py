"""Settings tab model for the Maya Shader Health Inspector panel."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

SETTINGS_BASIC_TAB_OBJECT_NAME = "shaderHealthInspectorSettingsBasicTab"
SETTINGS_ADVANCED_TAB_OBJECT_NAME = "shaderHealthInspectorSettingsAdvancedTab"
SETTINGS_CONNECTORS_TAB_OBJECT_NAME = "shaderHealthInspectorSettingsConnectorsTab"
SETTINGS_STUDIO_TAB_OBJECT_NAME = "shaderHealthInspectorSettingsStudioTab"
SETTINGS_STUDIO_ENVIRONMENT_TAB_OBJECT_NAME = "shaderHealthInspectorSettingsStudioEnvironmentTab"
SETTINGS_BUG_REPORT_TAB_OBJECT_NAME = "shaderHealthInspectorSettingsBugReportTab"


@dataclass(frozen=True)
class SettingsTabSpec:
    """Metadata for one settings category tab."""

    tab_id: str
    title: str
    object_name: str
    placeholder_text: str


SETTINGS_TAB_SPECS: tuple[SettingsTabSpec, ...] = (
    SettingsTabSpec(
        tab_id="basic",
        title="Basic",
        object_name=SETTINGS_BASIC_TAB_OBJECT_NAME,
        placeholder_text="",
    ),
    SettingsTabSpec(
        tab_id="advanced",
        title="Advanced",
        object_name=SETTINGS_ADVANCED_TAB_OBJECT_NAME,
        placeholder_text=(
            "Advanced options will live here (extra rule roots, debug logging, performance caps)."
        ),
    ),
    SettingsTabSpec(
        tab_id="connectors",
        title="Connectors",
        object_name=SETTINGS_CONNECTORS_TAB_OBJECT_NAME,
        placeholder_text="",
    ),
    SettingsTabSpec(
        tab_id="studio",
        title="Studio",
        object_name=SETTINGS_STUDIO_TAB_OBJECT_NAME,
        placeholder_text="",
    ),
    SettingsTabSpec(
        tab_id="studio_environment",
        title="Studio Environment",
        object_name=SETTINGS_STUDIO_ENVIRONMENT_TAB_OBJECT_NAME,
        placeholder_text=(
            "Studio network path roots and variable aliases will live here "
            "(texture_root, asset_root, cache_root, render_root, ${STUDIO_TEXTURE_ROOT})."
        ),
    ),
    SettingsTabSpec(
        tab_id="bug_report",
        title="Bug Report",
        object_name=SETTINGS_BUG_REPORT_TAB_OBJECT_NAME,
        placeholder_text=(
            "Bug report relay settings will live here (relay URL, API key, screenshot policy, "
            "privacy notice). Submissions route through a studio-hosted HTTPS relay."
        ),
    ),
)


def settings_tab_titles() -> tuple[str, ...]:
    """Return settings tab titles in display order."""

    return tuple(spec.title for spec in SETTINGS_TAB_SPECS)


def get_settings_tab_spec(tab_id: str) -> SettingsTabSpec | None:
    for spec in SETTINGS_TAB_SPECS:
        if spec.tab_id == tab_id:
            return spec
    return None


def build_placeholder_tab(
    qt_widgets: Any,
    spec: SettingsTabSpec,
    *,
    builder: Callable[[Any], Any] | None = None,
) -> Any:
    """Build a settings tab widget with a stable object name."""

    if builder is not None:
        tab = builder(qt_widgets)
        tab.setObjectName(spec.object_name)
        return tab

    tab = qt_widgets.QWidget()
    tab.setObjectName(spec.object_name)
    layout = qt_widgets.QVBoxLayout(tab)
    layout.setContentsMargins(8, 8, 8, 8)
    label = qt_widgets.QLabel(spec.placeholder_text)
    label.setWordWrap(True)
    layout.addWidget(label)
    layout.addStretch(1)
    return tab
