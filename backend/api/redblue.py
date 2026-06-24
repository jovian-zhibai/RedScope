"""Red-blue team scoring API."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.core.rbac import require_project
from backend.models.redblue import RedBlueExercise, ScoreEntry, DEFAULT_SCORING_RULES

router = APIRouter()


class ExerciseCreate(BaseModel):
    name: str
    red_team_name: str = "红队"
    blue_team_name: str = "蓝队"


class ScoreSubmit(BaseModel):
    team: str  # red / blue
    category: str
    title: str
    points: int
    description: str | None = None


@router.get("")
async def list_exercises(project_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RedBlueExercise).where(RedBlueExercise.project_id == project_id)
    )
    exercises = result.scalars().all()
    return {"items": [
        {"id": e.id, "name": e.name, "status": e.status,
         "red_team_name": e.red_team_name, "blue_team_name": e.blue_team_name,
         "created_at": e.created_at.isoformat() if e.created_at else None}
        for e in exercises
    ]}


@router.post("")
async def create_exercise(project_id: int, req: ExerciseCreate, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from datetime import datetime
    exercise = RedBlueExercise(
        project_id=project_id,
        name=req.name,
        red_team_name=req.red_team_name,
        blue_team_name=req.blue_team_name,
        scoring_rules=DEFAULT_SCORING_RULES,
        started_at=datetime.now(),
    )
    db.add(exercise)
    await db.flush()
    return {"id": exercise.id, "name": exercise.name, "scoring_rules": DEFAULT_SCORING_RULES}


@router.get("/{exercise_id}/scoreboard")
async def get_scoreboard(project_id: int, exercise_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    exercise = await db.get(RedBlueExercise, exercise_id)
    if not exercise or exercise.project_id != project_id:
        raise HTTPException(404, "演练不存在")

    red_total = await db.scalar(
        select(func.coalesce(func.sum(ScoreEntry.points), 0))
        .where(ScoreEntry.exercise_id == exercise_id, ScoreEntry.team == "red")
    )
    blue_total = await db.scalar(
        select(func.coalesce(func.sum(ScoreEntry.points), 0))
        .where(ScoreEntry.exercise_id == exercise_id, ScoreEntry.team == "blue")
    )

    red_entries = await db.execute(
        select(ScoreEntry).where(ScoreEntry.exercise_id == exercise_id, ScoreEntry.team == "red")
        .order_by(ScoreEntry.created_at.desc())
    )
    blue_entries = await db.execute(
        select(ScoreEntry).where(ScoreEntry.exercise_id == exercise_id, ScoreEntry.team == "blue")
        .order_by(ScoreEntry.created_at.desc())
    )

    def _format_entries(entries):
        return [
            {"id": e.id, "category": e.category, "title": e.title,
             "points": e.points, "description": e.description,
             "verified": bool(e.verified),
             "created_at": e.created_at.isoformat() if e.created_at else None}
            for e in entries.scalars().all()
        ]

    return {
        "exercise": {"id": exercise.id, "name": exercise.name, "status": exercise.status},
        "red_team": {"name": exercise.red_team_name, "total_score": red_total, "entries": _format_entries(red_entries)},
        "blue_team": {"name": exercise.blue_team_name, "total_score": blue_total, "entries": _format_entries(blue_entries)},
    }


@router.post("/{exercise_id}/score")
async def submit_score(project_id: int, exercise_id: int, req: ScoreSubmit, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    exercise = await db.get(RedBlueExercise, exercise_id)
    if not exercise or exercise.project_id != project_id:
        raise HTTPException(404, "演练不存在")
    if exercise.status != "active":
        raise HTTPException(400, "演练已结束")

    entry = ScoreEntry(
        exercise_id=exercise_id,
        team=req.team,
        category=req.category,
        title=req.title,
        points=req.points,
        description=req.description,
    )
    db.add(entry)
    await db.flush()
    return {"id": entry.id, "points": entry.points}


@router.post("/{exercise_id}/end")
async def end_exercise(project_id: int, exercise_id: int, _=Depends(require_project), db: AsyncSession = Depends(get_db)):
    from datetime import datetime
    exercise = await db.get(RedBlueExercise, exercise_id)
    if not exercise or exercise.project_id != project_id:
        raise HTTPException(404, "演练不存在")

    exercise.status = "completed"
    exercise.ended_at = datetime.now()
    await db.flush()
    return {"status": "completed"}


@router.get("/scoring-rules")
async def get_default_scoring_rules():
    return DEFAULT_SCORING_RULES
