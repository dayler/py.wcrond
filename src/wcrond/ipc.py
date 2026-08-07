import win32pipe, win32file, pywintypes
import threading
import json
import logging

logger = logging.getLogger(__name__)

class IPCServer:
    def __init__(self, pipe_name="\\\\.\\pipe\\wcrond"):
        self.pipe_name = pipe_name
        self.running = False
        self.thread = None
        self.handlers = {}
        self._register_default_handlers()

    def _register_default_handlers(self):
        # Default stubs
        self.handlers = {
            "status": lambda req: {"status": "ok", "data": {"uptime": 0, "jobs": 0, "threads": 0, "retry_queue_size": 0}},
            "list": lambda req: {"status": "ok", "data": []},
            "history": lambda req: {"status": "ok", "data": []},
            "retries": lambda req: {"status": "ok", "data": []},
            "run": lambda req: {"status": "ok", "data": "submitted"},
            "kill": lambda req: {"status": "ok", "data": "killed"},
            "cancel-retry": lambda req: {"status": "ok", "data": "cancelled"},
            "disable": lambda req: {"status": "ok", "data": "disabled"},
            "enable": lambda req: {"status": "ok", "data": "enabled"},
            "zombies": lambda req: {"status": "ok", "data": []},
            "reload": lambda req: {"status": "ok", "data": "reloaded"},
            "logs": lambda req: {"status": "ok", "data": []},
            "validate": lambda req: {"status": "ok", "data": "valid"},
            "next": lambda req: {"status": "ok", "data": []},
            "stop": lambda req: {"status": "ok", "data": "stopping"},
        }

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._server_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        # Dummy connection to unblock ConnectNamedPipe
        try:
            handle = win32file.CreateFile(
                self.pipe_name,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0, None, win32file.OPEN_EXISTING, 0, None
            )
            win32file.CloseHandle(handle)
        except Exception:
            pass
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)

    def handle_request(self, request):
        cmd = request.get("cmd")
        if not cmd:
            return {"status": "error", "message": "Missing 'cmd'"}
        if cmd not in self.handlers:
            return {"status": "error", "message": f"Unknown command: {cmd}"}
        try:
            result = self.handlers[cmd](request)
            if not isinstance(result, dict) or "status" not in result:
                return {"status": "error", "message": "Handler returned invalid format"}
            return result
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _server_loop(self):
        while self.running:
            pipe = None
            try:
                pipe = win32pipe.CreateNamedPipe(
                    self.pipe_name,
                    win32pipe.PIPE_ACCESS_DUPLEX,
                    win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
                    win32pipe.PIPE_UNLIMITED_INSTANCES,
                    65536,
                    65536,
                    0,
                    None
                )
                
                import winerror
                try:
                    win32pipe.ConnectNamedPipe(pipe, None)
                except pywintypes.error as e:
                    if e.winerror == winerror.ERROR_PIPE_CONNECTED:
                        pass
                    else:
                        raise
                
                if not self.running:
                    win32file.CloseHandle(pipe)
                    break
                    
                # Handle client in the same thread (fine for fast CLI commands)
                self._handle_client(pipe)
            except Exception as e:
                if self.running:
                    logger.error(f"IPC Error: {e}")
                if pipe:
                    try:
                        win32file.CloseHandle(pipe)
                    except:
                        pass

    def _handle_client(self, pipe):
        try:
            hr, data = win32file.ReadFile(pipe, 65536)
            if hr == 0:
                req_str = data.decode("utf-8").strip()
                if req_str:
                    req = json.loads(req_str)
                    resp = self.handle_request(req)
                    resp_bytes = json.dumps(resp).encode("utf-8")
                    win32file.WriteFile(pipe, resp_bytes)
        except Exception as e:
            logger.error(f"Error handling IPC client: {e}")
        finally:
            try:
                win32pipe.DisconnectNamedPipe(pipe)
                win32file.CloseHandle(pipe)
            except:
                pass
