from typing import Dict

from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QPushButton,
    QDialogButtonBox,
    QVBoxLayout,
)


class SettingsDialog(QDialog):
    def __init__(self, config_data: Dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")

        self.edit_listen_port = QSpinBox()
        self.edit_listen_port.setRange(1, 65535)
        self.edit_listen_port.setValue(config_data.get("listen_port", 1080))

        self.chk_autostart = QCheckBox("Windows 开机自启动")
        self.chk_autostart.setChecked(config_data.get("windows_autostart", False))

        form = QFormLayout()
        form.addRow("监听端口", self.edit_listen_port)
        form.addRow("", self.chk_autostart)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def get_result(self) -> Dict:
        return {
            "listen_port": self.edit_listen_port.value(),
            "windows_autostart": self.chk_autostart.isChecked(),
        }
