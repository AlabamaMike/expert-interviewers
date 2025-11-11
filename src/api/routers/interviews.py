"""
Interview management endpoints
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from typing import List, Optional
from pydantic import BaseModel

from ...models.interview import Interview, InterviewStatus
from ...models.call_guide import CallGuide

router = APIRouter()

# In-memory storage for demo
interviews_db = {}


class ScheduleInterviewRequest(BaseModel):
    """Request to schedule an interview"""
    call_guide_id: str
    respondent_phone: str
    respondent_name: Optional[str] = None
    respondent_email: Optional[str] = None
    scheduled_at: Optional[str] = None


@router.post("/schedule", response_model=Interview, status_code=status.HTTP_201_CREATED)
async def schedule_interview(request: ScheduleInterviewRequest) -> Interview:
    """Schedule a new interview"""
    interview = Interview(
        call_guide_id=request.call_guide_id,
        respondent_phone=request.respondent_phone,
        respondent_name=request.respondent_name,
        respondent_email=request.respondent_email,
        status=InterviewStatus.SCHEDULED
    )

    interviews_db[interview.interview_id] = interview
    return interview


@router.post("/{interview_id}/start", response_model=Interview)
async def start_interview(
    interview_id: str,
    background_tasks: BackgroundTasks
) -> Interview:
    """Start an interview"""
    if interview_id not in interviews_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview {interview_id} not found"
        )

    interview = interviews_db[interview_id]

    if interview.status != InterviewStatus.SCHEDULED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Interview is not in scheduled status"
        )

    # Start interview in background
    # background_tasks.add_task(conduct_interview_task, interview)

    interview.status = InterviewStatus.IN_PROGRESS
    return interview


@router.get("/{interview_id}", response_model=Interview)
async def get_interview(interview_id: str) -> Interview:
    """Get interview by ID"""
    if interview_id not in interviews_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview {interview_id} not found"
        )
    return interviews_db[interview_id]


@router.get("/", response_model=List[Interview])
async def list_interviews(
    status: Optional[InterviewStatus] = None,
    limit: int = 50
) -> List[Interview]:
    """List interviews with optional filtering"""
    interviews = list(interviews_db.values())

    if status:
        interviews = [i for i in interviews if i.status == status]

    return interviews[:limit]


@router.get("/{interview_id}/transcript")
async def get_interview_transcript(interview_id: str):
    """Get interview transcript"""
    if interview_id not in interviews_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview {interview_id} not found"
        )

    interview = interviews_db[interview_id]

    return {
        "interview_id": interview_id,
        "responses": [
            {
                "question": r.question_text,
                "answer": r.response_text,
                "sentiment": r.sentiment.value if r.sentiment else None,
                "timestamp": r.answered_at
            }
            for r in interview.responses
        ]
    }


@router.delete("/{interview_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_interview(interview_id: str):
    """Cancel a scheduled interview"""
    if interview_id not in interviews_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview {interview_id} not found"
        )

    interview = interviews_db[interview_id]
    interview.status = InterviewStatus.CANCELLED
