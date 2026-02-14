from typing import List, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, 
    QTextBrowser, QFrame, QScrollArea, QWidget, QSizePolicy
)
from PySide6.QtCore import Qt, QUrl, Signal, QThread
from PySide6.QtGui import QDesktopServices, QPixmap, QFont
import requests

class ImageLoader(QThread):
    loaded = Signal(bytes, QLabel)
    
    def __init__(self, url: str, label: QLabel):
        super().__init__()
        self.url = url
        self.label = label
        
    def run(self):
        try:
            if self.url.startswith("http"):
                resp = requests.get(self.url, timeout=5)
                if resp.status_code == 200:
                    self.loaded.emit(resp.content, self.label)
            else:
                # Local
                with open(self.url, "rb") as f:
                    self.loaded.emit(f.read(), self.label)
        except Exception:
            pass

class SponsorDialog(QDialog):
    def __init__(self, parent=None, links: List[dict] = None, message: str = ""):
        super().__init__(parent)
        self.setWindowTitle("赞助支持")
        self.resize(500, 600)
        self.links = links or []
        self.message = message
        self._threads = []

        layout = QVBoxLayout(self)

        # Title
        title = QLabel("感谢您的支持！")
        title.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        # Message
        if not self.message:
            self.message = (
                "<p style='font-size:14px'>如果您觉得本软件对您有帮助，欢迎赞助支持开发者。</p>"
                "<p style='font-size:14px'><b>赞助后请联系MZDYHR</b></p>"
                "<hr>"
                "<p>联系方式：<br>"
                "QQ：3500394466<br>"
                "邮箱：admin@example.com</p>"
            )
        
        msg_box = QTextBrowser()
        msg_box.setHtml(self.message)
        msg_box.setOpenExternalLinks(True)
        msg_box.setFrameShape(QFrame.NoFrame)
        msg_box.setStyleSheet("background-color: transparent;")
        layout.addWidget(msg_box)

        # Links Area (Scrollable if many)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        container = QWidget()
        vbox = QVBoxLayout(container)

        for link in self.links:
            name = link.get("name", "赞助链接")
            url = link.get("url", "")
            image = link.get("image", "")

            # Frame for each item
            item_frame = QFrame()
            item_frame.setFrameShape(QFrame.StyledPanel)
            item_frame.setStyleSheet("QFrame { border: 1px solid #ddd; border-radius: 5px; background: white; margin-bottom: 5px; }")
            
            h_layout = QHBoxLayout(item_frame)
            h_layout.setContentsMargins(10, 10, 10, 10)

            # Left: Info
            info_layout = QVBoxLayout()
            lbl_name = QLabel(name)
            font_name = QFont()
            font_name.setPointSize(12)
            font_name.setBold(True)
            lbl_name.setFont(font_name)
            lbl_name.setStyleSheet("border: none;")
            info_layout.addWidget(lbl_name)
            
            if url:
                btn = QPushButton("点击跳转")
                btn.setStyleSheet("QPushButton { background-color: #0d6efd; color: white; border: none; padding: 5px; border-radius: 3px; } QPushButton:hover { background-color: #0b5ed7; }")
                # Use default arg to capture loop variable
                btn.clicked.connect(lambda checked=False, u=url: QDesktopServices.openUrl(QUrl(u)))
                info_layout.addWidget(btn)
            
            h_layout.addLayout(info_layout)
            h_layout.addStretch()

            # Right: Image (QR Code)
            if image:
                img_lbl = QLabel()
                img_lbl.setFixedSize(100, 100)
                img_lbl.setAlignment(Qt.AlignCenter)
                img_lbl.setStyleSheet("border: 1px solid #eee;")
                img_lbl.setText("加载中...")
                h_layout.addWidget(img_lbl)
                
                # Load image
                loader = ImageLoader(image, img_lbl)
                loader.loaded.connect(self._on_image_loaded)
                self._threads.append(loader) # Keep reference
                loader.start()
            
            vbox.addWidget(item_frame)

        vbox.addStretch()
        container.setLayout(vbox)
        scroll.setWidget(container)
        layout.addWidget(scroll)

        # Close button
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _on_image_loaded(self, data: bytes, label: QLabel):
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        if not pixmap.isNull():
            scaled = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(scaled)
        else:
            label.setText("加载失败")
