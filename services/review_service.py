"""
Review & operations service.
Auto-generates and posts guest reviews, manages cleaning schedules,
and interfaces with smart lock APIs.
"""
import logging
import random
from datetime import date, datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from models import (
    Booking, Review, CleaningTask, BookingStatus,
    ReviewStatus, CleaningStatus,
)
from services.airbnb_client import airbnb_client
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Review templates ──────────────────────────────────────────────────────────

REVIEW_TEMPLATES = {
    "excellent": [
        "{name} was a wonderful guest! They left the place spotless, "
        "communicated well, and were respectful of the house rules. "
        "I'd highly recommend them to any host. 5 stars!",
        "It was a pleasure hosting {name}. The property was left in perfect "
        "condition and they were very polite and easy to work with. "
        "Would love to have them back!",
    ],
    "good": [
        "{name} was a great guest overall. They took care of the place and "
        "were communicative throughout their stay. Would recommend.",
        "Hosting {name} was a pleasant experience. They followed the house rules "
        "and left the property in good shape. Happy to host again.",
    ],
    "average": [
        "{name} was an okay guest. There were a few minor issues but nothing "
        "major. Communication could have been better.",
        "{name} stayed without any major problems. The place needed a bit more "
        "cleaning than usual but overall fine.",
    ],
    "poor": [
        "Had some issues during {name}'s stay. I'd recommend other hosts to "
        "communicate expectations clearly before confirming.",
    ],
}

PRIVATE_FEEDBACK_TEMPLATES = {
    "excellent": "Thank you so much for being such a great guest, {name}! You're welcome back anytime.",
    "good": "Thanks for staying, {name}! Hope to host you again.",
    "average": "Thanks for your stay, {name}. Please make sure to follow house rules regarding {issue} next time.",
    "poor": "Dear {name}, I wanted to share some feedback privately. There were concerns about {issue} during your stay.",
}


def _determine_category(rating: int) -> str:
    if rating == 5:
        return "excellent"
    if rating == 4:
        return "good"
    if rating == 3:
        return "average"
    return "poor"


def generate_review_text(guest_name: str, category: str) -> tuple[str, str]:
    """Generate public review and private feedback text."""
    first_name = guest_name.split()[0] if guest_name else "Guest"

    templates = REVIEW_TEMPLATES.get(category, REVIEW_TEMPLATES["good"])
    public = random.choice(templates).format(name=first_name)

    private = PRIVATE_FEEDBACK_TEMPLATES.get(category, "").format(
        name=first_name, issue="house rules"
    )

    return public, private


def auto_rate_booking(booking: Booking) -> int:
    """
    Simple heuristic to auto-determine a star rating.
    In production, integrate with your cleaning reports / incident logs.
    """
    # Default to 5 stars; adjust based on factors you track
    rating = 5

    stay_length = (booking.check_out - booking.check_in).days
    if stay_length == 1:
        rating = min(rating, 4)  # short stays are higher risk

    if booking.num_guests and booking.num_guests >= 6:
        rating = min(rating, 4)  # large groups slightly lower default

    return rating


async def generate_and_queue_review(booking_id: int, db: Session, override_rating: Optional[int] = None) -> Review:
    """Create a Review record (pending posting)."""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise ValueError(f"Booking {booking_id} not found")

    if booking.review:
        return booking.review  # already queued

    rating = override_rating or auto_rate_booking(booking)
    category = _determine_category(rating)
    public_text, private_text = generate_review_text(booking.guest_name, category)

    review = Review(
        booking_id=booking.id,
        rating=rating,
        public_review=public_text,
        private_feedback=private_text,
        template_category=category,
        status=ReviewStatus.PENDING,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    logger.info(f"Queued review for booking {booking_id} – {rating}★ ({category})")
    return review


async def post_pending_reviews(db: Session):
    """Scheduler job: post reviews for checkouts that were ≥ 24 h ago."""
    cutoff = date.today() - timedelta(days=1)
    pending = (
        db.query(Review)
        .join(Booking)
        .filter(
            Review.status == ReviewStatus.PENDING,
            Booking.check_out <= cutoff,
        )
        .all()
    )

    posted = 0
    for review in pending:
        booking = review.booking
        success = await airbnb_client.post_review(
            booking.external_id,
            review.rating,
            review.public_review,
            review.private_feedback,
        )
        if success:
            review.status = ReviewStatus.POSTED
            review.posted_at = datetime.utcnow()
            posted += 1
        else:
            logger.warning(f"Failed to post review for booking {booking.id}")
        db.commit()

    logger.info(f"Posted {posted}/{len(pending)} pending reviews")
    return posted


# ── Cleaning schedule ─────────────────────────────────────────────────────────

def schedule_cleaning_for_booking(booking: Booking, db: Session) -> CleaningTask:
    """Auto-create a cleaning task on the checkout day."""
    existing = db.query(CleaningTask).filter(CleaningTask.booking_id == booking.id).first()
    if existing:
        return existing

    task = CleaningTask(
        listing_id=booking.listing_id,
        booking_id=booking.id,
        scheduled_date=booking.check_out,
        scheduled_time="11:00",
        status=CleaningStatus.SCHEDULED,
        notes=f"Post-checkout clean after {booking.guest_name}'s stay",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    logger.info(f"Scheduled cleaning for listing {booking.listing_id} on {booking.check_out}")
    return task


# ── Smart lock ────────────────────────────────────────────────────────────────

def generate_access_code() -> str:
    """Generate a random 6-digit access code."""
    return str(random.randint(100000, 999999))


async def provision_smart_lock(booking: Booking, db: Session) -> Optional[str]:
    """
    Generate and set a unique access code on the smart lock for the duration of the stay.
    Currently mocked – wire up to August/Schlage/igloohome SDK in production.
    """
    listing = booking.listing
    if not listing or not listing.smart_lock_id:
        return None

    code = generate_access_code()

    if settings.smart_lock_api_key:
        # TODO: call your smart lock provider's API here
        # Example for August:
        #   await august_client.create_access_code(
        #       lock_id=listing.smart_lock_id,
        #       code=code,
        #       start=booking.check_in,
        #       end=booking.check_out,
        #   )
        logger.info(f"[MOCK] Smart lock code {code} provisioned for listing {listing.smart_lock_id}")
    else:
        logger.info(f"[MOCK] Generated access code {code} (smart lock not configured)")

    # Persist the code
    booking.access_code = code
    db.commit()
    return code
