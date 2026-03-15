"""
Mock Airbnb API client.

Replace the stub methods with real HTTP calls once you obtain API credentials.
Airbnb does not provide a public API, but you can:
  1. Use the unofficial API (reverse-engineered) – search PyPI for 'airbnb' packages.
  2. Apply for the Airbnb API via https://www.airbnb.com/partner
  3. Use a third-party property management API (Hostaway, Guesty, Lodgify) that
     connects to Airbnb on your behalf.
"""
import logging
from typing import Optional
import httpx
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AirbnbClient:
    BASE_URL = "https://api.airbnb.com/v2"  # placeholder – not a public endpoint

    def __init__(self):
        self.api_key = settings.airbnb_api_key
        self.user_id = settings.airbnb_user_id
        self._client = httpx.AsyncClient(
            headers={
                "X-Airbnb-API-Key": self.api_key,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def send_message(self, reservation_id: str, message: str) -> bool:
        """Send a message to a guest via Airbnb's messaging thread."""
        if not self.api_key:
            logger.warning("Airbnb API key not configured – simulating message send")
            logger.info(f"[MOCK] Message to reservation {reservation_id}: {message[:80]}...")
            return True  # mock success

        try:
            resp = await self._client.post(
                f"{self.BASE_URL}/messages",
                json={"reservation_id": reservation_id, "message": message},
            )
            resp.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to send Airbnb message: {e}")
            return False

    async def get_reservations(self, listing_id: str) -> list[dict]:
        """Fetch reservations for a listing."""
        if not self.api_key:
            logger.warning("Airbnb API key not configured – returning mock reservations")
            return []

        try:
            resp = await self._client.get(
                f"{self.BASE_URL}/reservations",
                params={"listing_id": listing_id, "user_id": self.user_id},
            )
            resp.raise_for_status()
            return resp.json().get("reservations", [])
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch reservations: {e}")
            return []

    async def update_listing_price(self, listing_id: str, date: str, price: float) -> bool:
        """Update the nightly price for a specific date on Airbnb."""
        if not self.api_key:
            logger.info(f"[MOCK] Price update – listing {listing_id}, date {date}, price ${price:.2f}")
            return True

        try:
            resp = await self._client.put(
                f"{self.BASE_URL}/listings/{listing_id}/price",
                json={"date": date, "price": price},
            )
            resp.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to update price: {e}")
            return False

    async def post_review(
        self,
        reservation_id: str,
        rating: int,
        public_review: str,
        private_feedback: Optional[str] = None,
    ) -> bool:
        """Post a host review for a guest."""
        if not self.api_key:
            logger.info(f"[MOCK] Review posted for reservation {reservation_id} – {rating}★")
            return True

        payload = {
            "reservation_id": reservation_id,
            "rating": rating,
            "public_review": public_review,
        }
        if private_feedback:
            payload["private_feedback"] = private_feedback

        try:
            resp = await self._client.post(f"{self.BASE_URL}/reviews", json=payload)
            resp.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to post review: {e}")
            return False

    async def close(self):
        await self._client.aclose()


airbnb_client = AirbnbClient()
