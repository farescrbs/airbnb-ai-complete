"""
Airbnb Automation API
~~~~~~~~~~~~~~~~~~~~~
A FastAPI-based backend automating:
  - Guest messaging (templated, event-triggered)
  - Dynamic pricing (occupancy / seasonal / demand)
  - Multi-platform calendar sync (iCal)
  - Guest reviews & operations (cleaning, smart locks)
"""
import logging
from contextlib import asynccontextmanager
from datetime import date, datetime
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from config import get_settings
from database import init_db, get_db, SessionLocal
from scheduler import start_scheduler, stop_scheduler
from routers import listings, bookings, messaging, pricing, calendar, operations
from schemas import DashboardStats
from models import (
    Listing, Booking, MessageLog, Review, CleaningTask,
    BookingStatus, MessageStatus, ReviewStatus, CleaningStatus,
)
from services.messaging_service import seed_default_templates

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database…")
    init_db()

    db = SessionLocal()
    try:
        seed_default_templates(db)
    finally:
        db.close()

    logger.info("Starting scheduler…")
    start_scheduler()

    yield

    # Shutdown
    stop_scheduler()
    logger.info("Application shutdown complete.")


app = FastAPI(
    title="Airbnb Automation API",
    description=(
        "Automate guest messaging, dynamic pricing, multi-platform calendar sync, "
        "guest reviews, cleaning schedules, and smart lock management."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

# ── UI routes ─────────────────────────────────────────────────────────────────

@app.get("/ui/listings")
def ui_listings(request: Request):
    return templates.TemplateResponse("listings.html", {"request": request})

@app.get("/ui/bookings")
def ui_bookings(request: Request):
    return templates.TemplateResponse("bookings.html", {"request": request})

@app.get("/ui/messaging")
def ui_messaging(request: Request):
    return templates.TemplateResponse("messaging.html", {"request": request})

@app.get("/ui/pricing")
def ui_pricing(request: Request):
    return templates.TemplateResponse("pricing.html", {"request": request})

@app.get("/ui/calendar")
def ui_calendar(request: Request):
    return templates.TemplateResponse("calendar.html", {"request": request})

@app.get("/ui/operations")
def ui_operations(request: Request):
    return templates.TemplateResponse("operations.html", {"request": request})

# Register routers
app.include_router(listings.router)
app.include_router(bookings.router)
app.include_router(messaging.router)
app.include_router(pricing.router)
app.include_router(calendar.router)
app.include_router(operations.router)


@app.get("/", tags=["UI"])
def root(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/dashboard", response_model=DashboardStats, tags=["Dashboard"])
def dashboard(db: Session = Depends(get_db)):
    """High-level stats overview."""
    today = date.today()

    active_bookings = db.query(Booking).filter(
        Booking.status == BookingStatus.CONFIRMED,
        Booking.check_in <= today,
        Booking.check_out >= today,
    ).count()

    upcoming_check_ins = db.query(Booking).filter(
        Booking.status == BookingStatus.CONFIRMED,
        Booking.check_in == today,
    ).count()

    upcoming_check_outs = db.query(Booking).filter(
        Booking.status == BookingStatus.CONFIRMED,
        Booking.check_out == today,
    ).count()

    messages_today = db.query(MessageLog).filter(
        MessageLog.status == MessageStatus.SENT,
        MessageLog.sent_at >= datetime.combine(today, datetime.min.time()),
    ).count()

    pending_reviews = db.query(Review).filter(Review.status == ReviewStatus.PENDING).count()

    pending_cleanings = db.query(CleaningTask).filter(
        CleaningTask.status == CleaningStatus.SCHEDULED
    ).count()

    # Revenue this month
    from sqlalchemy import func, extract
    revenue_result = db.query(func.sum(Booking.total_price)).filter(
        Booking.status == BookingStatus.CONFIRMED,
        extract("year", Booking.check_in) == today.year,
        extract("month", Booking.check_in) == today.month,
    ).scalar()

    return DashboardStats(
        total_listings=db.query(Listing).count(),
        active_bookings=active_bookings,
        upcoming_check_ins=upcoming_check_ins,
        upcoming_check_outs=upcoming_check_outs,
        messages_sent_today=messages_today,
        pending_reviews=pending_reviews,
        pending_cleanings=pending_cleanings,
        revenue_this_month=float(revenue_result or 0),
    )
