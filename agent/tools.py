"""
Outils disponibles pour l'agent Airbnb.
Chaque fonction correspond à un outil Claude.
"""
import uuid
from datetime import datetime, timedelta
import database as db
import config as cfg


def calculate_price(check_in: str, check_out: str, num_guests: int = 1) -> dict:
    """Calcule le prix total pour un séjour."""
    ci = datetime.strptime(check_in, "%Y-%m-%d")
    co = datetime.strptime(check_out, "%Y-%m-%d")
    nights = (co - ci).days

    if nights <= 0:
        return {"error": "Dates invalides : check-out doit être après check-in"}

    price_per_night = cfg.DEFAULT_PRICE_PER_NIGHT
    subtotal = price_per_night * nights

    discount_pct = 0
    discount_label = None
    if nights >= 28:
        discount_pct = cfg.MONTHLY_DISCOUNT
        discount_label = f"Réduction mensuelle ({int(cfg.MONTHLY_DISCOUNT*100)}%)"
    elif nights >= 7:
        discount_pct = cfg.WEEKLY_DISCOUNT
        discount_label = f"Réduction hebdomadaire ({int(cfg.WEEKLY_DISCOUNT*100)}%)"

    discount_amount = subtotal * discount_pct
    total = subtotal - discount_amount + cfg.CLEANING_FEE

    return {
        "check_in": check_in,
        "check_out": check_out,
        "num_nights": nights,
        "num_guests": num_guests,
        "price_per_night": price_per_night,
        "subtotal": round(subtotal, 2),
        "discount": discount_label,
        "discount_amount": round(discount_amount, 2),
        "cleaning_fee": cfg.CLEANING_FEE,
        "total": round(total, 2),
    }


def check_availability(check_in: str, check_out: str) -> dict:
    """Vérifie si les dates sont disponibles."""
    available = db.is_available(check_in, check_out)
    blocked = db.get_blocked_dates()

    ci = datetime.strptime(check_in, "%Y-%m-%d")
    co = datetime.strptime(check_out, "%Y-%m-%d")
    nights = (co - ci).days

    conflicts = []
    if not available:
        existing = db.list_reservations(from_date=check_in, to_date=check_out)
        for r in existing:
            if r["status"] not in ("cancelled", "rejected"):
                conflicts.append(f"{r['check_in']} → {r['check_out']} ({r['guest_name']})")

    return {
        "available": available,
        "check_in": check_in,
        "check_out": check_out,
        "nights": nights,
        "conflicts": conflicts,
        "min_nights": cfg.MIN_NIGHTS,
        "meets_minimum": nights >= cfg.MIN_NIGHTS,
    }


