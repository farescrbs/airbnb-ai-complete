import os
from dotenv import load_dotenv

load_dotenv()

# Anthropic API
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Propriété Airbnb
PROPERTY_NAME = os.getenv("PROPERTY_NAME", "Mon Appartement")
PROPERTY_ADDRESS = os.getenv("PROPERTY_ADDRESS", "")
HOST_NAME = os.getenv("HOST_NAME", "Host")
HOST_LANGUAGE = os.getenv("HOST_LANGUAGE", "fr")

# iCal Airbnb (URL d'export du calendrier)
AIRBNB_ICAL_URL = os.getenv("AIRBNB_ICAL_URL", "")

# Base de données
DB_PATH = os.getenv("DB_PATH", "airbnb_agent.db")

# Paramètres de tarification
DEFAULT_PRICE_PER_NIGHT = float(os.getenv("DEFAULT_PRICE_PER_NIGHT", "80"))
CLEANING_FEE = float(os.getenv("CLEANING_FEE", "30"))
WEEKLY_DISCOUNT = float(os.getenv("WEEKLY_DISCOUNT", "0.10"))  # 10%
MONTHLY_DISCOUNT = float(os.getenv("MONTHLY_DISCOUNT", "0.20"))  # 20%

# Règles de la propriété
MAX_GUESTS = int(os.getenv("MAX_GUESTS", "4"))
MIN_NIGHTS = int(os.getenv("MIN_NIGHTS", "2"))
CHECK_IN_TIME = os.getenv("CHECK_IN_TIME", "15:00")
CHECK_OUT_TIME = os.getenv("CHECK_OUT_TIME", "11:00")

# Règles de la maison (pour les messages automatiques)
HOUSE_RULES = os.getenv("HOUSE_RULES", """
- Pas de fête ni d'événements
- Non-fumeur
- Animaux non acceptés
- Respect du voisinage après 22h
""").strip()

# WiFi et équipements
WIFI_NAME = os.getenv("WIFI_NAME", "")
WIFI_PASSWORD = os.getenv("WIFI_PASSWORD", "")

# Instructions d'accès
ACCESS_INSTRUCTIONS = os.getenv("ACCESS_INSTRUCTIONS", "")
