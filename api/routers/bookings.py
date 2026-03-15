from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from database import get_db
from models import Booking, BookingStatus
from schemas import BookingCreate, BookingOut, BookingUpdate
from services import messaging_service, review_service

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("/", response_model=BookingOut, status_code=201)
async def create_booking(
    payload: BookingCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    booking = Booking(**payload.model_dump())
    db.add(booking)
    db.commit()
    db.refresh(booking)

    # Auto-provision smart lock code
    background_tasks.add_task(review_service.provision_smart_lock, booking, db)

    # Schedule all automated messages
    background_tasks.add_task(messaging_service.schedule_messages_for_booking, booking, db)

    # Auto-schedule cleaning task on checkout day
    background_tasks.add_task(review_service.schedule_cleaning_for_booking, booking, db)

    return booking


@router.get("/", response_model=List[BookingOut])
def list_bookings(
    listing_id: Optional[int] = None,
    status: Optional[BookingStatus] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Booking)
    if listing_id:
        q = q.filter(Booking.listing_id == listing_id)
    if status:
        q = q.filter(Booking.status == status)
    return q.order_by(Booking.check_in).all()


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.patch("/{booking_id}", response_model=BookingOut)
def update_booking(booking_id: int, payload: BookingUpdate, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(booking, k, v)
    db.commit()
    db.refresh(booking)
    return booking


@router.delete("/{booking_id}", status_code=204)
def cancel_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking.status = BookingStatus.CANCELLED
    db.commit()
