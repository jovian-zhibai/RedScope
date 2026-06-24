"""Red-blue team scoring: attack/defense scoring for HW exercises."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from backend.database import Base


class RedBlueExercise(Base):
    __tablename__ = "redblue_exercises"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(256), nullable=False)
    status = Column(String(20), default="active")  # active / paused / completed
    red_team_name = Column(String(128), default="红队")
    blue_team_name = Column(String(128), default="蓝队")
    scoring_rules = Column(JSONB)
    started_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ScoreEntry(Base):
    __tablename__ = "score_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    exercise_id = Column(Integer, ForeignKey("redblue_exercises.id"), nullable=False)
    team = Column(String(10), nullable=False)  # red / blue
    category = Column(String(64), nullable=False)
    title = Column(String(256), nullable=False)
    points = Column(Integer, nullable=False)
    description = Column(String(2048))
    evidence_path = Column(String(512))
    submitted_by = Column(Integer, ForeignKey("users.id"))
    verified = Column(Boolean, default=False)
    verified_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


DEFAULT_SCORING_RULES = {
    "red": {
        "获取外网权限": 100,
        "获取内网权限": 200,
        "获取服务器root/SYSTEM": 300,
        "获取域控权限": 500,
        "获取核心数据": 300,
        "横向移动成功": 200,
        "绕过安全设备": 150,
        "发现0day漏洞": 500,
        "社工钓鱼成功": 150,
    },
    "blue": {
        "发现攻击行为": 100,
        "封堵攻击IP": 50,
        "应急响应处置": 200,
        "发现后门木马": 200,
        "溯源攻击者": 300,
        "反制攻击者": 500,
        "安全加固有效防御": 100,
        "提交安全报告": 100,
    },
}
