"""
Agent Airbnb propulsé par Claude.
Gère toutes les demandes et réservations de manière autonome.
"""
import json
import anthropic
import config as cfg
from tools import TOOL_FUNCTIONS

client = anthropic.Anthropic(api_key=cfg.ANTHROPIC_API_KEY)

# Définition des outils pour Claude
TOOLS = [
    {
        "name": "calculate_price",
        "description": "Calcule le prix total pour un séjour incluant réductions et frais de ménage.",
        "input_schema": {
            "type": "object",
            "properties": {
                "check_in": {"type": "string", "description": "Date d'arrivée (YYYY-MM-DD)"},
                "check_out": {"type": "string", "description": "Date de départ (YYYY-MM-DD)"},
                "num_guests": {"type": "integer", "description": "Nombre de voyageurs"},
            },
            "required": ["check_in", "check_out"],
        },
    },
    {
        "name": "check_availability",
        "description": "Vérifie si les dates demandées sont disponibles pour une réservation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "check_in": {"type": "string", "description": "Date d'arrivée (YYYY-MM-DD)"},
                "check_out": {"type": "string", "description": "Date de départ (YYYY-MM-DD)"},
            },
            "required": ["check_in", "check_out"],
        },
    },
    {
        "name": "create_reservation",
        "description": "Crée et confirme une nouvelle réservation. Planifie automatiquement les messages et rappels.",
        "input_schema": {
            "type": "object",
            "properties": {
                "guest_name": {"type": "string", "description": "Nom complet du voyageur"},
                "check_in": {"type": "string", "description": "Date d'arrivée (YYYY-MM-DD)"},
                "check_out": {"type": "string", "description": "Date de départ (YYYY-MM-DD)"},
                "num_guests": {"type": "integer", "description": "Nombre de voyageurs"},
                "guest_email": {"type": "string", "description": "Email du voyageur (optionnel)"},
                "platform": {"type": "string", "description": "Plateforme (airbnb, booking, direct)", "default": "airbnb"},
                "notes": {"type": "string", "description": "Notes supplémentaires"},
            },
            "required": ["guest_name", "check_in", "check_out", "num_guests"],
        },
    },
    {
        "name": "get_reservation",
        "description": "Récupère tous les détails d'une réservation spécifique incluant l'historique des messages.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reservation_id": {"type": "string", "description": "ID de la réservation"},
            },
            "required": ["reservation_id"],
        },
    },
    {
        "name": "list_reservations",
        "description": "Liste les réservations selon leur statut et période.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "Filtre par statut: confirmed, pending, cancelled, completed"},
                "period": {"type": "string", "description": "Période: upcoming (défaut), past, all"},
            },
        },
    },
    {
        "name": "update_reservation",
        "description": "Met à jour le statut d'une réservation (confirmer, annuler, rejeter, compléter).",
        "input_schema": {
            "type": "object",
            "properties": {
                "reservation_id": {"type": "string", "description": "ID de la réservation"},
                "status": {"type": "string", "description": "Nouveau statut: confirmed, cancelled, rejected, completed"},
                "notes": {"type": "string", "description": "Notes sur le changement de statut"},
            },
            "required": ["reservation_id", "status"],
        },
    },
    {
        "name": "block_dates",
        "description": "Bloque des dates sur le calendrier (maintenance, usage personnel, travaux, etc.).",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "Début du blocage (YYYY-MM-DD)"},
                "end_date": {"type": "string", "description": "Fin du blocage (YYYY-MM-DD)"},
                "reason": {"type": "string", "description": "Raison du blocage"},
            },
            "required": ["start_date", "end_date"],
        },
    },
    {
        "name": "get_calendar",
        "description": "Affiche le calendrier de disponibilité avec réservations et blocages.",
        "input_schema": {
            "type": "object",
            "properties": {
                "month": {"type": "string", "description": "Mois à afficher (YYYY-MM). Défaut: 90 prochains jours"},
            },
        },
    },
    {
        "name": "generate_message",
        "description": "Génère automatiquement un message pour un voyageur selon le type de communication.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message_type": {
                    "type": "string",
                    "description": "Type: welcome, check_in_instructions, mid_stay, checkout_reminder, review_request, custom",
                },
                "reservation_id": {"type": "string", "description": "ID de la réservation"},
                "custom_context": {"type": "string", "description": "Contexte additionnel pour les messages personnalisés"},
            },
            "required": ["message_type", "reservation_id"],
        },
    },
    {
        "name": "log_incoming_message",
        "description": "Enregistre un message reçu d'un voyageur dans l'historique.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reservation_id": {"type": "string", "description": "ID de la réservation"},
                "content": {"type": "string", "description": "Contenu du message reçu"},
            },
            "required": ["reservation_id", "content"],
        },
    },
    {
        "name": "add_review",
        "description": "Enregistre l'avis et la note d'un voyageur après son séjour.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reservation_id": {"type": "string", "description": "ID de la réservation"},
                "rating": {"type": "number", "description": "Note de 1 à 5"},
                "comment": {"type": "string", "description": "Commentaire du voyageur"},
            },
            "required": ["reservation_id", "rating", "comment"],
        },
    },
    {
        "name": "get_stats",
        "description": "Retourne les statistiques globales: revenus, taux d'occupation, note moyenne, réservations.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_pending_tasks",
        "description": "Récupère les tâches automatiques en attente (messages à envoyer, rappels, suivis).",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "complete_task",
        "description": "Marque une tâche automatique comme terminée.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer", "description": "ID de la tâche"},
            },
            "required": ["task_id"],
        },
    },
]

