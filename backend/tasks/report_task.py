"""Report generation Celery task."""

from datetime import datetime
from backend.tasks.celery_app import celery_app
from backend.database_sync import SyncSession
from backend.core.report_generator import ReportGenerator
from backend.models.operational import Report


@celery_app.task(name="generate_report")
def generate_report_task(report_id: int, project_id: int):
    with SyncSession() as db:
        generator = ReportGenerator(db, project_id)
        output_path = generator.generate_docx()

        report = db.get(Report, report_id)
        if report:
            report.file_path = output_path
            report.generated_at = datetime.now()
        db.commit()

    return {"report_id": report_id, "file_path": output_path}
