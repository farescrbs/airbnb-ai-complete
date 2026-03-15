from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Review, CleaningTask, Booking, ReviewStatus, CleaningStatus
from schemas import (
    ReviewCreate, ReviewOut, GenerateReviewRequest,
    CleaningTaskCreate, CleaningTaskOut, CleaningTaskUpdate,
)
from services import review_service

router = APIRouter(prefix="/operations", tags=["Reviews & Operations"])


# ── Reviews ───────────────────────────────────────────────────────────────────

@router.post("/reviews/generate", response_model=ReviewOut, status_code=201)
async def generate_review(payload: GenerateReviewRequest, db: Session = Depends(get_db)):
    """Auto-generate a review draft for a booking."""
    try:
        review = await review_service.generate_and_queue_review(
            payload.booking_id, db, payload.override_rating
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return review


@router.post("/reviews", response_model=ReviewOut, status_code=201)
def create_review(payload: ReviewCreate, db: Session = Depends(get_db)):
    """Manually create/override a review."""
    booking = db.query(Booking).filter(Booking.id == payload.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    existing = db.query(Review).filter(Review.booking_id == payload.booking_id).first()
    if existing:
        for k, v in payload.model_dump().items():
            setattr(existing, k, v)
        db.commit()
        db.refresh(existing)
        return existing

    review = Review(**payload.model_dump())
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


@router.get("/reviews", response_model=List[ReviewOut])
def list_reviews(
    status: Optional[ReviewStatus] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Review)
    if status:
        q = q.filter(Review.status == status)
    return q.all()


@router.post("/reviews/post-pending", summary="Post all pending reviews (admin)")
async def post_pending(db: Session = Depends(get_db)):
    posted = await review_service.post_pending_reviews(db)
    return {"reviews_posted": posted}


# ── Cleaning tasks ────────────────────────────────────────────────────────────

@router.post("/cleaning", response_model=CleaningTaskOut, status_code=201)
def create_cleaning_task(payload: CleaningTaskCreate, db: Session = Depends(get_db)):
    task = CleaningTask(**payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/cleaning", response_model=List[CleaningTaskOut])
def list_cleaning_tasks(
    listing_id: Optional[int] = None,
    status: Optional[CleaningStatus] = None,
    db: Session = Depends(get_db),
):
    q = db.query(CleaningTask)
    if listing_id:
        q = q.filter(CleaningTask.listing_id == listing_id)
    if status:
        q = q.filter(CleaningTask.status == status)
    return q.order_by(CleaningTask.scheduled_date).all()


@router.patch("/cleaning/{task_id}", response_model=CleaningTaskOut)
def update_cleaning_task(
    task_id: int, payload: CleaningTaskUpdate, db: Session = Depends(get_db)
):
    task = db.query(CleaningTask).filter(CleaningTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Cleaning task not found")

    from datetime import datetime
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(task, k, v)
    if payload.status == CleaningStatus.COMPLETED:
        task.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return task


@router.delete("/cleaning/{task_id}", status_code=204)
def delete_cleaning_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(CleaningTask).filter(CleaningTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Cleaning task not found")
    db.delete(task)
    db.commit()


# ── Smart lock ────────────────────────────────────────────────────────────────

@router.post("/smart-lock/{booking_id}/provision", summary="Provision smart lock access code")
async def provision_lock(booking_id: int, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    code = await review_service.provision_smart_lock(booking, db)
    if code is None:
        raise HTTPException(
            status_code=400,
            detail="Smart lock not configured for this listing. Set smart_lock_id on the listing.",
        )
    return {"booking_id": booking_id, "access_code": code}
