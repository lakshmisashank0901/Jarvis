import os
import socket
import threading

from jarvis_mcp.host_client import HostClient


def test_empty_or_missing_socket_falls_back_to_open(tmp_path) -> None:
    client = HostClient(path=str(tmp_path / "missing.sock"))
    out = client.call("files.reveal", path="/tmp")
    assert out["ok"] is True
    assert out["via"] == "macos"


def test_quit_ok_without_target_falls_back(monkeypatch) -> None:
    sock_path = "/tmp/jarvis-test-host.sock"
    ready = threading.Event()

    def serve() -> None:
        try:
            os.unlink(sock_path)
        except OSError:
            pass
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(sock_path)
        srv.listen(1)
        ready.set()
        conn, _ = srv.accept()
        conn.recv(4096)
        conn.sendall(b'{"ok": true, "bundle_id": ""}\n')
        conn.close()
        srv.close()

    threading.Thread(target=serve, daemon=True).start()
    assert ready.wait(1)
    called: list[tuple] = []

    def fake_dispatch(op: str, **fields):
        called.append((op, fields))
        return {"ok": True, "name": fields.get("name")}

    monkeypatch.setattr("jarvis_mcp.host_client.dispatch", fake_dispatch)
    out = HostClient(path=sock_path).call("app.quit", name="Notes")
    assert out["via"] == "macos"
    assert called == [("app.quit", {"name": "Notes"})]
