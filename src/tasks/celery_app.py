"""
Celery application configuration
"""

from celery import Celery
from ..config import settings

# Create Celery app
celery_app = Celery(
    "expert_interviewers",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "src.tasks.interview_tasks",
    ]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max for any task
    task_soft_time_limit=3000,  # 50 minutes soft limit
    worker_prefetch_multiplier=1,  # One task at a time per worker
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks
)

# Task routes
celery_app.conf.task_routes = {
    "src.tasks.interview_tasks.conduct_interview_task": {"queue": "interviews"},
    "src.tasks.interview_tasks.extract_insights_task": {"queue": "analytics"},
    "src.tasks.interview_tasks.send_webhook_task": {"queue": "webhooks"},
}
