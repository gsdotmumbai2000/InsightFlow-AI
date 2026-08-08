"""Create-topic dialog (supports optional Gmail label binding)."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True, slots=True)
class CreateTopicFormData:
    name: str
    description: str
    ai_profile_id: str
    gmail_label_id: str


class CreateTopicDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Create Topic")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setObjectName("CreateTopicDialog")

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._name = QLineEdit()
        self._name.setObjectName("TopicNameInput")
        self._name.setAccessibleName("Topic name")
        self._description = QPlainTextEdit()
        self._description.setObjectName("TopicDescriptionInput")
        self._description.setAccessibleName("Topic description")
        self._description.setPlaceholderText("Optional description")
        self._description.setFixedHeight(80)
        self._ai_profile = QLineEdit()
        self._ai_profile.setObjectName("TopicAiProfileInput")
        self._ai_profile.setAccessibleName("AI profile ID")
        self._ai_profile.setPlaceholderText("Optional AI profile ID")
        self._gmail_label = QLineEdit()
        self._gmail_label.setObjectName("TopicGmailLabelInput")
        self._gmail_label.setAccessibleName("Optional Gmail label ID")
        self._gmail_label.setPlaceholderText("Optional — or map in Settings → Gmail")
        form.addRow("Name", self._name)
        form.addRow("Description", self._description)
        form.addRow("AI profile ID", self._ai_profile)
        form.addRow("Gmail label ID", self._gmail_label)
        layout.addLayout(form)

        hint = QLabel(
            "Leave Gmail label empty to create a local topic. "
            "Gmail label mapping is also available under Settings after Connect Gmail."
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

    def form_data(self) -> CreateTopicFormData:
        return CreateTopicFormData(
            name=self._name.text().strip(),
            description=self._description.toPlainText().strip(),
            ai_profile_id=self._ai_profile.text().strip(),
            gmail_label_id=self._gmail_label.text().strip(),
        )
