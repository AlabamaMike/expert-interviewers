"""
Call Guide management endpoints
"""

from fastapi import APIRouter, HTTPException, status
from typing import List
from datetime import datetime

from ...models.call_guide import CallGuide

router = APIRouter()

# In-memory storage for demo (replace with database in production)
call_guides_db = {}


@router.post("/", response_model=CallGuide, status_code=status.HTTP_201_CREATED)
async def create_call_guide(call_guide: CallGuide) -> CallGuide:
    """Create a new call guide"""
    call_guides_db[call_guide.guide_id] = call_guide
    return call_guide


@router.get("/{guide_id}", response_model=CallGuide)
async def get_call_guide(guide_id: str) -> CallGuide:
    """Get a call guide by ID"""
    if guide_id not in call_guides_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call guide {guide_id} not found"
        )
    return call_guides_db[guide_id]


@router.get("/", response_model=List[CallGuide])
async def list_call_guides() -> List[CallGuide]:
    """List all call guides"""
    return list(call_guides_db.values())


@router.put("/{guide_id}", response_model=CallGuide)
async def update_call_guide(guide_id: str, call_guide: CallGuide) -> CallGuide:
    """Update a call guide"""
    if guide_id not in call_guides_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call guide {guide_id} not found"
        )

    call_guide.updated_at = datetime.utcnow()
    call_guides_db[guide_id] = call_guide
    return call_guide


@router.delete("/{guide_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_call_guide(guide_id: str):
    """Delete a call guide"""
    if guide_id not in call_guides_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call guide {guide_id} not found"
        )
    del call_guides_db[guide_id]
