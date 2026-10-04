"""Tests kuro_system - logique pure, psutil moque, zero reseau."""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kuro_dashboard import system as kuro_system  # noqa: E402


class _FakeMem:
    def _asdict(self):
        return {"total": 8, "available": 4, "used": 4, "percent": 50.0}


class _FakeSwap:
    def _asdict(self):
        return {"total": 2, "used": 1, "percent": 50.0}


class _FakePsutil:
    def cpu_count(self, logical=True):
        return 8

    def cpu_percent(self, interval=None, percpu=False):
        return [10.0, 20.0] if percpu else 15.0

    def virtual_memory(self):
        return _FakeMem()

    def swap_memory(self):
        return _FakeSwap()

    def disk_partitions(self, all=False):
        return [SimpleNamespace(mountpoint="/", fstype="ext4")]

    def disk_usage(self, _mount):
        return SimpleNamespace(_asdict=lambda: {"total": 100, "used": 40, "percent": 40.0})

    def disk_io_counters(self):
        return SimpleNamespace(_asdict=lambda: {"read_bytes": 1})

    def net_io_counters(self):
        return SimpleNamespace(_asdict=lambda: {"bytes_sent": 5})

    def net_if_addrs(self):
        return {}

    def sensors_temperatures(self):
        return {}

    def sensors_fans(self):
        return {}

    def process_iter(self, _attrs):
        p1 = SimpleNamespace(info={"pid": 1, "name": "a", "cpu_percent": 9.0,
                                   "memory_percent": 1.0, "status": "running"})
        p2 = SimpleNamespace(info={"pid": 2, "name": "b", "cpu_percent": 1.0,
                                   "memory_percent": 5.0, "status": "sleeping"})
        return [p2, p1]


def test_payload_keys_present(monkeypatch):
    monkeypatch.setattr(kuro_system, "_psutil", lambda: _FakePsutil())
    monkeypatch.setattr(kuro_system, "_gpu", lambda: [])
    monkeypatch.setattr(kuro_system, "_docker",
                        lambda: {"available": False, "count": 0, "containers": []})
    payload = kuro_system.collect_system_snapshot(top_n=5)
    for key in ("generated_at", "host", "cpu", "memory", "disk",
                "network", "sensors", "gpu", "docker", "processes"):
        assert key in payload
    assert payload["psutil_available"] is True
    assert payload["cpu"]["percent"] == 15.0
    assert [p["pid"] for p in payload["processes"]] == [1, 2]


def test_fallback_without_psutil(monkeypatch):
    monkeypatch.setattr(kuro_system, "_psutil", lambda: None)
    monkeypatch.setattr(kuro_system, "_gpu", lambda: [])
    monkeypatch.setattr(kuro_system, "_docker",
                        lambda: {"available": False, "count": 0, "containers": []})
    payload = kuro_system.collect_system_snapshot()
    assert payload["psutil_available"] is False
    assert payload["cpu"]["percent"] is None
    assert payload["processes"] == []
    assert payload["disk"]["partitions"], "fallback disque attendu"


def test_gpu_docker_failures_safe(monkeypatch):
    import subprocess

    def _boom(*_a, **_k):
        raise FileNotFoundError("nope")

    monkeypatch.setattr(subprocess, "run", _boom)
    assert kuro_system._gpu() == []
    docker = kuro_system._docker()
    assert docker == {"available": False, "count": 0, "containers": []}


def test_to_float_edge():
    assert kuro_system._to_float("12.5") == 12.5
    assert kuro_system._to_float("n/a") is None
    assert kuro_system._to_float("") is None


def test_disk_skips_squashfs_snap(monkeypatch):
    from types import SimpleNamespace

    class _FakeSnapPsutil:
        def disk_partitions(self, all=False):
            return [SimpleNamespace(mountpoint="/", fstype="ext4"),
                    SimpleNamespace(mountpoint="/snap/core22/1", fstype="squashfs")]

        def disk_usage(self, _mount):
            return SimpleNamespace(
                _asdict=lambda: {"total": 100, "used": 40, "percent": 40.0})

        def disk_io_counters(self):
            raise RuntimeError("pas de io ici")

    monkeypatch.setattr(kuro_system, "_psutil", lambda: _FakeSnapPsutil())
    payload = kuro_system.collect_system_snapshot()
    mounts = [p["mount"] for p in payload["disk"]["partitions"]]
    assert mounts == ["/"]


def test_render_contains_header(monkeypatch):
    monkeypatch.setattr(kuro_system, "_psutil", lambda: None)
    monkeypatch.setattr(kuro_system, "_gpu", lambda: [])
    monkeypatch.setattr(kuro_system, "_docker",
                        lambda: {"available": False, "count": 0, "containers": []})
    text = kuro_system.render(kuro_system.collect_system_snapshot())
    assert "Glances Kuro" in text


def test_proc_detail_none_sans_psutil(monkeypatch):
    monkeypatch.setattr(kuro_system, "_psutil", lambda: None)
    assert kuro_system.proc_detail(1) is None


def test_proc_detail_fake_psutil(monkeypatch):
    class _FakeProc:
        def oneshot(self):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def name(self):
            return "demo"

        def cmdline(self):
            return ["/bin/demo", "--x"]

        def username(self):
            return "u"

        def num_threads(self):
            return 4

        def memory_info(self):
            return SimpleNamespace(rss=2048)

        def status(self):
            return "running"

        def create_time(self):
            return 1700000000.0

        def cpu_times(self):
            return SimpleNamespace(user=2.5, system=0.5)

    class _FakePsutilProc:
        def Process(self, pid):
            assert pid == 4242
            return _FakeProc()

    monkeypatch.setattr(kuro_system, "_psutil", lambda: _FakePsutilProc())
    info = kuro_system.proc_detail(4242)
    assert info["name"] == "demo" and info["threads"] == 4
    assert info["rss"] == 2048 and info["cpu_user"] == 2.5
