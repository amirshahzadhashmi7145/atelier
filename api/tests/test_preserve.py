from pathlib import Path

from app.domain.preserve import (
    materialize_writes,
    merge_keeping_symbols,
    missing_from_rewrites,
    removed_symbols,
)


def test_removed_symbols_detects_dropped_helper():
    previous = "app = 1\ndef reset_store():\n    pass\ndef create_connection():\n    pass\n"
    proposed = "app = 1\ndef create_connection():\n    pass\ndef list_rows():\n    pass\n"
    assert removed_symbols(previous, proposed) == ["reset_store"]


def test_merge_keeping_symbols_restores_reset_store():
    previous = "def reset_store():\n    pass\ndef create_connection():\n    pass\n"
    proposed = "def create_connection():\n    pass\ndef list_rows():\n    pass\n"
    merged = merge_keeping_symbols(previous, proposed)
    assert "def reset_store():" in merged
    assert "def list_rows():" in merged


def test_materialize_full_write_does_not_clobber(tmp_path: Path):
    path = tmp_path / "server" / "app.py"
    path.parent.mkdir()
    path.write_text(
        "def reset_store():\n    return None\n\ndef create_connection():\n    return 1\n",
        encoding="utf-8",
    )
    writes = materialize_writes(
        tmp_path,
        [("server/app.py", "def list_rows():\n    return []\n")],
        [],
    )
    content = dict(writes)["server/app.py"]
    assert "def reset_store():" in content
    assert "def create_connection():" in content
    assert "def list_rows():" in content
    assert missing_from_rewrites(tmp_path, writes) == []


def test_materialize_edit_is_surgical(tmp_path: Path):
    path = tmp_path / "server" / "app.py"
    path.parent.mkdir()
    path.write_text(
        "def reset_store():\n    return None\n\ndef create_connection():\n    return 1\n",
        encoding="utf-8",
    )
    writes = materialize_writes(
        tmp_path,
        [],
        [
            (
                "server/app.py",
                "def create_connection():\n    return 1\n",
                "def create_connection():\n    return 1\n\ndef list_rows():\n    return []\n",
            )
        ],
    )
    content = dict(writes)["server/app.py"]
    assert content.index("def reset_store():") < content.index("def list_rows():")


def test_missing_from_rewrites_flags_clobber(tmp_path: Path):
    path = tmp_path / "backend" / "main.py"
    path.parent.mkdir()
    path.write_text("def reset_store():\n    pass\ndef create_connection():\n    pass\n", encoding="utf-8")
    reasons = missing_from_rewrites(
        tmp_path,
        [("backend/main.py", "def list_rows():\n    pass\n")],
    )
    assert reasons
    assert "reset_store" in reasons[0]
    assert "create_connection" in reasons[0]
