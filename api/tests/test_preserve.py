from pathlib import Path

from app.domain.preserve import (
    materialize_writes,
    merge_keeping_js_exports,
    merge_keeping_symbols,
    missing_from_rewrites,
    removed_js_exports,
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


def test_materialize_keeps_verify_ui_scaffold(tmp_path: Path):
    path = tmp_path / "frontend" / "scripts" / "verify_ui.js"
    path.parent.mkdir(parents=True)
    original = (
        "const assert = require('assert');\n"
        "const fs = require('fs');\n"
        "const path = require('path');\n"
        "const pkg = path.join(__dirname, '..', 'package.json');\n"
        "assert.ok(fs.existsSync(pkg));\n"
        "process.exit(0);\n"
    )
    path.write_text(original, encoding="utf-8")
    writes = materialize_writes(
        tmp_path,
        [
            (
                "frontend/scripts/verify_ui.js",
                "const vite = require('vite');\nprocess.exit(0);\n",
            ),
            ("frontend/src/Hud.js", "export function Hud() { return null; }\n"),
        ],
        [],
    )
    by_path = dict(writes)
    assert by_path["frontend/scripts/verify_ui.js"] == original
    assert "Hud" in by_path["frontend/src/Hud.js"]


def test_merge_keeping_js_exports_restores_hud_helpers():
    previous = (
        "export function formatLevel(n) { return `Current Level: ${n}`; }\n"
        "export function formatProgress(a, b) { return `Progress: ${a} / ${b}`; }\n"
        "export function renderEndlessHud(el, opts) { el.textContent = 'x'; }\n"
    )
    proposed = (
        "export function formatLevel(n) { return `Current Level: ${n}`; }\n"
        "export function maxHintsLabel(n) { return `Max hints: ${n}`; }\n"
    )
    assert removed_js_exports(previous, proposed) == ["formatProgress", "renderEndlessHud"]
    merged = merge_keeping_js_exports(previous, proposed)
    assert "export function formatProgress" in merged
    assert "export function renderEndlessHud" in merged
    assert "maxHintsLabel" in merged


def test_materialize_keeps_js_exports_on_clobber(tmp_path: Path):
    path = tmp_path / "frontend" / "src" / "hud.mjs"
    path.parent.mkdir(parents=True)
    path.write_text(
        "export function formatProgress(a, b) { return `${a}/${b}`; }\n"
        "export function renderEndlessHud(el) { return el; }\n",
        encoding="utf-8",
    )
    writes = materialize_writes(
        tmp_path,
        [("frontend/src/hud.mjs", "export function formatLevel(n) { return String(n); }\n")],
        [],
    )
    content = dict(writes)["frontend/src/hud.mjs"]
    assert "formatProgress" in content
    assert "renderEndlessHud" in content
    assert "formatLevel" in content
