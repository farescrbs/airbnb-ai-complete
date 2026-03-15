from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Listing
from schemas import ListingCreate, ListingOut

router = APIRouter(prefix="/listings", tags=["Listings"])


@router.post("/", response_model=ListingOut, status_code=201)
def create_listing(payload: ListingCreate, db: Session = Depends(get_db)):
    listing = Listing(**payload.model_dump())
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


@router.get("/", response_model=List[ListingOut])
def list_listings(db: Session = Depends(get_db)):
    return db.query(Listing).all()


@router.get("/{listing_id}", response_model=ListingOut)
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.put("/{listing_id}", response_model=ListingOut)
def update_listing(listing_id: int, payload: ListingCreate, db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    for k, v in payload.model_dump().items():
        setattr(listing, k, v)
    db.commit()
    db.refresh(listing)
    return listing


@router.delete("/{listing_id}", status_code=204)
def delete_listing(listing_id: int, db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    db.delete(listing)
    db.commit()
