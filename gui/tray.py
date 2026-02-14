from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QMainWindow


class TrayIcon(QSystemTrayIcon):
    def __init__(self, window: QMainWindow, on_toggle_proxy, parent=None):
        super().__init__(parent)
        self.window = window
        self.on_toggle_proxy = on_toggle_proxy

        # Try to set a standard icon if none provided
        self.setIcon(QIcon.fromTheme("network-server")) 
        if window.windowIcon():
             self.setIcon(window.windowIcon())

        self.menu = QMenu()
        act_show = QAction("显示主界面", self.menu)
        self.act_toggle = QAction("启动/停止代理", self.menu)
        act_quit = QAction("退出", self.menu)

        act_show.triggered.connect(self._show_main)
        self.act_toggle.triggered.connect(on_toggle_proxy)
        act_quit.triggered.connect(self._quit)

        self.menu.addAction(act_show)
        self.menu.addAction(self.act_toggle)
        self.menu.addSeparator()
        self.menu.addAction(act_quit)

        self.setContextMenu(self.menu)
        self.setToolTip("智能线路优选代理")

        self.activated.connect(self._on_activated)

    def update_status(self, running: bool):
        self.act_toggle.setText("停止代理" if running else "启动代理")

    def _show_main(self) -> None:
        self.window.showNormal()
        self.window.activateWindow()

    def _quit(self) -> None:
        self.window.close()

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            if self.window.isHidden():
                self._show_main()
            else:
                self.window.hide()
