from typing import Dict

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QTextEdit,
    QCheckBox,
    QDialogButtonBox,
)


class AnnouncementDialog(QDialog):
    def __init__(self, data: Dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(data.get("title", "公告"))
        
        force = data.get("force", False)
        level = data.get("level", "info")
        
        label_title = QLabel(data.get("title", ""))
        title_style = "font-weight: bold; font-size: 14pt;"
        
        if level == "warning":
            title_style += " color: orange;"
        elif level == "critical":
            title_style += " color: red;"
            
        label_title.setStyleSheet(title_style)
        
        content = QTextEdit()
        content.setPlainText(data.get("content", ""))
        content.setReadOnly(True)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout()
        layout.addWidget(label_title)
        layout.addWidget(content)
        
        self.checkbox_ignore = None
        if not force:
            self.checkbox_ignore = QCheckBox("不再显示")
            layout.addWidget(self.checkbox_ignore)
            
        layout.addWidget(buttons)
        self.setLayout(layout)

    def should_ignore(self) -> bool:
        return self.checkbox_ignore.isChecked() if self.checkbox_ignore else False
