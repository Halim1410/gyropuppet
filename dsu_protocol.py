import socket
import struct
import binascii
import threading
import time

from config_manager import config
from motion_engine import MotionEngine

SERVER_ID = 123456

def _pkt(payload):
    h = struct.pack("<4sHH", b"DSUS", 1001, len(payload))
    pre = h + struct.pack("<II", 0, SERVER_ID) + payload
    crc = binascii.crc32(pre) & 0xFFFFFFFF
    return h + struct.pack("<II", crc, SERVER_ID) + payload

class DSUServer:
    def __init__(self, motion_engine: MotionEngine):
        self.sock = None
        self.clients = {}
        self.count = 0
        self.running = False
        self.start_t = time.perf_counter()
        self.motion_engine = motion_engine
        self.bound = False
        self.bind_lock = threading.Lock()

    def start(self):
        self.running = True
        try:
            with self.bind_lock:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.sock.setblocking(False)
                self.sock.bind((config["server_ip"], config["server_port"]))
                self.bound = True
            threading.Thread(target=self._listen, daemon=True).start()
            threading.Thread(target=self._motion, daemon=True).start()
            return True
        except Exception:
            self.bound = False
            return False

    def stop(self):
        self.running = False
        with self.bind_lock:
            if self.sock:
                try:
                    self.sock.close()
                except Exception:
                    pass
                self.sock = None
            self.bound = False

    def update_bind_address(self, ip, port):
        if not self.sock:
            return False
        with self.bind_lock:
            try:
                current = self.sock.getsockname()
                if current[0] == ip and current[1] == port:
                    return True
                self.sock.close()
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.sock.setblocking(False)
                self.sock.bind((ip, port))
                self.bound = True
                return True
            except Exception:
                self.bound = False
                return False

    def is_bound(self):
        return bool(self.bound and self.sock is not None)

    def _listen(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                if data[:4] == b"DSUC":
                    self.clients[addr] = time.time()
                    m = struct.unpack("<I", data[16:20])[0]
                    if m == 0x100000:
                        self.sock.sendto(_pkt(struct.pack("<IH", 0x100000, 1001)), addr)
                    elif m == 0x100001:
                        self.sock.sendto(_pkt(struct.pack("<IBBBB6sBB", 0x100001,
                            0, 2, 2, 2, b"\x00"*6, 5, 1)), addr)
            except Exception: 
                pass
            time.sleep(0.01)

    def _motion(self):
        while self.running:
            t0 = time.perf_counter()
            if self.clients:
                ax, ay, az, gp, gy, grl = self.motion_engine.get_motion_state()
                self.count += 1
                ts = int((time.perf_counter() - self.start_t) * 1_000_000)
                p1 = struct.pack("<BBBB6sBBI B B B B B B B B",
                    0,2,2,2,b"\x00"*6,5,1,self.count,0,0,0,0,128,128,128,128)
                payload = struct.pack("<I",0x100002)+p1+bytes(24)+struct.pack("<Q f f f f f f",ts,ax,ay,az,gp,gy,grl)
                pkt = _pkt(payload)
                now = time.time()
                for addr in list(self.clients):
                    if now - self.clients[addr] > 5: 
                        del self.clients[addr]
                        continue
                    try: 
                        self.sock.sendto(pkt, addr)
                    except Exception: 
                        pass
            time.sleep(max(0.001, 0.005 - (time.perf_counter() - t0)))
