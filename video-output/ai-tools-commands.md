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
