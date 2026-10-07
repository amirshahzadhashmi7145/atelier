from pathlib import Path

from app.domain.preserve import missing_from_rewrites, removed_symbols


def test_removed_symbols_detects_dropped_helper():
    previous = "app = 1\ndef reset_store():\n    pass\ndef create_connection():\n    pass\n"
    proposed = "app = 1\ndef create_connection():\n    pass\ndef list_rows():\n    pass\n"
    assert removed_symbols(previous, proposed) == ["reset_store"]


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
