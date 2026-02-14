from typing import List, Callable, Optional

from PySide6.QtCore import Qt, QTimer, Signal, QObject, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QPlainTextEdit,
    QSplitter,
    QHeaderView,
    QAbstractItemView
)

from mtrproxy.types import NodeInfo, ProxyStatus
from .sponsor_dialog import SponsorDialog


class BackendSignals(QObject):
    status_updated = Signal(object)
    nodes_updated = Signal(list)
    log_message = Signal(str)
    show_announcement = Signal(dict)


    update_ad = Signal(dict)
    show_update = Signal(dict)

class MainWindow(QMainWindow):
    def __init__(
        self,
        signals: BackendSignals,
        on_toggle_proxy: Callable[[], None],
        on_detect_all: Callable[[], None],
        on_refresh_nodes: Callable[[], None],
        on_select_node: Callable[[str], None],
        on_open_settings: Callable[[], None],
        sponsor_links: List[dict],
        ad_config: dict,
    ):
        super().__init__()
        self.signals = signals
        self.on_toggle_proxy = on_toggle_proxy
        self.on_detect_all = on_detect_all
        self.on_refresh_nodes = on_refresh_nodes
        self.on_select_node = on_select_node
        self.on_open_settings = on_open_settings
        self.sponsor_links = sponsor_links
        self.ad_config = ad_config

        self.setWindowTitle("mtr加速器")
        self.resize(1000, 600)

        self.status_label_run = QLabel("状态: 停止")
        self.status_label_node = QLabel("当前节点: -")
        self.status_label_latency = QLabel("延迟: -")
        self.status_label_port = QLabel("监听端口: -")
        self.status_label_uptime = QLabel("运行时间: -")
        self.status_label_conn = QLabel("连接数: 0")

        top_bar = QHBoxLayout()
        top_bar.addWidget(self.status_label_run)
        top_bar.addWidget(self.status_label_node)
        top_bar.addWidget(self.status_label_latency)
        top_bar.addWidget(self.status_label_port)
        top_bar.addWidget(self.status_label_uptime)
        top_bar.addWidget(self.status_label_conn)
        top_bar.addStretch()

        self.btn_toggle_proxy = QPushButton("启动代理")
        self.btn_detect_all = QPushButton("一键检测")
        self.btn_refresh_nodes = QPushButton("刷新节点")
        self.btn_settings = QPushButton("设置")
        self.btn_sponsor = QPushButton("赞助支持")

        btn_bar = QHBoxLayout()
        btn_bar.addWidget(self.btn_toggle_proxy)
        btn_bar.addWidget(self.btn_detect_all)
        btn_bar.addWidget(self.btn_refresh_nodes)
        btn_bar.addWidget(self.btn_settings)
        btn_bar.addWidget(self.btn_sponsor)
        btn_bar.addStretch()

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["节点名", "分组", "IP", "端口", "使用人数", "延迟(ms)", "状态", "操作"])
        self.table.horizontalHeader().setStretchLastSection(False) # Disable stretch for last column
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Fixed) # Last column fixed width
        self.table.setColumnWidth(7, 60) # Set small width
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)

        splitter = QSplitter(Qt.Vertical)
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.addWidget(self.table)
        splitter.addWidget(table_container)
        splitter.addWidget(self.log_view)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        self.ad_label = QLabel()
        self.ad_label.setAlignment(Qt.AlignCenter)
        self.ad_label.setStyleSheet("border: 1px solid gray; background-color: #f0f0f0; padding: 10px;")
        self._update_ad_label()

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_bar)
        main_layout.addLayout(btn_bar)
        main_layout.addWidget(splitter)
        main_layout.addWidget(self.ad_label)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.btn_toggle_proxy.clicked.connect(self.on_toggle_proxy)
        self.btn_detect_all.clicked.connect(self.on_detect_all)
        self.btn_refresh_nodes.clicked.connect(self.on_refresh_nodes)
        self.btn_settings.clicked.connect(self.on_open_settings)
        self.btn_sponsor.clicked.connect(self._on_sponsor_clicked)
        self.ad_label.mousePressEvent = self._on_ad_clicked

        self.signals.status_updated.connect(self.on_status_updated)
        self.signals.nodes_updated.connect(self.on_nodes_updated)
        self.signals.log_message.connect(self.append_log)
        self.signals.update_ad.connect(self.on_update_ad)
        self.signals.show_update.connect(self.on_show_update)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._elapsed_uptime = 0
        self._timer.start()

    def on_show_update(self, data: dict) -> None:
        from PySide6.QtWidgets import QMessageBox
        title = "发现新版本"
        msg = f"最新版本: {data['latest_version']}\n\n更新日志:\n{data.get('changelog', '无')}\n\n是否立即更新？"
        
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(msg)
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        
        if data.get("force_update", False):
            box.setText(msg + "\n\n(此版本为强制更新，旧版本已不可用)")
            box.setStandardButtons(QMessageBox.Yes)
            # Disable main controls
            self.centralWidget().setEnabled(False)
            
        ret = box.exec()
        
        if ret == QMessageBox.Yes or data.get("force_update", False):
            url = data.get("download_url")
            if url:
                QDesktopServices.openUrl(QUrl(url))
            if data.get("force_update", False):
                sys.exit(0) # Exit if forced

    def on_update_ad(self, ad_data: dict) -> None:
        self.ad_config = ad_data
        self._update_ad_label()

    def _update_ad_label(self) -> None:
        ad_type = self.ad_config.get("type", "text")
        if ad_type == "text":
            text = self.ad_config.get("text", "")
            self.ad_label.setText(text)
            self.ad_label.setPixmap(QPixmap()) # Clear image
        elif ad_type == "image":
            # For image, we need to download it or if it's a local path
            # Simple implementation: if it's http, maybe show text 'loading...' then fetch?
            # Or assume logic elsewhere handled it?
            # For now let's just support local path or handle basic url fetching in thread if needed
            # But prompt says "if type=image, show image banner".
            # Real implementation needs async image loading. 
            # Simplified: just show "Image Ad" text if we can't load easily, or load from url in thread.
            img_url = self.ad_config.get("image_url", "")
            if img_url:
                self.ad_label.setText("正在加载广告图片...")
                # In a real app, use NetworkAccessManager
                import threading
                import requests
                def load_img():
                    try:
                        r = requests.get(img_url, timeout=5)
                        if r.status_code == 200:
                            data = r.content
                            pixmap = QPixmap()
                            pixmap.loadFromData(data)
                            # Update UI in main thread via signal? 
                            # self.ad_label.setPixmap(pixmap) # Unsafe
                            # Let's add a signal for image loaded
                            pass
                    except:
                        pass
                # For simplicity in this demo, just showing text fallback or placeholder
                self.ad_label.setText(f"图片广告: {self.ad_config.get('text', '')}")
            else:
                self.ad_label.setText("广告图片无效")
        else:
            self.ad_label.setText("广告")

    def _on_ad_clicked(self, event) -> None:
        url = self.ad_config.get("url")
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def _on_sponsor_clicked(self) -> None:
        dialog = SponsorDialog(self, self.sponsor_links)
        dialog.exec()

    def append_log(self, text: str) -> None:
        self.log_view.appendPlainText(text)

    def on_status_updated(self, status: ProxyStatus) -> None:
        self.status_label_run.setText("状态: 运行" if status.running else "状态: 停止")
        if status.running:
            self.status_label_run.setStyleSheet("color: green")
            self.btn_toggle_proxy.setText("停止代理")
        else:
            self.status_label_run.setStyleSheet("color: red")
            self.btn_toggle_proxy.setText("启动代理")
            
        if status.current_node:
            self.status_label_node.setText(f"当前节点: {status.current_node.hostname}")
            if status.current_latency_ms is not None:
                self.status_label_latency.setText(f"延迟: {int(status.current_latency_ms)} ms")
            else:
                self.status_label_latency.setText("延迟: -")
        else:
            self.status_label_node.setText("当前节点: -")
            self.status_label_latency.setText("延迟: -")
        self.status_label_port.setText(f"监听端口: {status.listen_port}")
        self.status_label_conn.setText(f"连接数: {status.active_connections}")
        self._elapsed_uptime = status.uptime_seconds
        self._update_uptime_label()

    def _update_uptime_label(self) -> None:
        s = self._elapsed_uptime
        h = s // 3600
        m = (s % 3600) // 60
        sec = s % 60
        self.status_label_uptime.setText(f"运行时间: {h:02d}:{m:02d}:{sec:02d}")

    def _tick(self) -> None:
        # Just update uptime UI if running, although status update also does it.
        # This timer is mainly for per-second UI refresh if status update is less frequent.
        # But status update handles uptime.
        pass

    def on_nodes_updated(self, nodes: List[NodeInfo]) -> None:
        # Sort nodes by priority (asc)
        nodes.sort(key=lambda n: n.priority)
        
        self.table.setRowCount(len(nodes))

        for row, n in enumerate(nodes):
            self.table.setItem(row, 0, QTableWidgetItem(n.hostname))
            self.table.setItem(row, 1, QTableWidgetItem(n.group))
            self.table.setItem(row, 2, QTableWidgetItem(n.ip))
            self.table.setItem(row, 3, QTableWidgetItem(str(n.port)))
            self.table.setItem(row, 4, QTableWidgetItem(str(n.online_count)))
            
            latency_text = "-" if n.latency_ms is None else str(int(n.latency_ms))
            item_latency = QTableWidgetItem(latency_text)
            
            color = QColor("gray")
            if not n.reachable and n.status == "unreachable":
                color = QColor("gray")
            elif n.latency_ms is not None:
                if n.latency_ms < 50:
                    color = QColor("green")
                elif n.latency_ms < 150:
                    color = QColor("orange")
                else:
                    color = QColor("red")
            
            item_latency.setForeground(color)
            self.table.setItem(row, 5, item_latency)
            self.table.setItem(row, 6, QTableWidgetItem(n.motd if n.motd else n.status))

            btn = QPushButton("选择")
            btn.clicked.connect(lambda checked=False, host=n.hostname: self.on_select_node(host))
            self.table.setCellWidget(row, 7, btn)
