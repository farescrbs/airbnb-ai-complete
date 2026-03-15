#!/usr/bin/env python3
"""
Scoring Client - Évalue la qualité des voyageurs Airbnb
Inspiré des meilleures pratiques de conciergerie
"""

from datetime import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class GuestProfile:
    """Profil d'un voyageur"""
    name: str
    email: str
    phone: str = None
    country: str = None
    language: str = "fr"
    
    # Historique Airbnb
    reviews_count: int = 0
    reviews_rating: float = 0.0
    years_on_platform: int = 0
    previous_bookings: int = 0
    
    # Demande actuelle
    check_in_date: str = None
    check_out_date: str = None
    guests_count: int = 1
    message: str = ""
    instant_book: bool = False
    
    # Red flags
    questions_about_parties: bool = False
    mentions_extra_guests: bool = False
    short_notice: bool = False  # Réservation < 24h
    new_account: bool = False  # < 6 mois

class GuestScorer:
    """Système de scoring des voyageurs"""
    
    def __init__(self):
        self.weights = {
            "history": 0.30,
            "communication": 0.25,
            "booking_quality": 0.25,
            "red_flags": 0.20
        }
    
    def score_history(self, guest: GuestProfile) -> Tuple[int, List[str]]:
        """Score basé sur l'historique (0-100)"""
        score = 50  # Base
        notes = []
        
        # Reviews
        if guest.reviews_count >= 10:
            score += 20
            notes.append("✅ 10+ avis")
        elif guest.reviews_count >= 5:
            score += 10
            notes.append("⭐ 5+ avis")
        elif guest.reviews_count == 0:
            score -= 15
            notes.append("⚠️ Nouveau sur Airbnb")
        
        # Rating
        if guest.reviews_rating >= 4.8:
            score += 15
            notes.append("⭐⭐ Excellent rating")
        elif guest.reviews_rating >= 4.5:
            score += 10
            notes.append("⭐ Bon rating")
        elif guest.reviews_rating > 0 and guest.reviews_rating < 4.0:
            score -= 20
            notes.append("❌ Rating faible")
        
        # Ancienneté
        if guest.years_on_platform >= 2:
            score += 10
            notes.append("✅ Membre vérifié (2+ ans)")
        elif guest.new_account:
            score -= 10
            notes.append("⚠️ Compte récent")
        
        return min(100, max(0, score)), notes
    
    def score_communication(self, guest: GuestProfile) -> Tuple[int, List[str]]:
        """Score basé sur la communication (0-100)"""
        score = 50
        notes = []
        
        message = guest.message.lower()
        
        # Positifs
        if "bonjour" in message or "bonsoir" in message:
            score += 10
            notes.append("✅ Politesse")
        
        if len(message) > 100:
            score += 10
            notes.append("✅ Message détaillé")
        
        if "merci" in message:
            score += 5
            notes.append("✅ Courtoisie")
        
        # Négatifs
        if "!" in message and message.count("!") > 3:
            score -= 10
            notes.append("⚠️ Trop d'exclamations")
        
        if guest.questions_about_parties:
            score -= 30
            notes.append("❌ Question sur soirées")
        
        if "cigarette" in message or "fumer" in message:
            score -= 15
            notes.append("⚠️ Mention tabac")
        
        return min(100, max(0, score)), notes
    
    def score_booking_quality(self, guest: GuestProfile) -> Tuple[int, List[str]]:
        """Score basé sur la qualité de la réservation (0-100)"""
        score = 50
        notes = []
        
        # Durée du séjour
        if guest.check_in_date and guest.check_out_date:
            try:
                from datetime import datetime
                check_in = datetime.strptime(guest.check_in_date, "%Y-%m-%d")
                check_out = datetime.strptime(guest.check_out_date, "%Y-%m-%d")
                nights = (check_out - check_in).days
                
                if nights >= 7:
                    score += 15
                    notes.append(f"✅ Séjour long ({nights} nuits)")
                elif nights >= 3:
                    score += 10
                    notes.append(f"✅ Séjour moyen ({nights} nuits)")
                elif nights == 1:
                    score -= 5
                    notes.append("⚠️ Séjour 1 nuit")
                    
            except:
                pass
        
        # Nombre de voyageurs
        if guest.guests_count > 6:
            score -= 10
            notes.append("⚠️ Groupe important")
        elif guest.guests_count == 1:
            score += 5
            notes.append("✅ Voyageur seul (calme)")
        
        # Instant book
        if guest.instant_book:
            score += 10
            notes.append("✅ Instant Book (vérifié)")
        
        # Délai
        if guest.short_notice:
            score -= 10
            notes.append("⚠️ Réservation dernière minute")
        
        return min(100, max(0, score)), notes
    
    def score_red_flags(self, guest: GuestProfile) -> Tuple[int, List[str]]:
        """Détecte les red flags (0-100, 100 = aucun problème)"""
        score = 100
        notes = []
        
        red_flags = []
        
        if guest.questions_about_parties:
            red_flags.append("❌ Question sur soirées/fêtes")
            score -= 40
        
        if guest.mentions_extra_guests:
            red_flags.append("❌ Mention voyageurs non déclarés")
            score -= 30
        
        if guest.new_account and guest.reviews_count == 0:
            red_flags.append("❌ Compte tout neuf + 0 avis")
            score -= 25
        
        if guest.short_notice and guest.reviews_count < 3:
            red_flags.append("❌ Dernière minute + peu d'avis")
            score -= 20
        
        if not guest.message or len(guest.message) < 20:
            red_flags.append("⚠️ Message trop court/vide")
            score -= 15
        
        if red_flags:
            notes.extend(red_flags)
        else:
            notes.append("✅ Aucun red flag détecté")
        
        return max(0, score), notes
    
    def calculate_global_score(self, guest: GuestProfile) -> Dict:
        """Calcule le score global"""
        
        history_score, history_notes = self.score_history(guest)
        comm_score, comm_notes = self.score_communication(guest)
        booking_score, booking_notes = self.score_booking_quality(guest)
        red_flags_score, red_flags_notes = self.score_red_flags(guest)
        
        # Score pondéré
        global_score = (
            history_score * self.weights["history"] +
            comm_score * self.weights["communication"] +
            booking_score * self.weights["booking_quality"] +
            red_flags_score * self.weights["red_flags"]
        )
        
        # Catégorisation
        if global_score >= 80:
            category = "🟢 EXCELLENT"
            recommendation = "Accepter immédiatement"
        elif global_score >= 60:
            category = "🟡 BON"
            recommendation = "Accepter avec confirmation"
        elif global_score >= 40:
            category = "🟠 MOYEN"
            recommendation = "Vérifier avant d'accepter"
        else:
            category = "🔴 RISQUÉ"
            recommendation = "Refuser ou demander garantie"
        
        return {
            "guest_name": guest.name,
            "global_score": round(global_score, 1),
            "category": category,
            "recommendation": recommendation,
            "details": {
                "history": {"score": history_score, "notes": history_notes},
                "communication": {"score": comm_score, "notes": comm_notes},
                "booking": {"score": booking_score, "notes": booking_notes},
                "red_flags": {"score": red_flags_score, "notes": red_flags_notes}
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def generate_response(self, guest: GuestProfile, score: Dict) -> str:
        """Génère une réponse personnalisée basée sur le score"""
        
        if score["global_score"] >= 80:
            return f"""Bonjour {guest.name},

Merci pour votre intérêt ! Votre profil est excellent et nous serions ravis de vous accueillir.

[Instructions check-in automatiques]

Bien cordialement"""
        
        elif score["global_score"] >= 60:
            return f"""Bonjour {guest.name},

Merci pour votre demande. Pourriez-vous nous confirmer :
- Le nombre exact de voyageurs
- Le motif de votre séjour

Nous reviendrons vers vous rapidement.

Cordialement"""
        
        else:
            return f"""Bonjour {guest.name},

Merci pour votre intérêt. Suite à votre demande, nous aimerions en savoir plus :

- Pourriez-vous nous en dire plus sur vous et le motif de votre séjour ?
- Acceptez-vous notre règlement intérieur (pas de fête, respect des voisins) ?

Nous pourrons ensuite confirmer votre réservation.

Cordialement"""

# Exemple d'utilisation
if __name__ == "__main__":
    scorer = GuestScorer()
    
    # Exemple 1: Bon voyageur
    good_guest = GuestProfile(
        name="Marie Dupont",
        email="marie@example.com",
        reviews_count=15,
        reviews_rating=4.9,
        years_on_platform=3,
        message="Bonjour, je souhaite réserver pour un séjour professionnel. Merci !",
        check_in_date="2026-04-15",
        check_out_date="2026-04-20",
        guests_count=2
    )
    
    result = scorer.calculate_global_score(good_guest)
    
    print("🎯 SCORING CLIENT")
    print("=" * 50)
    print(f"Client: {result['guest_name']}")
    print(f"Score: {result['global_score']}/100")
    print(f"Catégorie: {result['category']}")
    print(f"Recommandation: {result['recommendation']}")
    print("\nDétails:")
    for category, data in result['details'].items():
        print(f"\n  {category.upper()}: {data['score']}/100")
        for note in data['notes']:
            print(f"    {note}")
    
    print("\n" + "=" * 50)
    print("\n💬 Réponse suggérée:")
    print(scorer.generate_response(good_guest, result))
