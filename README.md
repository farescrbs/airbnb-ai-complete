# Airbnb AI Complete

> **Application complète de gestion Airbnb propulsée par IA**
> Fusion de `airbnb-agent` (conversationnel) + `airbnb-automation` (automation)

---

## 🎯 Fonctionnalités

### 🤖 Agent Conversationnel (ex-airbnb-agent)
- [x] Répond aux messages des voyageurs en temps réel
- [x] Comprend le contexte et l'historique
- [x] Gère les objections et négociations
- [x] Scoring des clients (qualité, fiabilité, rentabilité)

### 📅 Gestion des Réservations
- [x] Vérification disponibilités
- [x] Création de réservations
- [x] Calcul dynamique des prix
- [x] Gestion des annulations/modifications

### 💰 Optimisation Revenue
- [x] Pricing dynamique (saisonnalité, demande, événements)
- [x] Ajustement automatique des tarifs
- [x] Minimisation des trous dans le calendrier

### 📨 Communication Automatique
- [x] Messages de bienvenue (booking confirmé)
- [x] Rappels check-in (24h avant)
- [x] Instructions d'arrivée (jour J)
- [x] Check mid-stay
- [x] Check-out et demande d'avis
- [x] Réponses aux questions fréquentes

### 🔐 Opérations
- [x] Génération codes serrure connectée
- [x] Planification ménage automatique
- [x] Gestion des reviews (génération + publication)
- [x] Suivi des incidents

### 📊 Analytics
- [x] Tableau de bord temps réel
- [x] Stats occupation et revenus
- [x] Performance de l'agent IA
- [x] Satisfaction clients

---

## 🏗️ Architecture

```
airbnb-ai-complete/
├── agent/              # Agent IA conversationnel
│   ├── core.py         # Cerveau de l'agent
│   ├── tools.py        # Outils disponibles
│   └── scoring.py      # Scoring clients
├── api/                # API FastAPI
│   ├── main.py         # Point d'entrée
│   ├── routers/        # Endpoints
│   └── middleware/     # Auth, logging
├── services/           # Logique métier
│   ├── messaging.py    # Gestion messages
│   ├── pricing.py      # Pricing dynamique
│   ├── calendar.py     # Calendrier
│   ├── reviews.py      # Reviews auto
│   └── operations.py   # Ménage, serrures
├── models/             # Modèles de données
│   ├── guest.py        # Voyageur
│   ├── booking.py      # Réservation
│   ├── listing.py      # Annonce
│   └── conversation.py # Historique chat
├── utils/              # Utilitaires
│   ├── database.py     # Connexion DB
│   ├── config.py       # Configuration
│   └── helpers.py      # Fonctions helpers
├── tests/              # Tests
├── docs/               # Documentation
└── README.md           # Ce fichier
```

---

## 🚀 Démarrage rapide

```bash
# 1. Entrer dans le projet
cd airbnb-ai-complete

# 2. Créer l'environnement virtuel
python -m venv .venv && source .venv/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec tes clés API

# 5. Initialiser la base de données
python -m utils.init_db

# 6. Lancer l'application
python -m api.main
```

L'API est disponible sur **http://localhost:8000**

Documentation interactive : **http://localhost:8000/docs**

---

## 🔌 Intégrations

| Service | Statut | Description |
|---------|--------|-------------|
| **Claude/OpenAI** | ✅ | Agent conversationnel |
| **Airbnb** | ⚠️ | Via iCal ou PMS (Hostaway/Guesty) |
| **SendGrid** | ✅ | Envoi d'emails |
| **Twilio** | 🔄 | SMS/WhatsApp (optionnel) |
| **Smart Lock** | 🔄 | August, Schlage, igloohome |

---

## 📋 Roadmap

### Phase 1 - MVP (Semaine 1-2)
- [ ] Fusionner code des deux projets
- [ ] Agent conversationnel basique
- [ ] Gestion réservations simple
- [ ] Messages automatiques

### Phase 2 - Automation (Semaine 3-4)
- [ ] Pricing dynamique
- [ ] Calendrier sync
- [ ] Reviews auto
- [ ] Dashboard

### Phase 3 - Intelligence (Semaine 5-6)
- [ ] Scoring avancé clients
- [ ] Prédiction demande
- [ ] Optimisation revenue
- [ ] Multi-propriétés

### Phase 4 - Scale (Semaine 7+)
- [ ] Interface propriétaire
- [ ] API publique
- [ ] White-label pour conciergeries

---

## 💡 Usage pour conciergeries

Ce projet peut être utilisé de deux façons :

1. **Pour toi** : Gérer tes propres biens
2. **White-label** : Vendre aux conciergeries (SaaS)

---

## 📁 Fichiers source

- Code original `airbnb-agent/` → `agent/`
- Code original `airbnb-automation/` → `api/` + `services/`

---
*Créé le : 13 mars 2026*
*Fusion de airbnb-agent + airbnb-automation*
