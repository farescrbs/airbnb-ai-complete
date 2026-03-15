"""
Guest messaging service.
Renders Jinja2 templates and sends messages via Airbnb (or email fallback).
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from jinja2 import Environment, BaseLoader
from sqlalchemy.orm import Session
from models import Booking, MessageTemplate, MessageLog, MessageTrigger, MessageStatus, BookingStatus
from services.airbnb_client import airbnb_client

logger = logging.getLogger(__name__)

jinja_env = Environment(loader=BaseLoader())

# Default templates loaded at startup if the DB is empty
DEFAULT_TEMPLATES = [
    {
        "name": "Booking Confirmed",
        "trigger": MessageTrigger.BOOKING_CONFIRMED,
        "subject": "Your booking at {{ listing_name }} is confirmed!",
        "body": (
            "Hi {{ guest_name }},\n\n"
            "Great news! Your reservation at **{{ listing_name }}** is confirmed.\n\n"
            "📅 Check-in: {{ check_in }}\n"
            "📅 Check-out: {{ check_out }}\n"
            "👥 Guests: {{ num_guests }}\n\n"
            "We'll send check-in details 24 hours before your arrival.\n\n"
            "Feel free to message if you have any questions!\n\nWarm regards,\nYour Host"
        ),
        "send_offset_hours": 0,
    },
    {
        "name": "Check-In Reminder (24h)",
        "trigger": MessageTrigger.CHECK_IN_REMINDER,
        "subject": "Your check-in tomorrow at {{ listing_name }}",
        "body": (
            "Hi {{ guest_name }},\n\n"
            "You're checking in tomorrow! Here are your details:\n\n"
            "📍 Address: {{ address }}\n"
            "🔑 Access code: {{ access_code }}\n"
            "🕐 Check-in time: 3:00 PM\n\n"
            "**Wi-Fi:** Available – details inside the property.\n\n"
            "Safe travels! We can't wait to host you.\n\nYour Host"
        ),
        "send_offset_hours": -24,
    },
    {
        "name": "Day of Check-In",
        "trigger": MessageTrigger.DAY_OF_CHECK_IN,
        "subject": "Welcome! Your stay at {{ listing_name }} starts today",
        "body": (
            "Hi {{ guest_name }},\n\n"
            "Welcome! Today's the day 🎉\n\n"
            "🔑 Access code: {{ access_code }}\n"
            "📞 Need help? Reply to this message anytime.\n\n"
            "Enjoy your stay!\n\nYour Host"
        ),
        "send_offset_hours": 0,
    },
    {
        "name": "Mid-Stay Check-In",
        "trigger": MessageTrigger.MID_STAY,
        "subject": "How's your stay going?",
        "body": (
            "Hi {{ guest_name }},\n\n"
            "Just checking in – hope you're enjoying your stay at {{ listing_name }}!\n\n"
            "Is there anything you need or any questions I can help with?\n\n"
            "Your Host"
        ),
        "send_offset_hours": 0,
    },
    {
        "name": "Check-Out Reminder",
        "trigger": MessageTrigger.CHECK_OUT_REMINDER,
        "subject": "Checkout reminder for {{ listing_name }}",
        "body": (
            "Hi {{ guest_name }},\n\n"
            "Just a reminder that checkout is today by **11:00 AM**.\n\n"
            "Please:\n"
            "- Leave the keys on the kitchen counter\n"
            "- Ensure all lights and appliances are off\n"
            "- Lock the front door\n\n"
            "It was a pleasure hosting you! I'll leave you a review shortly.\n\nYour Host"
        ),
        "send_offset_hours": 0,
    },
    {
        "name": "Post-Checkout Review Request",
        "trigger": MessageTrigger.POST_CHECKOUT,
        "subject": "Thank you for staying at {{ listing_name }}!",
        "body": (
            "Hi {{ guest_name }},\n\n"
            "Thank you so much for staying at {{ listing_name }} – it was a pleasure hosting you!\n\n"
            "If you enjoyed your stay, we'd really appreciate a review. "
            "It helps future guests and means a lot to us.\n\n"
            "Safe travels and hope to see you again!\n\nYour Host"
        ),
        "send_offset_hours": 2,  # 2h after checkout
    },
]


def seed_default_templates(db: Session):
    """Insert default templates if none exist."""
    if db.query(MessageTemplate).count() == 0:
        for tmpl in DEFAULT_TEMPLATES:
            db.add(MessageTemplate(**tmpl))
        db.commit()
        logger.info("Seeded default message templates.")


def render_template(template_body: str, booking: Booking) -> str:
    listing = booking.listing
    ctx = {
        "guest_name": booking.guest_name,
        "listing_name": listing.name if listing else "the property",
        "address": listing.address if listing else "",
        "check_in": booking.check_in.strftime("%A, %B %d, %Y"),
        "check_out": booking.check_out.strftime("%A, %B %d, %Y"),
        "num_guests": booking.num_guests,
        "access_code": booking.access_code or "TBD – will be sent closer to check-in",
    }
    tmpl = jinja_env.from_string(template_body)
    return tmpl.render(**ctx)


async def schedule_messages_for_booking(booking: Booking, db: Session):
    """Create MessageLog entries for all active templates matching future triggers."""
    templates = db.query(MessageTemplate).filter(MessageTemplate.is_active == True).all()
    now = datetime.utcnow()

    scheduled_count = 0
    for tmpl in templates:
        send_at = _compute_send_time(tmpl.trigger, booking, tmpl.send_offset_hours)
        if send_at is None or send_at < now:
            continue  # skip past events

        # Avoid duplicates
        existing = (
            db.query(MessageLog)
            .filter(
                MessageLog.booking_id == booking.id,
                MessageLog.template_id == tmpl.id,
            )
            .first()
        )
        if existing:
            continue

        log = MessageLog(
            booking_id=booking.id,
            template_id=tmpl.id,
            trigger=tmpl.trigger,
            status=MessageStatus.PENDING,
            scheduled_at=send_at,
        )
        db.add(log)
        scheduled_count += 1

    db.commit()
    logger.info(f"Scheduled {scheduled_count} messages for booking {booking.id}")
    return scheduled_count


async def send_pending_messages(db: Session):
    """Called by the scheduler – send all messages whose scheduled_at has passed."""
    now = datetime.utcnow()
    pending = (
        db.query(MessageLog)
        .filter(
            MessageLog.status == MessageStatus.PENDING,
            MessageLog.scheduled_at <= now,
        )
        .all()
    )

    sent = 0
    for log in pending:
        try:
            booking = log.booking
            if booking.status == BookingStatus.CANCELLED:
                log.status = MessageStatus.SKIPPED
                db.commit()
                continue

            rendered = render_template(log.template.body, booking)
            log.rendered_body = rendered

            success = await airbnb_client.send_message(booking.external_id, rendered)
            if success:
                log.status = MessageStatus.SENT
                log.sent_at = datetime.utcnow()
                sent += 1
            else:
                log.status = MessageStatus.FAILED
                log.error = "API returned failure"
        except Exception as exc:
            log.status = MessageStatus.FAILED
            log.error = str(exc)
            logger.exception(f"Error sending message log {log.id}")

        db.commit()

    logger.info(f"Sent {sent}/{len(pending)} pending messages")
    return sent


def _compute_send_time(
    trigger: MessageTrigger,
    booking: Booking,
    offset_hours: int,
) -> Optional[datetime]:
    """Return UTC datetime when a message should be sent."""
    check_in = datetime(booking.check_in.year, booking.check_in.month, booking.check_in.day, 15, 0)
    check_out = datetime(booking.check_out.year, booking.check_out.month, booking.check_out.day, 11, 0)

    mapping = {
        MessageTrigger.BOOKING_CONFIRMED: datetime.utcnow(),
        MessageTrigger.CHECK_IN_REMINDER: check_in + timedelta(hours=offset_hours),
        MessageTrigger.DAY_OF_CHECK_IN: check_in,
        MessageTrigger.MID_STAY: check_in + timedelta(days=(booking.check_out - booking.check_in).days // 2),
        MessageTrigger.CHECK_OUT_REMINDER: check_out,
        MessageTrigger.POST_CHECKOUT: check_out + timedelta(hours=abs(offset_hours) or 2),
    }
    return mapping.get(trigger)
