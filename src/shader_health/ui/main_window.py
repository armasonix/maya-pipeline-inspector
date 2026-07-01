"""Minimal Maya Shader Health Inspector panel content."""
from __future__ import annotations

from typing import Any

PANEL_OBJECT_NAME = "shaderHealthInspectorPanel"
PANEL_TITLE = "Maya Shader Health Inspector"
PANEL_CONTENT_OBJECT_NAME = "shaderHealthInspectorPanelContent"


def build_main_widget(qt_widgets: Any) -> Any:
    """Build the first visible UI shell for the dockable Maya panel."""

    widget = qt_widgets.QWidget()
    widget.setObjectName(PANEL_CONTENT_OBJECT_NAME)

    layout = qt_widgets.QVBoxLayout(widget)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(8)

    title = qt_widgets.QLabel(PANEL_TITLE)
    title.setObjectName("shaderHealthInspectorTitle")
    layout.addWidget(title)

    description = qt_widgets.QLabel(
        "Dockable UI baseline. Validation, results, details, and export actions "
        "will be added by the next Milestone 6 issues."
    )
    description.setObjectName("shaderHealthInspectorDescription")
    description.setWordWrap(True)
    layout.addWidget(description)

    validate_button = qt_widgets.QPushButton("Validate Scene")
    validate_button.setObjectName("shaderHealthInspectorValidateSceneButton")
    validate_button.setEnabled(False)
    validate_button.setToolTip("Validation is added in a later Maya UI issue.")
    layout.addWidget(validate_button)

    layout.addStretch(1)
    return widget
