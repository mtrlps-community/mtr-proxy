import socket
import threading
import time
import select
import logging
import json
import os

# 配置日志
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class Ep:
    def __init__(self, name, addr, port):
        self.name = name
        self.addr = addr
        self.port = port
        self.lat = float('inf')

    def ping(self, tout=2.0):
        start = time.time()
        try:
            with socket.create_connection((self.addr, self.port), timeout=tout):
                self.lat = (time.time() - start) * 1000
        except:
            self.lat = float('inf')
        return self.lat

    def __repr__(self):
        return f"{self.name}({self.addr}:{self.port}, {self.lat:.1f}ms)"

class McProxy:
    def __init__(self, lPort=18800, chkIntv=30):
        self.lPort = lPort
        self.chkIntv = chkIntv
        self.eps = []
        self.bestEp = None
        self.lastChk = 0
        self.running = False
        self.lock = threading.Lock()

    def addEp(self, name, addr, port):
        ep = Ep(name, addr, port)
        with self.lock:
            self.eps.append(ep)
        logger.info(f"添加端点: {ep}")

    def findBest(self):
        with self.lock:
            eps = list(self.eps)
        if not eps: return None
        
        threads = []
        for ep in eps:
            t = threading.Thread(target=ep.ping)
            t.start()
            threads.append(t)
        for t in threads: t.join()

        best = None
        minLat = float('inf')
        with self.lock:
            for ep in self.eps:
                if ep.lat < minLat:
                    minLat = ep.lat
                    best = ep
        return best

    def updateBest(self):
        logger.info("检查延迟...")
        newBest = self.findBest()
        with self.lock:
            if newBest != self.bestEp:
                if newBest and newBest.lat != float('inf'):
                    logger.info(f"切换到: {newBest}")
                    self.bestEp = newBest
                else:
                    logger.warning("没有可用的端点!")
                    self.bestEp = None
            elif self.bestEp:
                logger.info(f"保持: {self.bestEp}")
        self.lastChk = time.time()

    def _chkLoop(self):
        while self.running:
            if time.time() - self.lastChk >= self.chkIntv:
                self.updateBest()
            time.sleep(1)

    def _forward(self, cSock, rSock):
        socks = [cSock, rSock]
        try:
            while self.running:
                r, _, e = select.select(socks, [], socks, 10)
                if e: break
                for s in r:
                    data = s.recv(8192)
                    if not data: return
                    target = rSock if s is cSock else cSock
                    target.sendall(data)
        except:
            pass
        finally:
            cSock.close()
            rSock.close()

    def loadCfg(self, path="config.json"):
        if not os.path.exists(path): return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            self.lPort = cfg.get("listen_port", self.lPort)
            self.chkIntv = cfg.get("check_interval", self.chkIntv)
            
            for e in cfg.get("endpoints", []):
                addr = e.get("ip") or e.get("addr")
                if addr:
                    self.addEp(e["hostname"], addr, e["port"])
            
            for d in cfg.get("dns_endpoints", []):
                for p in d["ports"]:
                    self.addEp(d["hostname"], d["domain"], p)
            logger.info(f"配置文件加载成功: {path}")
        except Exception as e:
            logger.error(f"配置文件加载错误: {e}")

    def start(self):
        if not self.eps:
            logger.error("没有配置任何端点!")
            return
        self.running = True
        self.updateBest()
        threading.Thread(target=self._chkLoop, daemon=True).start()

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind(('127.0.0.1', self.lPort))
            server.listen(128)
            logger.info(f"代理已启动，监听端口: 127.0.0.1:{self.lPort}，检查间隔: {self.chkIntv}秒")
            while self.running:
                cSock, addr = server.accept()
                with self.lock:
                    tEp = self.bestEp
                if not tEp:
                    cSock.close()
                    continue
                try:
                    rSock = socket.create_connection((tEp.addr, tEp.port), timeout=2.0)
                    threading.Thread(target=self._forward, args=(cSock, rSock), daemon=True).start()
                except:
                    cSock.close()
        except Exception as e:
            logger.error(f"运行错误: {e}")
        finally:
            self.running = False
            server.close()

if __name__ == "__main__":
    p = McProxy()
    p.loadCfg()
    p.start()
