"""
Dynamic pricing service.
Calculates optimal nightly prices based on occupancy, seasonality, and demand.
"""
import json
import logging
from datetime import date, datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from models import Listing, Booking, PricingRule, PricingStrategy, BookingStatus
from services.airbnb_client import airbnb_client
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Peak months → default seasonal multipliers (can be overridden per rule)
DEFAULT_SEASONAL = {
    12: 1.50,  # December (Christmas/New Year)
    1: 1.30,   # January (New Year)
    7: 1.35,   # July (summer peak)
    8: 1.35,   # August (summer peak)
    11: 1.10,  # Thanksgiving
    2: 1.05,   # Valentine's / winter sports
}

# Weekend premium
WEEKEND_MULTIPLIER = 1.15  # Friday & Saturday nights


def calculate_occupancy(listing_id: int, db: Session, window_days: int = 30) -> float:
    """Return occupancy rate for the next `window_days` days (0.0–1.0)."""
    today = date.today()
    end = today + timedelta(days=window_days)

    bookings = (
        db.query(Booking)
        .filter(
            Booking.listing_id == listing_id,
            Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.PENDING]),
            Booking.check_out > today,
            Booking.check_in < end,
        )
        .all()
    )

    booked_nights = 0
    for b in bookings:
        start = max(b.check_in, today)
        finish = min(b.check_out, end)
        booked_nights += (finish - start).days

    return booked_nights / window_days


def get_seasonal_multiplier(target_date: date, seasonal_config: Optional[str]) -> float:
    """Return the seasonal multiplier for a given date."""
    if seasonal_config:
        try:
            config = json.loads(seasonal_config)
            for entry in config:
                if entry.get("month") == target_date.month:
                    return float(entry.get("multiplier", 1.0))
        except (json.JSONDecodeError, TypeError):
            pass
    return DEFAULT_SEASONAL.get(target_date.month, 1.0)


def calculate_price(
    listing: Listing,
    rule: PricingRule,
    target_date: date,
    db: Session,
) -> dict:
    """Calculate the optimal price for a listing on a specific date."""
    base = listing.base_price
    multiplier = 1.0
    reasoning_parts = []

    if rule.strategy == PricingStrategy.FLAT:
        multiplier = 1.0
        reasoning_parts.append("Flat pricing – no adjustment")

    elif rule.strategy == PricingStrategy.OCCUPANCY_BASED:
        occupancy = calculate_occupancy(listing.id, db)
        if occupancy < rule.low_occupancy_threshold:
            multiplier = rule.low_multiplier
            reasoning_parts.append(
                f"Low occupancy ({occupancy:.0%} < {rule.low_occupancy_threshold:.0%}) → {multiplier:.0%} rate"
            )
        elif occupancy > rule.high_occupancy_threshold:
            multiplier = rule.high_multiplier
            reasoning_parts.append(
                f"High occupancy ({occupancy:.0%} > {rule.high_occupancy_threshold:.0%}) → {multiplier:.0%} rate"
            )
        else:
            reasoning_parts.append(f"Normal occupancy ({occupancy:.0%}) → base rate")

    elif rule.strategy == PricingStrategy.SEASONAL:
        multiplier = get_seasonal_multiplier(target_date, rule.seasonal_config)
        reasoning_parts.append(f"Seasonal multiplier for month {target_date.month}: {multiplier:.2f}x")

    elif rule.strategy == PricingStrategy.DEMAND_BASED:
        multiplier = rule.demand_multiplier
        reasoning_parts.append(f"Demand-based multiplier: {multiplier:.2f}x")

    # Weekend premium on top
    if target_date.weekday() in (4, 5):  # Friday=4, Saturday=5
        multiplier *= WEEKEND_MULTIPLIER
        reasoning_parts.append(f"Weekend premium (+{(WEEKEND_MULTIPLIER-1)*100:.0f}%)")

    calculated = round(base * multiplier, 2)

    # Clamp to listing min/max
    if listing.min_price and calculated < listing.min_price:
        calculated = listing.min_price
        reasoning_parts.append(f"Clamped to min price ${listing.min_price:.2f}")
    if listing.max_price and calculated > listing.max_price:
        calculated = listing.max_price
        reasoning_parts.append(f"Clamped to max price ${listing.max_price:.2f}")

    return {
        "listing_id": listing.id,
        "target_date": target_date,
        "base_price": base,
        "calculated_price": calculated,
        "applied_strategy": rule.strategy.value,
        "multiplier": round(multiplier, 4),
        "reasoning": " | ".join(reasoning_parts),
    }


async def run_pricing_update(db: Session):
    """
    Scheduler job: recalculate prices for the next 90 days for all listings
    that have active pricing rules, then push updates to Airbnb.
    """
    listings = db.query(Listing).all()
    today = date.today()
    updated = 0

    for listing in listings:
        rule = (
            db.query(PricingRule)
            .filter(PricingRule.listing_id == listing.id, PricingRule.is_active == True)
            .first()
        )
        if not rule:
            continue

        for day_offset in range(90):
            target = today + timedelta(days=day_offset)
            result = calculate_price(listing, rule, target, db)
            success = await airbnb_client.update_listing_price(
                listing.external_id, target.isoformat(), result["calculated_price"]
            )
            if success:
                updated += 1

        # Update demand check timestamp
        rule.last_demand_check = datetime.utcnow()
        db.commit()

    logger.info(f"Pricing update complete – {updated} price points pushed")
    return updated