def create_reservation(
    guest_name: str,
    check_in: str,
    check_out: str,
    num_guests: int,
    guest_email: str = "",
    platform: str = "airbnb",
    notes: str = "",
) -> dict:
    """Crée une nouvelle réservation."""
    avail = check_availability(check_in, check_out)
    if not avail["available"]:
        return {"success": False, "error": "Dates non disponibles", "conflicts": avail["conflicts"]}

    if num_guests > cfg.MAX_GUESTS:
        return {"success": False, "error": f"Nombre de voyageurs maximum : {cfg.MAX_GUESTS}"}

    pricing = calculate_price(check_in, check_out, num_guests)
    if "error" in pricing:
        return {"success": False, "error": pricing["error"]}

    res_id = str(uuid.uuid4())[:8].upper()
    data = {
        "id": res_id,
        "guest_name": guest_name,
        "guest_email": guest_email,
        "check_in": check_in,
        "check_out": check_out,
        "num_guests": num_guests,
        "num_nights": pricing["num_nights"],
        "total_price": pricing["total"],
        "status": "confirmed",
        "platform": platform,
        "notes": notes,
    }
    db.add_reservation(data)

    # Planifier les tâches automatiques
    ci = datetime.strptime(check_in, "%Y-%m-%d")
    co = datetime.strptime(check_out, "%Y-%m-%d")
    db.add_task(res_id, "welcome_message", (ci - timedelta(days=2)).strftime("%Y-%m-%d 09:00"),
                "Envoyer message de bienvenue avec instructions d'accès")
    db.add_task(res_id, "checkin_reminder", ci.strftime("%Y-%m-%d 08:00"),
                "Rappel check-in le jour J")
    db.add_task(res_id, "mid_stay_check", (ci + timedelta(days=max(1, pricing["num_nights"]//2))).strftime("%Y-%m-%d 10:00"),
                "Message de mi-séjour")
    db.add_task(res_id, "checkout_reminder", (co - timedelta(days=1)).strftime("%Y-%m-%d 18:00"),
                "Rappel check-out pour le lendemain")
    db.add_task(res_id, "review_request", (co + timedelta(days=1)).strftime("%Y-%m-%d 10:00"),
                "Demande d'avis après le départ")

    return {"success": True, "reservation_id": res_id, **data, "pricing": pricing}


def get_reservation(reservation_id: str) -> dict:
    """Récupère les détails d'une réservation."""
    res = db.get_reservation(reservation_id)
    if not res:
        return {"error": f"Réservation {reservation_id} introuvable"}
    messages = db.get_messages(reservation_id)
    res["messages"] = messages
    return res


def list_reservations(status: str = None, period: str = "upcoming") -> dict:
    """Liste les réservations. period: upcoming | past | all"""
    today = datetime.now().strftime("%Y-%m-%d")
    if period == "upcoming":
        reservations = db.list_reservations(status=status, from_date=today)
    elif period == "past":
        reservations = db.list_reservations(status=status, to_date=today)
    else:
        reservations = db.list_reservations(status=status)
    return {"count": len(reservations), "reservations": reservations}


def update_reservation(reservation_id: str, status: str, notes: str = None) -> dict:
    """Met à jour le statut d'une réservation (confirmed/cancelled/rejected/completed)."""
    res = db.get_reservation(reservation_id)
    if not res:
        return {"error": f"Réservation {reservation_id} introuvable"}
    db.update_reservation_status(reservation_id, status, notes)
    return {"success": True, "reservation_id": reservation_id, "new_status": status}


def block_dates(start_date: str, end_date: str, reason: str = "Maintenance") -> dict:
    """Bloque des dates (maintenance, usage personnel, etc.)."""
    db.block_dates(start_date, end_date, reason)
    return {"success": True, "blocked": {"start": start_date, "end": end_date, "reason": reason}}


def get_calendar(month: str = None) -> dict:
    """Retourne la vue calendrier avec réservations et blocages."""
    if month:
        year, m = month.split("-")
        from_date = f"{year}-{m}-01"
        import calendar
        last_day = calendar.monthrange(int(year), int(m))[1]
        to_date = f"{year}-{m}-{last_day:02d}"
    else:
        today = datetime.now()
        from_date = today.strftime("%Y-%m-%d")
        to_date = (today + timedelta(days=90)).strftime("%Y-%m-%d")

    reservations = db.list_reservations(from_date=from_date, to_date=to_date)
    blocked = db.get_blocked_dates()

    return {
        "period": f"{from_date} → {to_date}",
        "reservations": [
            {
                "id": r["id"],
                "guest": r["guest_name"],
                "check_in": r["check_in"],
                "check_out": r["check_out"],
                "status": r["status"],
                "nights": r["num_nights"],
            }
            for r in reservations
        ],
        "blocked_dates": blocked,
    }


def generate_message(message_type: str, reservation_id: str, custom_context: str = "") -> dict:
    """
    Génère un message pour un voyageur.
    Types: welcome | check_in_instructions | mid_stay | checkout_reminder | review_request | inquiry_response | custom
    """
    res = db.get_reservation(reservation_id) if reservation_id else {}
    guest_name = res.get("guest_name", "Voyageur") if res else "Voyageur"

    templates = {
        "welcome": f"""Bonjour {guest_name},

Merci pour votre réservation à {cfg.PROPERTY_NAME} ! Nous avons hâte de vous accueillir du {res.get('check_in', '')} au {res.get('check_out', '')}.

Voici les informations importantes :
- Check-in : à partir de {cfg.CHECK_IN_TIME}
- Check-out : avant {cfg.CHECK_OUT_TIME}
- Nombre de voyageurs : {res.get('num_guests', '')}

Je vous enverrai les instructions d'accès détaillées 24h avant votre arrivée.

N'hésitez pas à me contacter pour toute question !

Cordialement,
{cfg.HOST_NAME}""",

        "check_in_instructions": f"""Bonjour {guest_name},

Votre arrivée est demain ! Voici les instructions d'accès :

{cfg.ACCESS_INSTRUCTIONS or "Les instructions d'accès seront communiquées directement."}

WiFi : {cfg.WIFI_NAME or "Communiqué sur place"}
Mot de passe : {cfg.WIFI_PASSWORD or "Communiqué sur place"}

Règles de la maison :
{cfg.HOUSE_RULES}

Bon voyage et à demain !
{cfg.HOST_NAME}""",

        "mid_stay": f"""Bonjour {guest_name},

J'espère que votre séjour se passe bien ! Tout est à votre goût ?

N'hésitez pas à me contacter si vous avez besoin de quoi que ce soit.

Cordialement,
{cfg.HOST_NAME}""",

        "checkout_reminder": f"""Bonjour {guest_name},

Votre séjour touche à sa fin ! Pour rappel, le check-out est demain avant {cfg.CHECK_OUT_TIME}.

Merci de laisser les clés {cfg.ACCESS_INSTRUCTIONS or "à l'emplacement indiqué"} et de laisser le logement dans l'état où vous l'avez trouvé.

Ce fut un plaisir de vous accueillir !
{cfg.HOST_NAME}""",

        "review_request": f"""Bonjour {guest_name},

J'espère que vous êtes bien rentré(e) ! Ce fut un plaisir de vous accueillir à {cfg.PROPERTY_NAME}.

Si vous avez apprécié votre séjour, je serais ravi(e) que vous laissiez un avis sur Airbnb. Cela m'aide énormément !

Je laisserai également un avis positif pour vous.

À bientôt peut-être !
{cfg.HOST_NAME}""",
    }

    message = templates.get(message_type, custom_context or "Message personnalisé")

    if reservation_id and res:
        db.save_message(reservation_id, "outgoing", message, auto_generated=True)

    return {
        "message_type": message_type,
        "reservation_id": reservation_id,
        "guest_name": guest_name,
        "message": message,
    }


def log_incoming_message(reservation_id: str, content: str) -> dict:
    """Enregistre un message entrant d'un voyageur."""
    db.save_message(reservation_id, "incoming", content, auto_generated=False)
    return {"success": True, "reservation_id": reservation_id, "logged": content}


def add_review(reservation_id: str, rating: float, comment: str) -> dict:
    """Enregistre l'avis d'un voyageur."""
    db.save_review(reservation_id, rating, comment)
    return {"success": True, "reservation_id": reservation_id, "rating": rating}


def get_stats() -> dict:
    """Retourne les statistiques globales de la propriété."""
    stats = db.get_stats()
    reviews = db.get_reviews()
    return {**stats, "recent_reviews": reviews[:5]}


def get_pending_tasks() -> dict:
    """Retourne les tâches en attente (messages à envoyer, rappels, etc.)."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    tasks = db.get_pending_tasks(before_datetime=now)
    return {"count": len(tasks), "tasks": tasks}


def complete_task(task_id: int) -> dict:
    """Marque une tâche comme complétée."""
    db.complete_task(task_id)
    return {"success": True, "task_id": task_id, "status": "completed"}


# Mapping nom → fonction pour l'agent
TOOL_FUNCTIONS = {
    "calculate_price": calculate_price,
    "check_availability": check_availability,
    "create_reservation": create_reservation,
    "get_reservation": get_reservation,
    "list_reservations": list_reservations,
    "update_reservation": update_reservation,
    "block_dates": block_dates,
    "get_calendar": get_calendar,
    "generate_message": generate_message,
    "log_incoming_message": log_incoming_message,
    "add_review": add_review,
    "get_stats": get_stats,
    "get_pending_tasks": get_pending_tasks,
    "complete_task": complete_task,
}
