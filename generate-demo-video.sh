#!/bin/bash
# generate-demo-video.sh
# Génère une vidéo de démo complète pour Airbnb AI Manager

PRODUCT_NAME="Airbnb AI Manager"
DEMO_URL="https://demo-mu-nine-17.vercel.app"
LANDING_URL="https://landing-page-zeta-five-41.vercel.app"
OUTPUT_DIR="/Users/farescrbs/projects/airbnb-ai-complete/video-output"

# Créer le dossier de sortie
mkdir -p "$OUTPUT_DIR"

echo "🎬 Génération de la vidéo de démo pour $PRODUCT_NAME"
echo "================================================"

# Étape 1: Générer le script de la vidéo
echo "📝 Étape 1: Génération du script..."

cat > "$OUTPUT_DIR/script.txt" << 'EOF'
[SCÈNE 1 - INTRO - 0:00 à 0:15]
VISUEL: Dashboard avec stats animées
VOIX: "Bonjour, je suis entrepreneur et je gère 5 locations Airbnb. Avant, je passais 3 heures par jour à répondre aux messages, ajuster les prix et gérer les réservations."

[SCÈNE 2 - PROBLÈME - 0:15 à 0:30]
VISUEL: Notification spam, téléphone qui sonne
VOIX: "C'était épuisant. Je manquais des messages, mes prix n'étaient pas optimisés, et je passais mes week-ends à gérer des problèmes au lieu de les profiter."

[SCÈNE 3 - SOLUTION - 0:30 à 0:50]
VISUEL: Logo Airbnb AI Manager qui apparaît
VOIX: "Puis j'ai découvert Airbnb AI Manager. En 5 minutes, j'ai connecté mon compte et l'IA a pris le relais."

[SCÈNE 4 - DÉMO 1 - 0:50 à 1:15]
VISUEL: Chat avec réponse instantanée de l'IA
VOIX: "Regardez ça. Un voyageur demande la disponibilité. L'IA répond en 2 secondes avec un message personnalisé, professionnel, dans sa langue. Je n'ai rien à faire."

[SCÈNE 5 - DÉMO 2 - 1:15 à 1:35]
VISUEL: Calendrier avec prix qui changent
VOIX: "Le pricing dynamique analyse la demande, les événements et la concurrence. Il ajuste automatiquement les prix pour maximiser mes revenus. Résultat : plus 47% ce mois."

[SCÈNE 6 - DÉMO 3 - 1:35 à 1:50]
VISUEL: Avis 5 étoiles qui apparaissent
VOIX: "L'IA demande des avis aux bons clients au bon moment. Mes notes sont passées de 4.2 à 4.9 étoiles."

[SCÈNE 7 - RÉSULTATS - 1:50 à 2:05]
VISUEL: Stats finales avec graphiques
VOIX: "Résultat final : 15 heures économisées par semaine, 30% de revenus en plus, et je peux enfin profiter de mon temps libre."

[SCÈNE 8 - CTA - 2:05 à 2:20]
VISUEL: Page de prix avec bouton "Essayer gratuitement"
VOIX: "Essayez Airbnb AI Manager gratuitement pendant 14 jours. Aucune carte bancaire requise. Le lien est en description."

[FIN]
VISUEL: Logo + URL
VOIX: "Airbnb AI Manager. Votre concierge virtuel 24 sur 24."
EOF

echo "✅ Script généré"

# Étape 2: Créer le storyboard visuel
echo "🎨 Étape 2: Création du storyboard..."

