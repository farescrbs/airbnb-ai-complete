from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import PricingRule, Listing
from schemas import PricingRuleCreate, PricingRuleOut, PriceCalculationResult
from services import pricing_service

router = APIRouter(prefix="/pricing", tags=["Pricing"])


@router.post("/rules", response_model=PricingRuleOut, status_code=201)
def create_rule(payload: PricingRuleCreate, db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == payload.listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    rule = PricingRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/rules", response_model=List[PricingRuleOut])
def list_rules(listing_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(PricingRule)
    if listing_id:
        q = q.filter(PricingRule.listing_id == listing_id)
    return q.all()


@router.get("/rules/{rule_id}", response_model=PricingRuleOut)
def get_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(PricingRule).filter(PricingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.put("/rules/{rule_id}", response_model=PricingRuleOut)
def update_rule(rule_id: int, payload: PricingRuleCreate, db: Session = Depends(get_db)):
    rule = db.query(PricingRule).filter(PricingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    for k, v in payload.model_dump().items():
        setattr(rule, k, v)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(PricingRule).filter(PricingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()


@router.get("/calculate", response_model=PriceCalculationResult)
def calculate_price(
    listing_id: int,
    target_date: date = None,
    db: Session = Depends(get_db),
):
    """Preview the calculated price for a listing on a given date."""
    if target_date is None:
        target_date = date.today()

    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    rule = (
        db.query(PricingRule)
        .filter(PricingRule.listing_id == listing_id, PricingRule.is_active == True)
        .first()
    )
    if not rule:
        raise HTTPException(status_code=404, detail="No active pricing rule for this listing")

    result = pricing_service.calculate_price(listing, rule, target_date, db)
    return result


@router.get("/occupancy/{listing_id}")
def get_occupancy(listing_id: int, window_days: int = 30, db: Session = Depends(get_db)):
    """Get the occupancy rate for the next N days."""
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    occupancy = pricing_service.calculate_occupancy(listing_id, db, window_days)
    return {
        "listing_id": listing_id,
        "window_days": window_days,
        "occupancy_rate": round(occupancy, 4),
        "occupancy_pct": f"{occupancy:.1%}",
    }


@router.post("/run-update", summary="Trigger pricing update for all listings (admin)")
async def run_pricing_update(db: Session = Depends(get_db)):
    updated = await pricing_service.run_pricing_update(db)
    return {"price_points_updated": updated}
