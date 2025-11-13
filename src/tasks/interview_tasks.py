"""
Background tasks for interview processing
"""

from celery import Task
import logging
from typing import Dict, Any
from datetime import datetime

from .celery_app import celery_app
from ..data.connection import get_db_connection
from ..data.database import InterviewModel, CallGuideModel, InsightExtractionModel, WebhookModel
from ..models.call_guide import CallGuide
from ..models.interview import Interview, InterviewStatus
from ..intelligence.llm_provider import create_llm_provider
from ..intelligence.insight_extractor import InsightExtractor
from ..config import settings
import httpx

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task with database session"""

    def __init__(self):
        super().__init__()
        self._db = None

    @property
    def db(self):
        if self._db is None:
            self._db = get_db_connection().get_session()
        return self._db

    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()


@celery_app.task(base=DatabaseTask, bind=True, name="conduct_interview_task")
def conduct_interview_task(self, interview_id: str) -> Dict[str, Any]:
    """
    Conduct an interview in the background

    Args:
        interview_id: ID of the interview to conduct

    Returns:
        Dict with interview results
    """
    logger.info(f"Starting interview task: {interview_id}")

    try:
        # Get interview from database
        interview_model = self.db.query(InterviewModel).filter(
            InterviewModel.id == interview_id
        ).first()

        if not interview_model:
            raise ValueError(f"Interview {interview_id} not found")

        # Get call guide
        call_guide_model = self.db.query(CallGuideModel).filter(
            CallGuideModel.id == interview_model.call_guide_id
        ).first()

        if not call_guide_model:
            raise ValueError(f"Call guide {interview_model.call_guide_id} not found")

        # TODO: Initialize orchestrator and conduct interview
        # This would integrate with Twilio to make actual calls
        # For now, we'll update status

        interview_model.status = InterviewStatusEnum.IN_PROGRESS
        interview_model.started_at = datetime.utcnow()
        self.db.commit()

        logger.info(f"Interview {interview_id} started")

        # Simulate interview completion
        # In production, this would call InterviewOrchestrator

        # Trigger insight extraction after interview
        extract_insights_task.delay(interview_id)

        # Send webhook notification
        send_webhook_task.delay("interview.completed", {
            "interview_id": str(interview_id),
            "status": "completed"
        })

        return {
            "interview_id": str(interview_id),
            "status": "completed",
            "message": "Interview conducted successfully"
        }

    except Exception as e:
        logger.error(f"Error conducting interview {interview_id}: {e}", exc_info=True)

        # Update interview status to failed
        interview_model = self.db.query(InterviewModel).filter(
            InterviewModel.id == interview_id
        ).first()
        if interview_model:
            interview_model.status = InterviewStatusEnum.FAILED
            interview_model.escalation_reason = str(e)
            self.db.commit()

        raise


@celery_app.task(base=DatabaseTask, bind=True, name="extract_insights_task")
def extract_insights_task(self, interview_id: str) -> Dict[str, Any]:
    """
    Extract insights from completed interview

    Args:
        interview_id: ID of the interview

    Returns:
        Dict with extraction results
    """
    logger.info(f"Extracting insights for interview: {interview_id}")

    try:
        # Get interview from database
        interview_model = self.db.query(InterviewModel).filter(
            InterviewModel.id == interview_id
        ).first()

        if not interview_model:
            raise ValueError(f"Interview {interview_id} not found")

        # Get call guide for research objective
        call_guide_model = self.db.query(CallGuideModel).filter(
            CallGuideModel.id == interview_model.call_guide_id
        ).first()

        # Convert to Pydantic model for processing
        # This would convert database model to Pydantic Interview model

        # Initialize LLM and insight extractor
        llm = create_llm_provider(
            provider="claude",
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model
        )
        extractor = InsightExtractor(llm)

        # Extract insights (would be async in production)
        # insights = await extractor.extract_interview_insights(
        #     interview=interview,
        #     research_objective=call_guide_model.research_objective
        # )

        # Store insights in database
        # insight_model = InsightExtractionModel(
        #     interview_id=interview_id,
        #     interview_ids=[str(interview_id)],
        #     executive_summary=insights.executive_summary,
        #     ...
        # )
        # self.db.add(insight_model)
        # self.db.commit()

        logger.info(f"Insights extracted for interview {interview_id}")

        # Send webhook notification
        send_webhook_task.delay("insights.extracted", {
            "interview_id": str(interview_id)
        })

        return {
            "interview_id": str(interview_id),
            "status": "completed",
            "message": "Insights extracted successfully"
        }

    except Exception as e:
        logger.error(f"Error extracting insights for {interview_id}: {e}", exc_info=True)
        raise


@celery_app.task(name="send_webhook_task", max_retries=3, default_retry_delay=60)
def send_webhook_task(event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send webhook notification

    Args:
        event_type: Type of event (e.g., "interview.completed")
        payload: Event payload data

    Returns:
        Dict with delivery results
    """
    logger.info(f"Sending webhook for event: {event_type}")

    try:
        db = get_db_connection().get_session()

        # Get active webhooks for this event type
        webhooks = db.query(WebhookModel).filter(
            WebhookModel.is_active == True,
            WebhookModel.events.contains([event_type])
        ).all()

        results = []

        for webhook in webhooks:
            try:
                # Prepare request
                headers = webhook.headers or {}
                if webhook.secret:
                    headers["X-Webhook-Secret"] = webhook.secret

                # Send webhook
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(
                        webhook.url,
                        json={
                            "event": event_type,
                            "timestamp": datetime.utcnow().isoformat(),
                            "data": payload
                        },
                        headers=headers
                    )

                if response.status_code < 300:
                    webhook.success_count += 1
                    webhook.last_triggered_at = datetime.utcnow()
                    results.append({
                        "webhook_id": str(webhook.id),
                        "status": "success",
                        "status_code": response.status_code
                    })
                    logger.info(f"Webhook {webhook.id} delivered successfully")
                else:
                    webhook.failure_count += 1
                    results.append({
                        "webhook_id": str(webhook.id),
                        "status": "failed",
                        "status_code": response.status_code
                    })
                    logger.warning(f"Webhook {webhook.id} failed with status {response.status_code}")

            except Exception as e:
                webhook.failure_count += 1
                results.append({
                    "webhook_id": str(webhook.id),
                    "status": "error",
                    "error": str(e)
                })
                logger.error(f"Error sending webhook {webhook.id}: {e}")

        db.commit()
        db.close()

        return {
            "event_type": event_type,
            "webhooks_triggered": len(webhooks),
            "results": results
        }

    except Exception as e:
        logger.error(f"Error in webhook task: {e}", exc_info=True)
        raise