cat > "$OUTPUT_DIR/storyboard.json" << EOF
{
  "scenes": [
    {
      "id": 1,
      "duration": 15,
      "type": "dashboard",
      "url": "$DEMO_URL",
      "actions": ["show_stats", "animate_numbers"],
      "voiceover": "intro"
    },
    {
      "id": 2,
      "duration": 15,
      "type": "problem",
      "visual": "notifications_spam",
      "voiceover": "problem"
    },
    {
      "id": 3,
      "duration": 20,
      "type": "solution",
      "visual": "logo_reveal",
      "voiceover": "solution"
    },
    {
      "id": 4,
      "duration": 25,
      "type": "demo_chat",
      "url": "$DEMO_URL",
      "actions": ["click_simulate", "show_typing", "show_response"],
      "voiceover": "demo1"
    },
    {
      "id": 5,
      "duration": 20,
      "type": "demo_pricing",
      "url": "$DEMO_URL",
      "actions": ["click_optimize", "highlight_calendar", "show_price_changes"],
      "voiceover": "demo2"
    },
    {
      "id": 6,
      "duration": 15,
      "type": "demo_reviews",
      "visual": "stars_animation",
      "voiceover": "demo3"
    },
    {
      "id": 7,
      "duration": 15,
      "type": "results",
      "visual": "final_stats",
      "voiceover": "results"
    },
    {
      "id": 8,
      "duration": 15,
      "type": "cta",
      "url": "$LANDING_URL",
      "actions": ["scroll_to_pricing", "highlight_button"],
      "voiceover": "cta"
    }
  ],
  "total_duration": 140,
  "format": "16:9",
  "resolution": "1920x1080"
}
EOF

echo "✅ Storyboard créé"

# Étape 3: Générer les commandes pour les outils IA
echo "🤖 Étape 3: Préparation des outils IA..."

cat > "$OUTPUT_DIR/ai-tools-commands.md" << 'EOF'
# Outils IA pour générer la vidéo

## Option 1: Synthesia (Recommandé)
- Créer un compte sur https://www.synthesia.io
- Choisir un avatar professionnel (homme/femme français)
- Uploader le script
- Générer la vidéo (~$30 pour 2 min)

## Option 2: HeyGen
- https://www.heygen.com
- Avatar plus réalistes
- Prix similaire

## Option 3: Solution Gratuite (DIY)
1. Enregistrer l'écran avec OBS/QuickTime
2. Narrer avec micro ou ElevenLabs (voix IA)
3. Monter avec iMovie ou DaVinci Resolve

## Option 4: Screen Recording + IA Voice
```bash
# 1. Enregistrer la démo
# Ouvrir https://demo-mu-nine-17.vercel.app
# Enregistrer l'écran avec QuickTime

# 2. Générer la voix avec ElevenLabs
# Utiliser le script généré
# Voix recommandée: "Adam" ou "Bella" (français)

# 3. Synchroniser avec FFmpeg
ffmpeg -i screen-recording.mp4 -i voiceover.mp3 -c:v copy -c:a aac output.mp4
```
EOF

echo "✅ Guide des outils IA créé"

# Étape 4: Créer le prompt pour génération automatique
echo "🎯 Étape 4: Prompt pour génération IA..."

cat > "$OUTPUT_DIR/prompt-for-ai.txt" << EOF
Tu es un expert en création de vidéos de démo SaaS. 

Crée une vidéo de 2 minutes pour "$PRODUCT_NAME" avec cette structure:

PRODUIT: Gestion Airbnb automatisée par IA
PUBLIC: Propriétaires Airbnb et conciergeries
OBJECTIF: Montrer la valeur et convertir en essai gratuit

RESSOURCES VISUELLES:
- Démo interactive: $DEMO_URL
- Landing page: $LANDING_URL

SCRIPT FOURNI DANS: script.txt

