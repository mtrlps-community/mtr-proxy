import sys
import threading
from pathlib import Path

from PySide6.QtWidgets import QApplication, QStyle

from mtrproxy.config import ConfigManager
from mtrproxy.nodes import NodeManager
from mtrproxy.proxy_core import ProxyServer
from mtrproxy.announcement import fetch_announcement, should_show_announcement
from mtrproxy.autostart_win import set_windows_autostart
from mtrproxy.heartbeat import HeartbeatManager
from mtrproxy.update import check_update

from gui.main_window import MainWindow, BackendSignals
from gui.settings_dialog import SettingsDialog
from gui.announcement_dialog import AnnouncementDialog
from gui.tray import TrayIcon


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("MTRProxyGUI")
    
    # Set default icon
    icon = app.style().standardIcon(QStyle.SP_ComputerIcon)
    app.setWindowIcon(icon)

    config_path = Path("config.json")
    cfg = ConfigManager(config_path)
    data = cfg.get_all()

    signals = BackendSignals()

    node_manager = NodeManager(
        remote_api=data.get("remote_nodes_api", ""),
        detect_interval_seconds=data.get("detect_interval_seconds", 60),
        auto_detect_enabled=data.get("auto_detect_enabled", False),
        on_nodes_updated=lambda nodes: signals.nodes_updated.emit(nodes),
        on_best_node_changed=None,
    )

    proxy = ProxyServer(
        listen_host=data.get("listen_host", "127.0.0.1"),
        listen_port=data.get("listen_port", 1080),
        node_manager=node_manager,
        on_status=lambda status: signals.status_updated.emit(status),
    )

    heartbeat = HeartbeatManager(
        api_url=data.get("heartbeat_api", "https://example.com/api/heartbeat"),
        client_id=data.get("client_id", ""),
        version=data.get("version", "1.0.0"),
        interval=60
    )

    def on_toggle_proxy() -> None:
        if proxy._server_sock:
            proxy.stop()
            heartbeat.stop()
            signals.log_message.emit("代理服务已停止")
            tray.update_status(False)
        else:
            proxy.start()
            
            # Get current node info for heartbeat
            node_info = None
            current_node = node_manager.get_current_node()
            if current_node:
                node_info = {
                    "hostname": current_node.hostname,
                    "ip": current_node.ip,
                    "port": current_node.port
                }
            
            heartbeat.start({
                "port": proxy.listen_port,
                "current_node": node_info
            })
            signals.log_message.emit("代理服务启动中...")
            tray.update_status(True)

    def on_detect_all() -> None:
        signals.log_message.emit("开始检测所有节点延迟...")
        threading.Thread(target=lambda: node_manager.detect_all_nodes(auto_switch=not node_manager._manual_selected), daemon=True).start()

    def on_refresh_nodes() -> None:
        signals.log_message.emit("正在刷新远程节点...")
        def _refresh():
            try:
                nodes = node_manager.fetch_nodes_from_remote()
                signals.log_message.emit(f"成功获取 {len(nodes)} 个节点")
            except Exception as e:
                signals.log_message.emit(f"刷新节点失败: {e}")
        threading.Thread(target=_refresh, daemon=True).start()

    def on_select_node(hostname: str) -> None:
        node = node_manager.manual_select_node(hostname)
        if node:
            signals.log_message.emit(f"手动切换到节点: {hostname}")
        else:
            signals.log_message.emit(f"节点 {hostname} 不存在")

    def on_open_settings() -> None:
        dlg = SettingsDialog(cfg.get_all(), win)
        if dlg.exec() == dlg.Accepted:
            new_data = dlg.get_result()
            cfg.update_bulk(new_data)
            cfg.save()
            
            node_manager.remote_api = new_data["remote_nodes_api"]
            node_manager.detect_interval_seconds = new_data["detect_interval_seconds"]
            node_manager.auto_detect_enabled = new_data["auto_detect_enabled"]
            
            if proxy.listen_port != new_data["listen_port"]:
                 proxy.listen_port = new_data["listen_port"]
                 signals.log_message.emit("监听端口配置已更新，请重启代理以生效")
            
            set_windows_autostart("mtrproxy_gui", new_data.get("windows_autostart", False))
            
            win.ad_config = new_data.get("ad", {})
            win._update_ad_label()
            signals.log_message.emit("配置已保存")

    win = MainWindow(
        signals=signals,
        on_toggle_proxy=on_toggle_proxy,
        on_detect_all=on_detect_all,
        on_refresh_nodes=on_refresh_nodes,
        on_select_node=on_select_node,
        on_open_settings=on_open_settings,
        sponsor_links=data.get("sponsor_links", []),
        ad_config=data.get("ad", {}),
    )
    
    # Handle announcement signal
    def show_announcement_dialog(ann_data: dict):
        dlg = AnnouncementDialog(ann_data, win)
        if dlg.exec() == dlg.Accepted and dlg.should_ignore():
            ignored = cfg.get("ignored_announcement_ids", [])
            ignored.append(ann_data.get("id"))
            cfg.set("ignored_announcement_ids", ignored)
            cfg.save()

    signals.show_announcement.connect(show_announcement_dialog)

    win.show()

    tray = TrayIcon(win, on_toggle_proxy)
    tray.show()
    tray.setIcon(icon)

    # Initial tasks
    on_refresh_nodes()
    node_manager.start()

    # Check announcement
    ann_api = data.get("announcement_api", "")
    if ann_api:
        def _check_ann():
            try:
                ann = fetch_announcement(ann_api)
                ignored = cfg.get("ignored_announcement_ids", [])
                if ann and should_show_announcement(ann, ignored):
                    signals.show_announcement.emit(ann)
            except Exception:
                pass
        threading.Thread(target=_check_ann, daemon=True).start()

    # Fetch ad config
    ad_api = data.get("ad_api", "")
    if ad_api:
        def _fetch_ad():
            try:
                import requests
                resp = requests.get(ad_api, timeout=5)
                if resp.status_code == 200:
                    ad_data = resp.json()
                    signals.update_ad.emit(ad_data)
            except Exception:
                pass
        threading.Thread(target=_fetch_ad, daemon=True).start()
    
    # Check update
    update_api = data.get("update_api", "")
    if update_api:
        def _check_update():
            has_update, update_data = check_update(update_api, data.get("version", "1.0.0"))
            if has_update and update_data:
                signals.show_update.emit(update_data)
        threading.Thread(target=_check_update, daemon=True).start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
