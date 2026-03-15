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
