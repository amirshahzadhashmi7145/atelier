from app.domain.zone_infer import (
    infer_zone_from_paths,
    infer_zone_from_text,
    normalize_task_zone,
)


RULES = [("backend/**", "backend"), ("frontend/**", "frontend")]


def test_stack_setup_text_is_frontend():
    zone = infer_zone_from_text(
        "Setup Technology Stack",
        "Ensure TypeScript with Vite and no game engine or UI framework.",
        {"backend", "frontend"},
    )
    assert zone == "frontend"


def test_normalize_overrides_wrong_backend_zone():
    assert (
        normalize_task_zone(
            zone="backend",
            title="Setup Technology Stack",
            description="Vite + TypeScript package.json",
            known_zones={"backend", "frontend"},
        )
        == "frontend"
    )


def test_paths_infer_single_owner():
    assert (
        infer_zone_from_paths(
            ["frontend/package.json", "frontend/vite.config.ts"],
            RULES,
        )
        == "frontend"
    )


def test_mixed_paths_do_not_infer():
    assert (
        infer_zone_from_paths(
            ["frontend/package.json", "backend/app.py"],
            RULES,
        )
        is None
    )
