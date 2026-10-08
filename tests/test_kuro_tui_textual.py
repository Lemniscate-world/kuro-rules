"""Tests kuro_dashboard.tui_textual — montage Textual via pilote (opt-in)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

pytest.importorskip("textual")

from kuro_dashboard import tui_textual  # noqa: E402


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


@pytest.mark.anyio
async def test_app_mounts_with_sidebar():
    app = tui_textual.KuroApp(interval=10, top=3)
    async with app.run_test() as pilot:
        assert app.query_one("#sidebar")
        assert app.query_one("#main")
        assert app.query_one("#procs")
        await pilot.pause()


@pytest.mark.anyio
async def test_strat_seo_panneaux_independants():
    app = tui_textual.KuroApp(interval=30, top=3)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.query_one("#strategy")
        assert app.query_one("#seo")
        keys = {b.key: b.action for b in app.BINDINGS}
        assert keys.get("6") == "toggle_strat"
        assert keys.get("7") == "toggle_seo"
        app.action_toggle_strat()
        assert app.query_one("#strat-box").has_class("hidden")
        assert not app.query_one("#market-box").has_class("hidden")
        app.action_toggle_strat()
        assert not app.query_one("#strat-box").has_class("hidden")
        app.action_toggle_seo()
        assert app.query_one("#seo-box").has_class("hidden")
        await pilot.pause()


@pytest.mark.anyio
async def test_kuro_lines_effective_counts():
    kuro = {"db_present": True, "projects": 0, "sessions": 0,
            "alerts_open": 0, "memory_nodes": 0, "recent_alerts": [],
            "heartbeat_age_min": 1.0, "repos_fs": 5}
    app = tui_textual.KuroApp(interval=10, top=3)
    async with app.run_test() as pilot:
        lines = app._kuro_lines(kuro)
        assert "SAIN" in lines[0]
        assert "5" in lines[1]
        await pilot.pause()


@pytest.mark.anyio
async def test_detail_panel_lifecycle(monkeypatch):
    from kuro_dashboard import system as kuro_system

    class _P:
        def __init__(self, pid):
            self._pid = pid

        def oneshot(self):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

        def name(self):
            return "demo"

        def cmdline(self):
            return ["demo"]

        def username(self):
            return "u"

        def num_threads(self):
            return 1

        def memory_info(self):
            from types import SimpleNamespace
            return SimpleNamespace(rss=10)

        def status(self):
            return "running"

        def create_time(self):
            return 1700000000.0

        def cpu_times(self):
            from types import SimpleNamespace
            return SimpleNamespace(user=1.0, system=0.0)

    class _Ps:
        def Process(self, pid):  # noqa: N802 - mock psutil (API Capitalisée imposée)
            return _P(pid)

    monkeypatch.setattr(kuro_system, "_psutil", lambda: _Ps())
    app = tui_textual.KuroApp(interval=30, top=5)
    async with app.run_test() as pilot:
        await pilot.pause()
        app._procs = [{"pid": 4242, "name": "demo", "cpu": 1.0, "mem": 1.0}]
        app._detail_pid = 4242
        app._render_detail()
        from textual.widgets import Static
        text = str(app.query_one("#detail", Static).render())
        assert "4242" in text
        assert app._detail_pid == 4242
        await pilot.pause()
