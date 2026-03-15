from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from database import get_db
from models import CalendarFeed, Listing
from schemas import CalendarFeedCreate, CalendarFeedOut, CalendarSyncResult
from services import calendar_service

router = APIRouter(prefix="/calendar", tags=["Calendar"])


@router.post("/feeds", response_model=CalendarFeedOut, status_code=201)
def add_feed(payload: CalendarFeedCreate, db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == payload.listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    feed = CalendarFeed(**payload.model_dump())
    db.add(feed)
    db.commit()
    db.refresh(feed)
    return feed


@router.get("/feeds", response_model=List[CalendarFeedOut])
def list_feeds(listing_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(CalendarFeed)
    if listing_id:
        q = q.filter(CalendarFeed.listing_id == listing_id)
    return q.all()


@router.delete("/feeds/{feed_id}", status_code=204)
def delete_feed(feed_id: int, db: Session = Depends(get_db)):
    feed = db.query(CalendarFeed).filter(CalendarFeed.id == feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    db.delete(feed)
    db.commit()


@router.post("/feeds/{feed_id}/sync", response_model=CalendarSyncResult)
async def sync_single_feed(feed_id: int, db: Session = Depends(get_db)):
    feed = db.query(CalendarFeed).filter(CalendarFeed.id == feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    result = await calendar_service.sync_feed(feed, db)
    return result


@router.post("/sync-all", summary="Sync all active calendar feeds (admin)")
async def sync_all(db: Session = Depends(get_db)):
    results = await calendar_service.sync_all_feeds(db)
    return {"synced_feeds": len(results), "results": results}


@router.get("/export/{listing_id}", response_class=Response)
def export_ical(listing_id: int, db: Session = Depends(get_db)):
    """Export listing bookings as an iCal feed (subscribe from other platforms)."""
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    ical_content = calendar_service.generate_ical_export(listing, db)
    return Response(
        content=ical_content,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="listing-{listing_id}.ics"'},
    )
