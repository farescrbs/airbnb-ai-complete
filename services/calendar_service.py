"""
Calendar & booking sync service.
Imports iCal feeds from external platforms (VRBO, Booking.com, direct) and
creates/updates bookings in the local database.
"""
import logging
from datetime import datetime, date, timedelta
from typing import Optional
import httpx
from icalendar import Calendar
from sqlalchemy.orm import Session
from models import CalendarFeed, Booking, Listing, BookingStatus, Platform
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def fetch_ical(url: str) -> Optional[bytes]:
    """Download an iCal feed."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch iCal from {url}: {e}")
        return None


def parse_ical_events(ical_data: bytes) -> list[dict]:
    """Parse iCal data and return a list of event dicts."""
    events = []
    try:
        cal = Calendar.from_ical(ical_data)
        for component in cal.walk():
            if component.name != "VEVENT":
                continue

            summary = str(component.get("SUMMARY", ""))
            uid = str(component.get("UID", ""))

            dtstart = component.get("DTSTART")
            dtend = component.get("DTEND")
            if not dtstart or not dtend:
                continue

            start = dtstart.dt if hasattr(dtstart.dt, "date") else dtstart.dt
            end = dtend.dt if hasattr(dtend.dt, "date") else dtend.dt

            # Normalize to date
            if isinstance(start, datetime):
                start = start.date()
            if isinstance(end, datetime):
                end = end.date()

            events.append({
                "uid": uid,
                "summary": summary,
                "check_in": start,
                "check_out": end,
            })
    except Exception as e:
        logger.error(f"Failed to parse iCal: {e}")

    return events


def detect_conflicts(
    listing_id: int,
    check_in: date,
    check_out: date,
    db: Session,
    exclude_external_id: Optional[str] = None,
) -> list[str]:
    """Return list of conflicting booking external IDs."""
    query = (
        db.query(Booking)
        .filter(
            Booking.listing_id == listing_id,
            Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.PENDING]),
            Booking.check_in < check_out,
            Booking.check_out > check_in,
        )
    )
    if exclude_external_id:
        query = query.filter(Booking.external_id != exclude_external_id)

    return [b.external_id for b in query.all()]


async def sync_feed(feed: CalendarFeed, db: Session) -> dict:
    """Sync a single iCal feed into the local bookings table."""
    ical_data = await fetch_ical(feed.ical_url)
    if not ical_data:
        return {"feed_id": feed.id, "events_imported": 0, "conflicts": [], "error": "fetch_failed"}

    events = parse_ical_events(ical_data)
    imported = 0
    conflicts = []

    for event in events:
        uid = event["uid"]
        check_in = event["check_in"]
        check_out = event["check_out"]

        # Skip blocked dates (no summary) and past events
        if check_out <= date.today():
            continue

        conflict_ids = detect_conflicts(feed.listing_id, check_in, check_out, db, exclude_external_id=uid)
        if conflict_ids:
            conflicts.append(
                f"Event {uid} ({check_in}→{check_out}) conflicts with: {', '.join(conflict_ids)}"
            )
            continue

        existing = db.query(Booking).filter(Booking.external_id == uid).first()
        if existing:
            # Update if dates changed
            if existing.check_in != check_in or existing.check_out != check_out:
                existing.check_in = check_in
                existing.check_out = check_out
                existing.updated_at = datetime.utcnow()
                db.commit()
        else:
            booking = Booking(
                listing_id=feed.listing_id,
                external_id=uid,
                platform=feed.platform,
                status=BookingStatus.CONFIRMED,
                guest_name=event["summary"] or "Guest",
                check_in=check_in,
                check_out=check_out,
            )
            db.add(booking)
            db.commit()
            imported += 1

    feed.last_synced = datetime.utcnow()
    db.commit()

    return {
        "feed_id": feed.id,
        "platform": feed.platform.value,
        "events_imported": imported,
        "conflicts": conflicts,
        "synced_at": feed.last_synced,
    }


async def sync_all_feeds(db: Session):
    """Scheduler job: sync all active calendar feeds."""
    feeds = db.query(CalendarFeed).filter(CalendarFeed.is_active == True).all()
    results = []
    for feed in feeds:
        result = await sync_feed(feed, db)
        results.append(result)
        logger.info(f"Synced feed {feed.id} ({feed.platform}) – {result.get('events_imported', 0)} imported")
    return results


def generate_ical_export(listing: Listing, db: Session) -> str:
    """Generate an iCal feed for a listing (to embed in Airbnb / share)."""
    bookings = (
        db.query(Booking)
        .filter(
            Booking.listing_id == listing.id,
            Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.PENDING]),
            Booking.check_out >= date.today(),
        )
        .all()
    )

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//Airbnb Automation//{listing.name}//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for b in bookings:
        dtstart = b.check_in.strftime("%Y%m%d")
        dtend = b.check_out.strftime("%Y%m%d")
        lines += [
            "BEGIN:VEVENT",
            f"UID:{b.external_id}",
            f"DTSTART;VALUE=DATE:{dtstart}",
            f"DTEND;VALUE=DATE:{dtend}",
            f"SUMMARY:Reserved – {b.guest_name}",
            "STATUS:CONFIRMED",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)
