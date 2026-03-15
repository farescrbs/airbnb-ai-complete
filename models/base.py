from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Date, Text, ForeignKey, Enum as SAEnum,
)
from sqlalchemy.orm import relationship
import enum
from database import Base


# ── Enums ────────────────────────────────────────────────────────────────────

class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class MessageTrigger(str, enum.Enum):
    BOOKING_CONFIRMED = "booking_confirmed"
    CHECK_IN_REMINDER = "check_in_reminder"      # 24 h before
    DAY_OF_CHECK_IN = "day_of_check_in"
    MID_STAY = "mid_stay"
    CHECK_OUT_REMINDER = "check_out_reminder"    # morning of checkout
    POST_CHECKOUT = "post_checkout"              # review request


class MessageStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


class PricingStrategy(str, enum.Enum):
    FLAT = "flat"
    OCCUPANCY_BASED = "occupancy_based"
    SEASONAL = "seasonal"
    DEMAND_BASED = "demand_based"


class Platform(str, enum.Enum):
    AIRBNB = "airbnb"
    VRBO = "vrbo"
    BOOKINGCOM = "bookingcom"
    DIRECT = "direct"


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    POSTED = "posted"
    SKIPPED = "skipped"


class CleaningStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ── Models ───────────────────────────────────────────────────────────────────

class Listing(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True)
    external_id = Column(String(64), unique=True, index=True)  # Airbnb listing ID
    platform = Column(SAEnum(Platform), default=Platform.AIRBNB)
    name = Column(String(256), nullable=False)
    address = Column(String(512))
    base_price = Column(Float, nullable=False)
    min_price = Column(Float)
    max_price = Column(Float)
    smart_lock_id = Column(String(128))  # device ID for smart lock integration
    ical_url = Column(Text)              # outbound iCal feed URL from platform
    created_at = Column(DateTime, default=datetime.utcnow)

    bookings = relationship("Booking", back_populates="listing")
    pricing_rules = relationship("PricingRule", back_populates="listing")
    calendar_feeds = relationship("CalendarFeed", back_populates="listing")
    cleaning_tasks = relationship("CleaningTask", back_populates="listing")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False)
    external_id = Column(String(64), unique=True, index=True)  # Airbnb reservation ID
    platform = Column(SAEnum(Platform), default=Platform.AIRBNB)
    status = Column(SAEnum(BookingStatus), default=BookingStatus.PENDING)

    guest_name = Column(String(256))
    guest_email = Column(String(256))
    guest_phone = Column(String(64))
    num_guests = Column(Integer, default=1)

    check_in = Column(Date, nullable=False)
    check_out = Column(Date, nullable=False)
    nightly_rate = Column(Float)
    total_price = Column(Float)

    access_code = Column(String(32))  # smart lock code generated for this stay
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    listing = relationship("Listing", back_populates="bookings")
    message_logs = relationship("MessageLog", back_populates="booking")
    review = relationship("Review", back_populates="booking", uselist=False)
    cleaning_task = relationship("CleaningTask", back_populates="booking", uselist=False)


class MessageTemplate(Base):
    __tablename__ = "message_templates"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    trigger = Column(SAEnum(MessageTrigger), nullable=False)
    subject = Column(String(256))
    body = Column(Text, nullable=False)   # Jinja2 template syntax
    send_offset_hours = Column(Integer, default=0)  # hours relative to trigger event
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    logs = relationship("MessageLog", back_populates="template")


class MessageLog(Base):
    __tablename__ = "message_logs"

    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("message_templates.id"), nullable=False)
    trigger = Column(SAEnum(MessageTrigger))
    status = Column(SAEnum(MessageStatus), default=MessageStatus.PENDING)
    scheduled_at = Column(DateTime)
    sent_at = Column(DateTime)
    rendered_body = Column(Text)
    error = Column(Text)

    booking = relationship("Booking", back_populates="message_logs")
    template = relationship("MessageTemplate", back_populates="logs")


class PricingRule(Base):
    __tablename__ = "pricing_rules"

    id = Column(Integer, primary_key=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False)
    name = Column(String(128))
    strategy = Column(SAEnum(PricingStrategy), default=PricingStrategy.OCCUPANCY_BASED)
    is_active = Column(Boolean, default=True)

    # Occupancy-based thresholds (% occupancy → multiplier)
    low_occupancy_threshold = Column(Float, default=0.3)   # < 30% → discount
    high_occupancy_threshold = Column(Float, default=0.7)  # > 70% → premium
    low_multiplier = Column(Float, default=0.85)
    high_multiplier = Column(Float, default=1.20)

    # Seasonal overrides (JSON stored as text)
    seasonal_config = Column(Text)   # JSON: [{month: 12, multiplier: 1.5}, ...]

    # Demand-based
    demand_multiplier = Column(Float, default=1.0)
    last_demand_check = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    listing = relationship("Listing", back_populates="pricing_rules")


class CalendarFeed(Base):
    __tablename__ = "calendar_feeds"

    id = Column(Integer, primary_key=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False)
    platform = Column(SAEnum(Platform), nullable=False)
    ical_url = Column(Text, nullable=False)  # external iCal feed to import
    last_synced = Column(DateTime)
    sync_interval_minutes = Column(Integer, default=60)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    listing = relationship("Listing", back_populates="calendar_feeds")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False, unique=True)
    status = Column(SAEnum(ReviewStatus), default=ReviewStatus.PENDING)
    rating = Column(Integer)          # 1-5 auto-determined
    public_review = Column(Text)      # text posted publicly
    private_feedback = Column(Text)   # private feedback to guest
    template_category = Column(String(64))  # excellent | good | average | poor
    posted_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    booking = relationship("Booking", back_populates="review")


class CleaningTask(Base):
    __tablename__ = "cleaning_tasks"

    id = Column(Integer, primary_key=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False)
    booking_id = Column(Integer, ForeignKey("bookings.id"))
    status = Column(SAEnum(CleaningStatus), default=CleaningStatus.SCHEDULED)
    scheduled_date = Column(Date, nullable=False)
    scheduled_time = Column(String(8), default="11:00")  # HH:MM
    cleaner_name = Column(String(256))
    cleaner_contact = Column(String(256))
    notes = Column(Text)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    listing = relationship("Listing", back_populates="cleaning_tasks")
    booking = relationship("Booking", back_populates="cleaning_task")