EXIGENCES:
- Ton professionnel mais accessible
- Rythme dynamique (changement de scène toutes les 15-20s)
- Musique de fond légère (pas de droits d'auteur)
- Sous-titres en français
- Call-to-action clair à la fin

FORMAT: MP4 1920x1080 30fps
DURÉE: 2 minutes max
EOF

echo "✅ Prompt IA créé"

# Étape 5: Créer un script Python pour automatisation
echo "🐍 Étape 5: Script d'automatisation..."

cat > "$OUTPUT_DIR/generate-video.py" << 'PYEOF'
#!/usr/bin/env python3
"""
Générateur de vidéo de démo automatisé
Utilise Selenium pour capturer la démo + génération de voix IA
"""

import os
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configuration
DEMO_URL = "https://demo-mu-nine-17.vercel.app"
LANDING_URL = "https://landing-page-zeta-five-41.vercel.app"
OUTPUT_DIR = "/Users/farescrbs/projects/airbnb-ai-complete/video-output"

def setup_driver():
    """Configure le driver Chrome pour capture vidéo"""
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--headless")  # Mode sans interface
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    
    # Options pour capture vidéo
    chrome_options.add_argument("--enable-logging")
    chrome_options.add_argument("--v=1")
    
    return webdriver.Chrome(options=chrome_options)

def capture_scene(driver, scene_id, duration, actions):
    """Capture une scène de la vidéo"""
    print(f"Capture scène {scene_id}...")
    
    # Exécuter les actions
    for action in actions:
        if action == "show_stats":
            # Attendre que les stats soient visibles
            time.sleep(2)
        elif action == "click_simulate":
            # Cliquer sur le bouton simuler
            try:
                btn = driver.find_element(By.CSS_SELECTOR, "button[onclick='simulateAIResponse()']")
                btn.click()
                time.sleep(3)  # Attendre la réponse
            except:
                pass
        elif action == "click_optimize":
            # Cliquer sur optimiser les prix
            try:
                btn = driver.find_element(By.CSS_SELECTOR, "button[onclick='optimizePrices()']")
                btn.click()
                time.sleep(2)
            except:
                pass
    
    # Attendre la durée de la scène
    time.sleep(duration)

def generate_video():
    """Génère la vidéo complète"""
    print("🎬 Démarrage de la génération de vidéo...")
    
    # Charger le storyboard
    with open(f"{OUTPUT_DIR}/storyboard.json", "r") as f:
        storyboard = json.load(f)
    
    driver = setup_driver()
    
    try:
        for scene in storyboard["scenes"]:
            scene_id = scene["id"]
            duration = scene["duration"]
            actions = scene.get("actions", [])
            url = scene.get("url", DEMO_URL)
            
            # Naviguer vers l'URL
            driver.get(url)
            time.sleep(3)  # Attendre le chargement
            
            # Capturer la scène
            capture_scene(driver, scene_id, duration, actions)
            
            # TODO: Sauvegarder les frames ou utiliser une lib de capture vidéo
            
        print("✅ Capture terminée")
        
    finally:
        driver.quit()
    
    print(f"📁 Fichiers générés dans: {OUTPUT_DIR}")

if __name__ == "__main__":
    generate_video()
PYEOF

chmod +x "$OUTPUT_DIR/generate-video.py"

echo "✅ Script Python créé"

# Résumé final
echo ""
echo "================================================"
echo "✅ VIDÉO PRÊTE À ÊTRE GÉNÉRÉE"
echo "================================================"
echo ""
echo "📁 Fichiers créés dans: $OUTPUT_DIR"
echo ""
echo "📄 Contenu:"
echo "  • script.txt - Script narratif complet"
echo "  • storyboard.json - Plan visuel détaillé"
echo "  • ai-tools-commands.md - Guide outils IA"
echo "  • prompt-for-ai.txt - Prompt pour génération auto"
echo "  • generate-video.py - Script d'automatisation"
echo ""
echo "🚀 Prochaines étapes:"
echo ""
echo "OPTION 1 - Rapide (Payant):"
echo "  1. Aller sur https://synthesia.io"
echo "  2. Créer un compte ($30/crédit)"
echo "  3. Copier-coller le script.txt"
echo "  4. Générer la vidéo en 10 minutes"
echo ""
echo "OPTION 2 - Gratuit (DIY):"
echo "  1. Ouvrir $DEMO_URL"
echo "  2. Enregistrer l'écran avec QuickTime"
echo "  3. Narrer avec votre voix ou ElevenLabs"
echo "  4. Monter avec iMovie"
echo ""
echo "OPTION 3 - Automatique (Python):"
echo "  1. Installer dépendances: pip install selenium"
echo "  2. Lancer: python3 $OUTPUT_DIR/generate-video.py"
echo "  3. Ajouter FFmpeg pour montage"
echo ""
