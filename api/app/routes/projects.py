"""HTTP in, planning service out.

These handlers do not decide whether a step is legal. The service does.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.services.execution import ExecutionService
from app.schemas import (
    ClarificationSubmit,
    GateSubmit,
    InterpretationUpdate,
    ProjectCreate,
    ProjectListItem,
    ProjectSnapshot,
    RequirementWrite,
)
from app.services.planning import PlanningService

router = APIRouter(prefix="/api")


def get_service(request: Request):
    session: Session = request.app.state.session_factory()
    try:
        yield PlanningService(session, request.app.state.llm)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.post("/projects", response_model=ProjectSnapshot)
def create_project(body: ProjectCreate, service: PlanningService = Depends(get_service)) -> ProjectSnapshot:
    return service.create_project(
        name=body.name,
        description=body.description,
        tech_preferences=body.tech_preferences,
    )


@router.get("/projects", response_model=list[ProjectListItem])
def list_projects(service: PlanningService = Depends(get_service)) -> list[ProjectListItem]:
    return service.list_projects()


@router.get("/projects/{project_id}", response_model=ProjectSnapshot)
def get_project(project_id: str, service: PlanningService = Depends(get_service)) -> ProjectSnapshot:
    return service.snapshot(project_id)


@router.patch("/projects/{project_id}/interpretation", response_model=ProjectSnapshot)
def update_interpretation(
    project_id: str,
    body: InterpretationUpdate,
    service: PlanningService = Depends(get_service),
) -> ProjectSnapshot:
    return service.update_interpretation(project_id, body.interpretation)


@router.post("/projects/{project_id}/interpret", response_model=ProjectSnapshot)
def interpret(project_id: str, service: PlanningService = Depends(get_service)) -> ProjectSnapshot:
    return service.interpret(project_id)


@router.post("/projects/{project_id}/clarifications", response_model=ProjectSnapshot)
def answer_clarifications(
    project_id: str,
    body: ClarificationSubmit,
    service: PlanningService = Depends(get_service),
) -> ProjectSnapshot:
    return service.answer_clarifications(
        project_id,
        [(item.id, item.answer) for item in body.answers],
        proceed=body.proceed,
    )


@router.post("/projects/{project_id}/requirements", response_model=ProjectSnapshot)
def generate_requirements(project_id: str, service: PlanningService = Depends(get_service)) -> ProjectSnapshot:
    return service.generate_requirements(project_id)


@router.post("/projects/{project_id}/requirements/items", response_model=ProjectSnapshot)
def add_requirement(
    project_id: str,
    body: RequirementWrite,
    service: PlanningService = Depends(get_service),
) -> ProjectSnapshot:
    return service.add_requirement(project_id, body)


@router.patch("/projects/{project_id}/requirements/{requirement_id}", response_model=ProjectSnapshot)
def update_requirement(
    project_id: str,
    requirement_id: str,
    body: RequirementWrite,
    service: PlanningService = Depends(get_service),
) -> ProjectSnapshot:
    return service.update_requirement(project_id, requirement_id, body)


@router.delete("/projects/{project_id}/requirements/{requirement_id}", response_model=ProjectSnapshot)
def delete_requirement(
    project_id: str,
    requirement_id: str,
    service: PlanningService = Depends(get_service),
) -> ProjectSnapshot:
    return service.delete_requirement(project_id, requirement_id)


@router.post("/projects/{project_id}/architecture", response_model=ProjectSnapshot)
def generate_architecture(project_id: str, service: PlanningService = Depends(get_service)) -> ProjectSnapshot:
    return service.generate_architecture(project_id)


@router.post("/projects/{project_id}/tasks", response_model=ProjectSnapshot)
def generate_tasks(project_id: str, service: PlanningService = Depends(get_service)) -> ProjectSnapshot:
    return service.generate_tasks(project_id)


def get_executor(request: Request):
    session: Session = request.app.state.session_factory()
    try:
        yield ExecutionService(session, request.app.state.llm, request.app.state.settings)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@router.post("/projects/{project_id}/tasks/run", response_model=ProjectSnapshot)
def run_next_task(project_id: str, service: ExecutionService = Depends(get_executor)) -> ProjectSnapshot:
    return service.run_next(project_id)


@router.post("/projects/{project_id}/tasks/{task_id}/accept", response_model=ProjectSnapshot)
def accept_task(
    project_id: str,
    task_id: str,
    service: ExecutionService = Depends(get_executor),
) -> ProjectSnapshot:
    return service.accept(project_id, task_id)


@router.post("/projects/{project_id}/gates", response_model=ProjectSnapshot)
def decide_gate(
    project_id: str,
    body: GateSubmit,
    service: PlanningService = Depends(get_service),
) -> ProjectSnapshot:
    return service.decide_gate(project_id, gate=body.gate, decision=body.decision, note=body.note)
