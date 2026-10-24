# test_install_startup_silent.py — fixture reelle du dossier Demarrage (R125).
#
# Regression 24/10 : KuroBot.cmd et OpenVikingPilot.bat ouvraient 2 consoles
# cmd visibles A CHAQUE login, et 2 autres lanceurs etaient casses (MemosPilot
# : stage Temp efface ; horcruxe-lab : ligne cd/python collee). Le fix migre
# les 4 services vers des .lnk -> pythonw.exe + task_launchers/hidden_launch.py.
#
# Ce test reproduit le contenu REEL des 5 entrees du dossier et verifie :
#   1. aucune entree ne peut ouvrir de fenetre (doctor : startup_launchers_health)
#   2. les 4 entrees obligatoires sont bien presentes
#   3. la detection repere encore un .bat console (preuve negative, R116)
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import kuro_doctor as doctor  # noqa: E402
import install_startup_silent as inst  # noqa: E402

# Contenus reels recopies du dossier au moment du fix (24/10/2026).
_FIXTURE = {
    "KuroDaemon.bat": '@echo off\nstart "" "C:\\Python314\\pythonw.exe" '
                      '"C:\\Users\\Utilisateur\\Documents\\kuro\\daemon.py"\n',
    "KuroSupervisor.bat": 'REM verifie le daemon Kuro a chaque login\n'
                          'start "" "C:\\Python314\\pythonw.exe" '
                          '"C:\\Users\\Utilisateur\\Documents\\kuro-rules\\scripts\\kuro_supervisor.py"'
                          " --check --fix\n",
    "KuroBot.lnk": "",
    "OpenVikingPilot.lnk": "",
    "KuroPulse.lnk": "",
    "Ollama.lnk": "",
}


def _populate(tmp_path):
    for name, content in _FIXTURE.items():
        (tmp_path / name).write_text(content, encoding="utf-8")
    return tmp_path


def test_aucune_fenetre_au_login(tmp_path):
    """Les 5 entrees du dossier sont silencieuses (doctor R125 au login)."""
    startup = _populate(tmp_path)
    ok, detail = doctor.startup_launchers_health(startup)
    assert ok is True, detail
    assert "sans console" in detail


def test_entrees_obligatoires_presentes(tmp_path):
    """Les 4 services doivent garder leur point d'entree au login."""
    startup = _populate(tmp_path)
    ok, detail = doctor.startup_launchers_health(startup)
    assert ok is True, detail
    for name in doctor.STARTUP_REQUIRED:
        assert (startup / name).exists(), f"{name} manquant : le service ne demarrera pas"


def test_bat_console_still_detected(tmp_path):
    """Preuve negative : un .bat qui ouvre une fenetre est signale (R116)."""
    startup = _populate(tmp_path)
    (startup / "KuroBot.cmd").write_text(
        '@echo off\nstart /min "KuroBot" cmd /c "python -u scripts\\kuro_bot.py '
        '>> logs\\kuro-bot.log 2>&1"\n', encoding="utf-8")
    ok, detail = doctor.startup_launchers_health(startup)
    assert ok is False
    assert "KuroBot.cmd" in detail


def test_lanceur_cache_present():
    """hidden_launch.py doit exister : c'est la cible des 2 nouveaux .lnk."""
    helper = doctor.KURO_ROOT / "scripts" / "task_launchers" / "hidden_launch.py"
    assert helper.exists()
    assert doctor.STARTUP_REQUIRED == (
        "KuroDaemon.bat", "KuroPulse.lnk", "KuroBot.lnk", "OpenVikingPilot.lnk")


@pytest.mark.parametrize("link,target,args", inst.STARTUP_LINKS)
def test_raccourcis_definis(link, target, args):
    """Chaque service a un .lnk vers pythonw.exe (jamais cmd.exe/python.exe)."""
    assert link.endswith(".lnk")
    assert target.lower().endswith("pythonw.exe")
    assert "hidden_launch.py" in args
    assert "--log" in args
