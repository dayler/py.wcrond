import win32file, pywintypes
import json
import time

class IPCClient:
    def __init__(self, pipe_name="\\\\.\\pipe\\wcrond", timeout=5.0):
        self.pipe_name = pipe_name
        self.timeout = timeout

    def send_request(self, request):
        start_time = time.time()
        handle = None
        while time.time() - start_time < self.timeout:
            try:
                handle = win32file.CreateFile(
                    self.pipe_name,
                    win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                    0,
                    None,
                    win32file.OPEN_EXISTING,
                    0,
                    None
                )
                break
            except pywintypes.error as e:
                # 2 = ERROR_FILE_NOT_FOUND (pipe doesn't exist, daemon not running)
                # 231 = ERROR_PIPE_BUSY
                if e.winerror == 2:
                    raise ConnectionError("Daemon no está corriendo (pipe no encontrado)")
                elif e.winerror == 231:
                    time.sleep(0.1)
                else:
                    raise
        
        if not handle:
            raise TimeoutError("Timeout conectando al daemon")

        try:
            # Send
            req_bytes = json.dumps(request).encode("utf-8")
            win32file.WriteFile(handle, req_bytes)
            
            # Receive
            hr, data = win32file.ReadFile(handle, 65536)
            if hr == 0:
                resp_str = data.decode("utf-8")
                return json.loads(resp_str)
            else:
                raise Exception(f"Read error: {hr}")
        finally:
            win32file.CloseHandle(handle)
