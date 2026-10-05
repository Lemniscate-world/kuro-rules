"""Tests face.py — humeurs derivees de donnees reelles, ASCII strict."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kuro_dashboard import face  # noqa: E402


def _sys(cpu=None, mem=None, disk=None, temp=None):
    return {"cpu": {"percent": cpu},
            "memory": {"percent": mem},
            "disk": {"partitions": [{"percent": disk}] if disk is not None else []},
            "sensors": {"temperatures": [{"current": temp}]} if temp else {}}


def _kuro(age=None, db=True):
    return {"db_present": db, "heartbeat_age_min": age}


def test_critical_cases():
    assert face.mood_for(_sys(), _kuro(99))[0] == "critical"  # daemon mort
    assert face.mood_for(_sys(disk=96), _kuro(1))[0] == "critical"
    assert face.mood_for(_sys(cpu=95), _kuro(1))[0] == "critical"
    assert face.mood_for(_sys(temp=90), _kuro(1))[0] == "critical"


def test_worried_cases():
    assert face.mood_for(_sys(cpu=40), _kuro(5))[0] == "worried"  # stale
    assert face.mood_for(_sys(cpu=80), _kuro(1))[0] == "worried"
    assert face.mood_for(_sys(cpu=40), _kuro(None))[0] == "worried"  # jamais vu


def test_idle_happy_fresh():
    assert face.mood_for(_sys(cpu=3), _kuro(1))[0] == "idle"
    assert face.mood_for(_sys(cpu=40), _kuro(1))[0] == "happy"
    # machine fraiche (pas de DB, pas de psutil) : pas de fausse alerte
    assert face.mood_for(_sys(), {"db_present": False})[0] == "happy"


def test_blink_and_spinner():
    assert face.should_blink(0.1) is True
    assert face.should_blink(2.0) is False
    assert face.should_blink(None) is False
    assert len({face.spinner(t) for t in (0.0, 0.5, 1.0, 1.5)}) == 4


def test_faces_ascii_only():
    for mood in ("happy", "idle", "worried", "critical"):
        for blink in (False, True):
            for line in face.face_frame(mood, blink):
                assert all(ord(c) < 128 for c in line), f"non-ASCII: {line!r}"
    assert face.face_frame("happy", True) != face.face_frame("happy", False)
    assert face.face_frame("nope") == face.face_frame("happy")
