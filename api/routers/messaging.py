from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from database import get_db
from models import MessageTemplate, MessageLog, MessageStatus
from schemas import (
    MessageTemplateCreate, MessageTemplateOut,
    MessageLogOut, SendMessageRequest,
)
from services import messaging_service

router = APIRouter(prefix="/messaging", tags=["Messaging"])


# ── Templates ─────────────────────────────────────────────────────────────────

@router.post("/templates", response_model=MessageTemplateOut, status_code=201)
def create_template(payload: MessageTemplateCreate, db: Session = Depends(get_db)):
    tmpl = MessageTemplate(**payload.model_dump())
    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    return tmpl


@router.get("/templates", response_model=List[MessageTemplateOut])
def list_templates(db: Session = Depends(get_db)):
    return db.query(MessageTemplate).all()


@router.get("/templates/{template_id}", response_model=MessageTemplateOut)
def get_template(template_id: int, db: Session = Depends(get_db)):
    tmpl = db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tmpl


@router.put("/templates/{template_id}", response_model=MessageTemplateOut)
def update_template(
    template_id: int, payload: MessageTemplateCreate, db: Session = Depends(get_db)
):
    tmpl = db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    for k, v in payload.model_dump().items():
        setattr(tmpl, k, v)
    db.commit()
    db.refresh(tmpl)
    return tmpl


@router.delete("/templates/{template_id}", status_code=204)
def delete_template(template_id: int, db: Session = Depends(get_db)):
    tmpl = db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(tmpl)
    db.commit()


# ── Logs & manual send ────────────────────────────────────────────────────────

@router.get("/logs", response_model=List[MessageLogOut])
def list_message_logs(
    booking_id: Optional[int] = None,
    status: Optional[MessageStatus] = None,
    db: Session = Depends(get_db),
):
    q = db.query(MessageLog)
    if booking_id:
        q = q.filter(MessageLog.booking_id == booking_id)
    if status:
        q = q.filter(MessageLog.status == status)
    return q.order_by(MessageLog.scheduled_at.desc()).all()


@router.post("/send", response_model=MessageLogOut)
async def send_message_now(
    payload: SendMessageRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Immediately render and send a specific template to a booking."""
    from models import Booking
    booking = db.query(Booking).filter(Booking.id == payload.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    tmpl = db.query(MessageTemplate).filter(MessageTemplate.id == payload.template_id).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")

    from datetime import datetime
    from models import MessageLog
    rendered = messaging_service.render_template(tmpl.body, booking)

    log = MessageLog(
        booking_id=booking.id,
        template_id=tmpl.id,
        trigger=tmpl.trigger,
        status=MessageStatus.PENDING,
        rendered_body=rendered,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    from services.airbnb_client import airbnb_client
    success = await airbnb_client.send_message(booking.external_id, rendered)
    if success:
        log.status = MessageStatus.SENT
        log.sent_at = datetime.utcnow()
    else:
        log.status = MessageStatus.FAILED
        log.error = "API returned failure"
    db.commit()
    db.refresh(log)
    return log


@router.post("/process-pending", summary="Trigger pending message dispatch (admin)")
async def process_pending_messages(db: Session = Depends(get_db)):
    """Manually trigger the scheduled message dispatcher."""
    sent = await messaging_service.send_pending_messages(db)
    return {"sent": sent}
