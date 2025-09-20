import os
import json
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv

BASE = "https://api.sendpulse.com"
OUT_DIR = "/app/out"
os.makedirs(OUT_DIR, exist_ok=True)

load_dotenv()
CLIENT_ID = os.getenv("SP_CLIENT_ID")
CLIENT_SECRET = os.getenv("SP_CLIENT_SECRET")
BOT_ID = os.getenv("SP_BOT_ID")  # opcional: si no está, autodetectamos el primero
SINCE = os.getenv("SINCE")
UNTIL = os.getenv("UNTIL")
DEBUG = os.getenv("DEBUG", "0") == "1"

# -------------------- OAuth --------------------
def get_token():
    if not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError("SP_CLIENT_ID / SP_CLIENT_SECRET no están definidos.")
    url = f"{BASE}/oauth/access_token"

    # 1) x-www-form-urlencoded
    r = requests.post(
        url,
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    if r.status_code == 200:
        return r.json()["access_token"]

    # 2) JSON fallback
    r2 = requests.post(
        url,
        json={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        timeout=30,
    )
    if r2.status_code == 200:
        return r2.json()["access_token"]

    try:
        body = r2.json()
    except Exception:
        body = r2.text
    raise requests.HTTPError(f"Token error. Status={r2.status_code}. Body={body}", response=r2)

def sp_get(url, token, params=None):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers, params=params or {}, timeout=30)
    if r.status_code >= 400:
        try:
            body = r.json()
        except Exception:
            body = r.text
        raise requests.HTTPError(f"{r.status_code} GET {url} params={params} body={body}", response=r)
    return r.json()

# -------------------- Descubrimiento --------------------
def list_bots(token):
    # WhatsApp bots
    data = sp_get(f"{BASE}/whatsapp/bots", token)
    return data.get("data", data) if isinstance(data, dict) else data

def discover_chats_endpoint(token, bot_id):
    """
    Intenta descubrir qué endpoint de 'chats/conversations' existe en tu cuenta.
    Devuelve (endpoint_url, uses_bot_in_path: bool, supports_dates: bool)
    """
    candidates = [
        # 1) WhatsApp por bot (variante A)
        (f"{BASE}/whatsapp/bots/{bot_id}/chats", True, True),
        # 2) WhatsApp global (variante B)
        (f"{BASE}/whatsapp/chats", False, True),
        # 3) Chatbots (genérico) con canal por query
        (f"{BASE}/chatbots/chats", False, True),
        # 4) Live-chat (genérico)
        (f"{BASE}/livechat/chats", False, True),
        # 5) Chatbots por bot (algunas cuentas)
        (f"{BASE}/chatbots/bots/{bot_id}/chats", True, True),
        # 6) Conversations genérico (algunas cuentas)
        (f"{BASE}/chatbots/conversations", False, True),
    ]

    params_base = {"limit": 1, "offset": 0}
    if SINCE: params_base["date_from"] = SINCE
    if UNTIL: params_base["date_to"] = UNTIL

    tried = []
    for url, needs_bot, supports_dates in candidates:
        try:
            params = dict(params_base)
            if "chatbots/chats" in url:
                # algunos requieren channel=whatsapp
                params["channel"] = "whatsapp"
            data = sp_get(url, token, params)
            items = data.get("data", data)
            if not isinstance(items, list):
                items = items.get("items", [])
            # si no revienta y devuelve estructura lista o vacía, lo damos por válido
            return (url, needs_bot, supports_dates)
        except requests.HTTPError as e:
            tried.append(str(e))

    raise RuntimeError("No encontré un endpoint de 'chats' válido en tu cuenta. Intentos:\n- " + "\n- ".join(tried))

def discover_messages_endpoint(token, bot_id, chat_id):
    """
    Intenta descubrir qué endpoint de mensajes por chat existe.
    Devuelve endpoint pattern con placeholders: pattern.format(bot_id=..., chat_id=...)
    """
    candidates = [
        f"{BASE}/whatsapp/bots/{{bot_id}}/chats/{{chat_id}}/messages",
        f"{BASE}/whatsapp/chats/{{chat_id}}/messages",
        f"{BASE}/chatbots/chats/messages",                    # ?chat_id=...
        f"{BASE}/chatbots/chats/{{chat_id}}/messages",
        f"{BASE}/livechat/chats/{{chat_id}}/messages",
        f"{BASE}/chatbots/conversations/{{chat_id}}/messages",
    ]

    params = {"limit": 1}
    if SINCE: params["since"] = SINCE
    if UNTIL: params["until"] = UNTIL

    tried = []
    for pattern in candidates:
        url = pattern.format(bot_id=bot_id, chat_id=chat_id)
        try:
            # para el caso de .../chats/messages con query chat_id
            eff_params = dict(params)
            if url.endswith("/chats/messages"):
                eff_params["chat_id"] = chat_id
            data = sp_get(url, token, eff_params)
            # si llega aquí, el endpoint existe
            return pattern
        except requests.HTTPError as e:
            tried.append(str(e))
    raise RuntimeError("No encontré un endpoint de 'messages' válido. Intentos:\n- " + "\n- ".join(tried))

# -------------------- Lógica de negocio --------------------
POS = ["gracias","excelente","perfecto","genial","buen","funcionó","funciono",
       "rápido","rapido","me ayudaron","amable","solución","solucion"]
NEG = ["mal","tarde","no sirve","no sirvio","no funcionó","no funciono","problema",
       "queja","molesto","reclamo","pésimo","pesimo","lento","cancelar"]

def rule_sentiment_es(text: str) -> int:
    if not text:
        return 0
    t = text.lower()
    score = 0
    for w in POS:
        if w in t: score += 1
    for w in NEG:
        if w in t: score -= 1
    return score

def main():
    print("SP_CLIENT_ID:", (CLIENT_ID or "")[:4] + "…")
    print("SP_CLIENT_SECRET:", (CLIENT_SECRET or "")[:4] + "…")

    token = get_token()

    # Resolver bot_id (si no vino por env)
    bot_id = BOT_ID
    if not bot_id:
        bots = list_bots(token)
        if not bots:
            raise RuntimeError("No hay bots de WhatsApp en esta cuenta.")
        bot = bots[0]
        bot_id = bot.get("id") or bot.get("bot_id") or bot.get("botId")
        print("Usando BOT_ID detectado:", (bot_id or "")[:4] + "…")

    # Descubrir endpoint para CHATS
    print("→ Descubriendo endpoint de CHATS…")
    chats_url, _, _ = discover_chats_endpoint(token, bot_id)
    print(f"   CHATS endpoint: {chats_url}")

    # Traer CHATS
    print("→ Descargando chats…")
    all_chats, offset, limit = [], 0, 2000
    while offset < limit:
        params = {"limit": min(200, limit - offset), "offset": offset}
        if "chatbots/chats" in chats_url:
            params["channel"] = "whatsapp"
        if SINCE: params["date_from"] = SINCE
        if UNTIL: params["date_to"] = UNTIL
        data = sp_get(chats_url, token, params)
        items = data.get("data", data)
        if not isinstance(items, list):
            items = items.get("items", [])
        if not items:
            break
        all_chats.extend(items)
        offset += len(items)
    print(f"   {len(all_chats)} chats")

    if DEBUG:
        with open(os.path.join(OUT_DIR, "debug.chats_url.txt"), "w") as f:
            f.write(chats_url + "\n")

    # Necesitamos al menos un chat_id para descubrir endpoint de mensajes
    sample_chat_id = None
    for ch in all_chats:
        sample_chat_id = ch.get("id") or ch.get("chat_id") or ch.get("chatId")
        if sample_chat_id:
            break

    if not sample_chat_id:
        # Igual guardamos los chats crudos
        with open(os.path.join(OUT_DIR, "chats.raw.json"), "w", encoding="utf-8") as f:
            json.dump(all_chats, f, ensure_ascii=False, indent=2)
        print("No se encontraron chats (o no hay chat_id). Termino.")
        return

    # Descubrir endpoint para MENSAJES
    print("→ Descubriendo endpoint de MENSAJES…")
    msg_pattern = discover_messages_endpoint(token, bot_id, sample_chat_id)
    print(f"   MESSAGES endpoint pattern: {msg_pattern}")
    if DEBUG:
        with open(os.path.join(OUT_DIR, "debug.messages_url.txt"), "w") as f:
            f.write(msg_pattern + "\n")

    # Bajar mensajes por chat
    rows = []
    for ch in all_chats:
        chat_id = ch.get("id") or ch.get("chat_id") or ch.get("chatId")
        if not chat_id:
            continue
        url = msg_pattern.format(bot_id=bot_id, chat_id=chat_id)
        params = {"limit": 200}
        if url.endswith("/chats/messages"):
            params["chat_id"] = chat_id
        if SINCE: params["since"] = SINCE
        if UNTIL: params["until"] = UNTIL

        try:
            data = sp_get(url, token, params)
        except requests.HTTPError as e:
            if DEBUG:
                print(f"[WARN] No pude leer mensajes de chat {chat_id}: {e}")
            continue

        msgs = data.get("data", data)
        msgs = msgs if isinstance(msgs, list) else msgs.get("items", [])
        for m in msgs:
            text = m.get("text") or (m.get("message") or {}).get("text") or m.get("caption") or ""
            ts = m.get("timestamp") or m.get("created_at") or m.get("createdAt")
            direction = m.get("direction") or m.get("type") or "unknown"
            contact_id = ch.get("contact_id") or ch.get("contactId") or m.get("contact_id") or m.get("contactId")
            senti = rule_sentiment_es(text)
            rows.append({
                "chatId": chat_id,
                "contactId": contact_id,
                "direction": direction,
                "timestamp": ts,
                "text": text,
                "sentiment": senti
            })

    # Guardados
    with open(os.path.join(OUT_DIR, "chats.raw.json"), "w", encoding="utf-8") as f:
        json.dump(all_chats, f, ensure_ascii=False, indent=2)
    with open(os.path.join(OUT_DIR, "messages.raw.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    if not rows:
        print("No se obtuvieron mensajes (pero guardé chats.raw.json).")
        return

    df = pd.DataFrame(rows)
    grouped = df.groupby("chatId")["sentiment"].agg(["count", "mean"]).reset_index()
    grouped = grouped.rename(columns={"count": "msgs", "mean": "avg_sentiment"})
    grouped.to_csv(os.path.join(OUT_DIR, "summary_by_chat.csv"), index=False, encoding="utf-8")

    sentiments = df["sentiment"].to_numpy(dtype=float)

    plt.figure()
    plt.hist(sentiments, bins=np.arange(np.min(sentiments)-0.5, np.max(sentiments)+1.5, 1))
    plt.title("Histograma de sentimiento (heurístico)")
    plt.xlabel("Sentimiento (-, 0, +)")
    plt.ylabel("Frecuencia")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "hist_sentimiento.png"), dpi=144)

    top = grouped.sort_values(["msgs", "avg_sentiment"], ascending=[False, False]).head(15)
    plt.figure()
    plt.bar(top["chatId"].astype(str), top["avg_sentiment"])
    plt.title("Promedio de sentimiento por chat (Top 15 por volumen)")
    plt.xlabel("chatId")
    plt.ylabel("Promedio sentimiento")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "avg_sentimiento_top_chats.png"), dpi=144)

    print("Listo ✅ Archivos en", OUT_DIR)

if __name__ == "__main__":
    main()
