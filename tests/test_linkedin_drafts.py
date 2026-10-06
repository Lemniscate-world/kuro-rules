import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from linkedin_drafts import build_post, lint, split_x_draft


def test_split_hook_body():
    hook, body = split_x_draft("Shipped X.\n138 tests pass.\n#Tag")
    assert hook == "Shipped X."
    assert body == ["138 tests pass."]


def test_split_empty():
    assert split_x_draft("#Seul") == ("", [])


def test_build_shape():
    post = build_post("NeuralDBG", "Shipped X.", ["138 tests pass."], ["ML", "PyTorch"])
    assert post.startswith("Shipped X.")
    assert "#ML" in post and "#PyTorch" in post
    assert "commentaire" in post
    assert len(post) <= 3000


def test_build_default_tag():
    post = build_post("Foo", "Hook.", [], [])
    assert "#Foo" in post


def test_lint_catches_leaks():
    assert lint("normal post. 138 tests.") == []
    assert lint("key token=abc secret") != []
    assert lint("C:\\Users\\x\\file") != []
    assert lint("x" * 3001) != []
