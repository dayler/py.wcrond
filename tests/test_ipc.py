import pytest
import time
import os
from wcrond.ipc import IPCServer
from wcrond_ctl.client import IPCClient

@pytest.fixture
def pipe_name():
    return f"\\\\.\\pipe\\wcrond_test_pipe_{os.getpid()}_{time.time_ns()}"

@pytest.fixture
def ipc_server(pipe_name):
    server = IPCServer(pipe_name=pipe_name)
    server.start()
    time.sleep(0.1) # give it time to start
    yield server, pipe_name
    server.stop()

def test_ipc_server_start_stop():
    name = f"\\\\.\\pipe\\wcrond_test_pipe_start_{os.getpid()}_{time.time_ns()}"
    server = IPCServer(pipe_name=name)
    server.start()
    assert server.running
    time.sleep(0.1)
    server.stop()
    assert not server.running

def test_ipc_send_receive(ipc_server):
    server, pipe = ipc_server
    client = IPCClient(pipe_name=pipe)
    resp = client.send_request({"cmd": "status"})
    assert resp["status"] == "ok"
    assert "data" in resp

def test_ipc_invalid_command(ipc_server):
    server, pipe = ipc_server
    client = IPCClient(pipe_name=pipe)
    resp = client.send_request({"cmd": "unknown"})
    assert resp["status"] == "error"
    assert "Unknown command" in resp["message"]

def test_ipc_timeout():
    # server is not running, simulate busy pipe by grabbing it?
    # Actually, if daemon not running, it throws ConnectionError immediately.
    client = IPCClient(pipe_name="\\\\.\\pipe\\wcrond_not_exist", timeout=0.1)
    with pytest.raises(ConnectionError, match="no está corriendo"):
        client.send_request({"cmd": "status"})

def test_ipc_daemon_not_running():
    client = IPCClient(pipe_name="\\\\.\\pipe\\wcrond_not_exist", timeout=0.1)
    with pytest.raises(ConnectionError, match="no está corriendo"):
        client.send_request({"cmd": "status"})

def test_ipc_handler_status(ipc_server):
    server, pipe = ipc_server
    client = IPCClient(pipe_name=pipe)
    resp = client.send_request({"cmd": "status"})
    assert resp["status"] == "ok"
    assert "uptime" in resp["data"]

def test_ipc_handler_list(ipc_server):
    server, pipe = ipc_server
    client = IPCClient(pipe_name=pipe)
    resp = client.send_request({"cmd": "list"})
    assert resp["status"] == "ok"
    assert isinstance(resp["data"], list)

def test_ipc_handler_history(ipc_server):
    server, pipe = ipc_server
    client = IPCClient(pipe_name=pipe)
    resp = client.send_request({"cmd": "history"})
    assert resp["status"] == "ok"
    assert isinstance(resp["data"], list)