SYSTEM_PROMPT = f"""Tu es un agent Airbnb intelligent et autonome qui gère la propriété "{cfg.PROPERTY_NAME}" pour l'hôte {cfg.HOST_NAME}.

Tu gères de manière AUTONOME et PROACTIVE :
- Les demandes de réservation (vérification disponibilité, prix, confirmation)
- Les communications avec les voyageurs (messages de bienvenue, instructions, rappels)
- Le calendrier et les blocages de dates
- Le suivi des tâches automatiques (rappels check-in/check-out, demandes d'avis)
- Les statistiques et la performance de la propriété

INFORMATIONS DE LA PROPRIÉTÉ :
- Nom : {cfg.PROPERTY_NAME}
- Prix par nuit : {cfg.DEFAULT_PRICE_PER_NIGHT}€
- Frais de ménage : {cfg.CLEANING_FEE}€
- Réduction semaine : {int(cfg.WEEKLY_DISCOUNT*100)}%
- Réduction mois : {int(cfg.MONTHLY_DISCOUNT*100)}%
- Max voyageurs : {cfg.MAX_GUESTS}
- Nuits minimum : {cfg.MIN_NIGHTS}
- Check-in : {cfg.CHECK_IN_TIME}
- Check-out : {cfg.CHECK_OUT_TIME}

RÈGLES DE LA MAISON :
{cfg.HOUSE_RULES}

COMPORTEMENT :
- Réponds toujours en français
- Sois professionnel, chaleureux et efficace
- Utilise les outils disponibles pour effectuer toutes les actions nécessaires
- Pour chaque demande, vérifie automatiquement disponibilité ET prix
- Génère proactivement les messages appropriés
- Informe l'hôte de tout ce que tu fais
- Si une demande est ambiguë, fais des suppositions raisonnables et explique-les
- Pour les nouvelles réservations, planifie automatiquement tous les messages de suivi

Date et heure actuelles : {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}
"""


class AirbnbAgent:
    def __init__(self):
        self.conversation_history = []

    def reset(self):
        self.conversation_history = []

    def run(self, user_message: str, verbose: bool = False) -> str:
        """Traite un message et retourne la réponse de l'agent."""
        self.conversation_history.append({"role": "user", "content": user_message})

        while True:
            response = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=self.conversation_history,
            )

            if verbose:
                print(f"  [stop_reason: {response.stop_reason}]")

            # Collecter les blocs de contenu
            tool_uses = []
            text_parts = []

            for block in response.content:
                if block.type == "tool_use":
                    tool_uses.append(block)
                elif block.type == "text":
                    text_parts.append(block.text)

            # Ajouter la réponse de l'assistant à l'historique
            self.conversation_history.append({"role": "assistant", "content": response.content})

            # Si pas d'appels d'outils → réponse finale
            if response.stop_reason == "end_turn" or not tool_uses:
                return "\n".join(text_parts)

            # Exécuter les outils
            tool_results = []
            for tool_use in tool_uses:
                fn_name = tool_use.name
                fn_args = tool_use.input

                if verbose:
                    print(f"  [outil: {fn_name}({json.dumps(fn_args, ensure_ascii=False)})]")

                fn = TOOL_FUNCTIONS.get(fn_name)
                if fn:
                    try:
                        result = fn(**fn_args)
                    except Exception as e:
                        result = {"error": str(e)}
                else:
                    result = {"error": f"Outil inconnu: {fn_name}"}

                if verbose:
                    print(f"  [résultat: {json.dumps(result, ensure_ascii=False)[:200]}]")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })

            # Ajouter les résultats dans l'historique
            self.conversation_history.append({"role": "user", "content": tool_results})
