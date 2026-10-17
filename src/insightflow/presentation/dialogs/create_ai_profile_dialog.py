"""Create/edit-AI-profile dialog.

Intentionally small: an AI profile controls analysis *instructions* only.
Provider/model configuration remains controlled by ``AISettings``
(``INSIGHTFLOW_AI_*`` environment variables) and is never exposed here.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from insightflow.application.dto.models import AIProfileDto

DEFAULT_OUTPUT_SCHEMA_VERSION = "v1"

# (label, AIOutputStyle value)
_OUTPUT_STYLES = (
    ("Analysis — summary, key facts, sentiment, market impact", "ANALYSIS"),
    ("Custom text — exactly what the instructions ask for", "CUSTOM_TEXT"),
)


@dataclass(frozen=True, slots=True)
class CreateAIProfileFormData:
    name: str
    description: str
    instructions: str
    output_schema_version: str
    assign_to_selected_topic: bool
    output_style: str = "ANALYSIS"


class CreateAIProfileDialog(QDialog):
    """Collects the fields required by ``AIProfile.create(...)``.

    Field-level validation is intentionally left to the existing
    domain/application validation (``AIProfile.__post_init__`` via
    ``CreateAIProfileUseCase``) rather than duplicated here — the same
    convention already used by ``CreateTopicDialog``.

    Passing ``existing`` opens it in edit mode, pre-filled from that profile.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        topic_name: str | None = None,
        existing: AIProfileDto | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit AI Profile" if existing else "Create AI Profile")
        self.setModal(True)
        self.setMinimumWidth(560)
        self.setObjectName("CreateAIProfileDialog")

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._name = QLineEdit()
        self._name.setObjectName("AIProfileNameInput")
        self._name.setAccessibleName("AI profile name")

        self._description = QLineEdit()
        self._description.setObjectName("AIProfileDescriptionInput")
        self._description.setAccessibleName("AI profile description")
        self._description.setPlaceholderText("Optional description")

        self._instructions = QPlainTextEdit()
        self._instructions.setObjectName("AIProfileInstructionsInput")
        self._instructions.setAccessibleName("AI profile instructions")
        self._instructions.setPlaceholderText(
            "What should the AI look for and how should it interpret it?"
        )
        self._instructions.setFixedHeight(220)

        self._output_schema_version = QLineEdit(DEFAULT_OUTPUT_SCHEMA_VERSION)
        self._output_schema_version.setObjectName("AIProfileOutputSchemaInput")
        self._output_schema_version.setAccessibleName(
            "AI profile output schema version"
        )

        self._output_style = QComboBox()
        self._output_style.setObjectName("AIProfileOutputStyleInput")
        self._output_style.setAccessibleName("AI profile output style")
        for label, value in _OUTPUT_STYLES:
            self._output_style.addItem(label, value)

        if existing is not None:
            self._name.setText(existing.name)
            self._description.setText(existing.description or "")
            self._instructions.setPlainText(existing.instructions)
            self._output_schema_version.setText(existing.output_schema_version)
            # Editing changes the analysis intent only, never the output schema.
            self._output_schema_version.setReadOnly(True)
            style_index = self._output_style.findData(existing.output_style)
            self._output_style.setCurrentIndex(max(style_index, 0))
            topic_name = None

        form.addRow("Name", self._name)
        form.addRow("Description", self._description)
        form.addRow("Output style", self._output_style)
        form.addRow("Instructions", self._instructions)
        form.addRow("Output schema version", self._output_schema_version)
        layout.addLayout(form)

        self._assign_to_topic: QCheckBox | None = None
        if topic_name:
            self._assign_to_topic = QCheckBox(
                f"Assign to '{topic_name}' after creation"
            )
            self._assign_to_topic.setObjectName("AIProfileAssignToTopicCheckbox")
            self._assign_to_topic.setChecked(True)
            layout.addWidget(self._assign_to_topic)

        format_hint = QLabel(
            "Analysis: the AI returns a fixed analysis (summary, key facts, "
            "why it matters, what to watch, sentiment, market impact) guided "
            "by your instructions. Custom text: the AI writes exactly what "
            "your instructions ask for — e.g. a Tamil news script — shown as "
            "Generated content, plus a one-line summary for lists."
        )
        format_hint.setObjectName("MutedLabel")
        format_hint.setWordWrap(True)
        layout.addWidget(format_hint)

        if existing is not None:
            version_hint = QLabel(
                f"Currently version {existing.version}. Changing the "
                "instructions saves a new version; earlier analyses keep "
                "the version they used. Use Re-analyze to apply it to an "
                "existing event."
            )
            version_hint.setObjectName("MutedLabel")
            version_hint.setWordWrap(True)
            layout.addWidget(version_hint)

        hint = QLabel(
            "AI provider/model configuration is controlled separately by "
            "AISettings (INSIGHTFLOW_AI_* environment variables) — this "
            "profile only defines analysis instructions."
        )
        hint.setObjectName("MutedLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def form_data(self) -> CreateAIProfileFormData:
        return CreateAIProfileFormData(
            name=self._name.text().strip(),
            description=self._description.text().strip(),
            instructions=self._instructions.toPlainText().strip(),
            output_schema_version=(
                self._output_schema_version.text().strip()
                or DEFAULT_OUTPUT_SCHEMA_VERSION
            ),
            assign_to_selected_topic=(
                self._assign_to_topic.isChecked()
                if self._assign_to_topic is not None
                else False
            ),
            output_style=str(self._output_style.currentData() or "ANALYSIS"),
        )
