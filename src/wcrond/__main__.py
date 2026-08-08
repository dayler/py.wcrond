import argparse
import sys
import os
import json
import subprocess
import win32pipe, win32file, pywintypes
from pathlib import Path

from wcrond.daemon import WcrondDaemon
from wcrond.config import WcrondConfig
from wcrond.logging_config import setup_logging

def send_ipc_command(config, cmd, quiet=False, **kwargs):
    pipe_name = config.ipc_pipe_name
    req = {"cmd": cmd}
    req.update(kwargs)
    
    import time
    start_time = time.time()
    handle = None
    
    while time.time() - start_time < 3.0:
        try:
            handle = win32file.CreateFile(
                pipe_name,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0, None, win32file.OPEN_EXISTING, 0, None
            )
            break
        except pywintypes.error as e:
            if e.winerror in (2, 231):
                time.sleep(0.1)
                continue
            if not quiet:
                print(f"Error communicating with daemon: {e}")
            return None
        except Exception as e:
            if not quiet:
                print(f"Error communicating with daemon: {e}")
            return None
    
    if not handle:
        if not quiet:
            print("Daemon is not running.")
        return None
        
    try:
        data = json.dumps(req).encode('utf-8')
        win32file.WriteFile(handle, data)
        
        hr, response_data = win32file.ReadFile(handle, 65536)
        win32file.CloseHandle(handle)
        
        response = json.loads(response_data.decode('utf-8'))
        return response
    except Exception as e:
        if not quiet:
            print(f"Error communicating with daemon: {e}")
        return None

import shutil

def init_wcrond(config):
    base = config.base_dir
    base.mkdir(parents=True, exist_ok=True)
    
    # Intentar buscar la carpeta examples en el directorio actual (ej. si se corre desde código fuente)
    # o desde el directorio del paquete si se decide empaquetar allí
    project_root = Path(sys.prefix)
    cwd = Path.cwd()
    
    examples_dirs = [
        cwd / "examples",
        Path(__file__).parent.parent.parent / "examples"
    ]
    
    examples_dir = None
    for d in examples_dirs:
        if d.exists() and d.is_dir():
            examples_dir = d
            break
            
    wcrond_conf = base / "wcrond.toml"
    if not wcrond_conf.exists():
        if examples_dir and (examples_dir / "wcrond.init.toml").exists():
            shutil.copy(examples_dir / "wcrond.init.toml", wcrond_conf)
        else:
            wcrond_conf.touch(exist_ok=True)
            
    wcrontab_conf = base / "wcrontab.toml"
    if not wcrontab_conf.exists():
        if examples_dir and (examples_dir / "wcrontab.init.toml").exists():
            shutil.copy(examples_dir / "wcrontab.init.toml", wcrontab_conf)
        else:
            wcrontab_conf.touch(exist_ok=True)
            
    (base / "jobs.d").mkdir(exist_ok=True)
    
    log_dir = config.get_absolute_path(config.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    print(f"Initialized wcrond at {base}")

def main():
    parser = argparse.ArgumentParser(prog="wcrond")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_p = subparsers.add_parser("start")
    start_p.add_argument("--foreground", action="store_true")
    start_p.add_argument("--config")

    status_p = subparsers.add_parser("status")
    status_p.add_argument("--config")

    stop_p = subparsers.add_parser("stop")
    stop_p.add_argument("--config")
    
    init_p = subparsers.add_parser("init")
    init_p.add_argument("--config")

    args = parser.parse_args()

    config = WcrondConfig.load(args.config)

    if args.command == "init":
        init_wcrond(config)
    elif args.command == "start":
        setup_logging(config)
        if args.foreground:
            daemon = WcrondDaemon(args.config)
            daemon.start()
        else:
            cmd = [sys.executable, "-m", "wcrond", "start", "--foreground"]
            if args.config:
                cmd.extend(["--config", args.config])
            
            # DETACHED_PROCESS = 0x00000008
            # CREATE_NEW_PROCESS_GROUP = 0x00000200
            creationflags = 0x00000008 | 0x00000200
            subprocess.Popen(cmd, creationflags=creationflags)
            print("Started wcrond daemon in background")
    elif args.command == "stop":
        res = send_ipc_command(config, "stop")
        if res and res.get("status") == "ok":
            print("Daemon stopping...")
        else:
            print("Failed to stop daemon.")
    elif args.command == "status":
        res = send_ipc_command(config, "status", quiet=True)
        if res and res.get("status") == "ok":
            uptime = res.get("data", {}).get("uptime", 0)
            print(f"wcrond is running (Uptime: {uptime}s)")
            sys.exit(0)
        else:
            print("wcrond is not running.")
            sys.exit(1)

if __name__ == '__main__':
    main()
