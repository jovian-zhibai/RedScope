from celery import Celery
from backend.config import get_settings

settings = get_settings()

celery_app = Celery(
    "redscope",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_track_started=True,
    worker_max_tasks_per_child=100,
    task_soft_time_limit=3600,
    task_time_limit=7200,
)

celery_app.autodiscover_tasks(["backend.tasks"])
