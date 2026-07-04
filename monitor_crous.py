import requests
import json
import os
import time

# ─── CONFIG ────────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
SEEN_FILE = "seen_ids.json"

# CROUS d'Île-de-France : Paris (21), Créteil (10), Versailles (38)
CROUS_IDS = {
    "Paris": 21,
    "Créteil": 10,
    "Versailles": 38,
}

# ─── CHARGER / SAUVEGARDER LES IDs DÉJÀ VUES ───────────────────────────────
def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

# ─── RÉCUPÉRER LES ANNONCES ─────────────────────────────────────────────────
def fetch_listings(crous_name, crous_id):
    url = f"https://trouverunlogement.lescrous.fr/api/fr/search/{crous_id}"
    params = {
        "page": 1,
        "per_page": 50,
    }
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    try:
        r = requests.get(url, params=params, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        items = data.get("data", {}).get("data", []) or data.get("data", []) or []
        return items
    except Exception as e:
        print(f"[{crous_name}] Erreur: {e}")
        return []

# ─── ENVOYER UN MESSAGE TELEGRAM ────────────────────────────────────────────
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"Erreur Telegram: {e}")

# ─── FORMATER UNE ANNONCE ────────────────────────────────────────────────────
def format_listing(item, crous_name):
    title = item.get("title") or item.get("name") or "Logement CROUS"
    price = item.get("price") or item.get("rent") or "N/A"
    city = item.get("city") or item.get("town") or crous_name
    area = item.get("area") or item.get("surface") or "N/A"
    slug = item.get("slug") or item.get("id") or ""
    link = f"https://trouverunlogement.lescrous.fr/logements/{slug}" if slug else "https://trouverunlogement.lescrous.fr"

    return (
        f"🏠 <b>Nouvelle annonce CROUS {crous_name} !</b>\n\n"
        f"📍 <b>Ville :</b> {city}\n"
        f"🏷️ <b>Type :</b> {title}\n"
        f"📐 <b>Surface :</b> {area} m²\n"
        f"💶 <b>Prix :</b> {price} €/mois\n\n"
        f"🔗 <a href='{link}'>Voir l'annonce</a>"
    )

# ─── MAIN ────────────────────────────────────────────────────────────────────
def main():
    seen = load_seen()
    new_count = 0

    for crous_name, crous_id in CROUS_IDS.items():
        listings = fetch_listings(crous_name, crous_id)
        print(f"[{crous_name}] {len(listings)} annonces trouvées")

        for item in listings:
            item_id = str(item.get("id") or item.get("slug") or "")
            if not item_id or item_id in seen:
                continue

            # Nouvelle annonce !
            seen.add(item_id)
            new_count += 1
            message = format_listing(item, crous_name)
            send_telegram(message)
            print(f"  → Nouvelle annonce envoyée : {item_id}")
            time.sleep(0.5)  # éviter le spam

    if new_count == 0:
        print("Aucune nouvelle annonce.")

    save_seen(seen)

if __name__ == "__main__":
    main()
