import os, json, requests
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

BASE = "https://graph.instagram.com/v21.0"
TOKEN = os.environ["IG_ACCESS_TOKEN"]
USER_ID = os.environ["IG_USER_ID"]

def get(path, params=None):
    p = {"access_token": TOKEN, **(params or {})}
    r = requests.get(f"{BASE}/{path}", params=p)
    return r.json()

# --- 1. Info basica de la cuenta ---
me = get("me", {"fields": "username,followers_count,media_count"})
print(f"\n=== CUENTA ===")
print(f"@{me['username']} | {me['followers_count']} seguidores | {me['media_count']} posts")

# --- 2. Insights de cuenta (ultimos 30 dias) ---
print("\n=== INSIGHTS CUENTA (30d) ===")
since = int(datetime.now(timezone.utc).timestamp()) - 30 * 86400
until = int(datetime.now(timezone.utc).timestamp())
for metric in ["reach", "views", "follower_count", "profile_views", "accounts_engaged", "total_interactions"]:
    r = get(f"{USER_ID}/insights", {"metric": metric, "period": "day", "since": since, "until": until})
    if "error" in r:
        print(f"  {metric}: ERROR — {r['error']['message'][:80]}")
    elif "data" in r:
        vals = r["data"][0].get("values", []) if r["data"] else []
        total = sum(v.get("value", 0) for v in vals)
        recent = vals[-7:] if vals else []
        recent_total = sum(v.get("value", 0) for v in recent)
        print(f"  {metric}: {total} total 30d | {recent_total} ultimos 7d")

# --- 3. Ultimos 20 reels/posts con insights ---
print("\n=== MEDIA RECIENTE (likes | reach | views | saved | shares) ===")
media = get(f"{USER_ID}/media", {
    "fields": "id,timestamp,media_type,caption,like_count,comments_count",
    "limit": 20,
})

rows = []
if "data" in media:
    for item in media["data"]:
        mid = item["id"]
        ts = item.get("timestamp", "")[:10]
        caption = (item.get("caption") or "").split("\n")[0][:55]
        likes = item.get("like_count", 0)
        comments = item.get("comments_count", 0)

        ins = get(f"{mid}/insights", {"metric": "reach,views,saved,shares,total_interactions"})
        metrics = {}
        if "data" in ins:
            for m in ins["data"]:
                metrics[m["name"]] = m.get("value", 0)

        rows.append({
            "ts": ts,
            "caption": caption,
            "likes": likes,
            "comments": comments,
            "reach": metrics.get("reach", "?"),
            "views": metrics.get("views", "?"),
            "saved": metrics.get("saved", "?"),
            "shares": metrics.get("shares", "?"),
            "interactions": metrics.get("total_interactions", "?"),
        })

# Ordenar por likes desc para ver cuales pegaron
rows.sort(key=lambda x: x["likes"], reverse=True)

for r in rows:
    print(f"\n[{r['ts']}] {r['caption']!r}")
    print(f"  likes={r['likes']} comments={r['comments']} reach={r['reach']} views={r['views']} saved={r['saved']} shares={r['shares']}")

# --- 4. Analisis de patron de engagement ---
print("\n=== ANALISIS DE PATRON ===")
with_likes = [r for r in rows if isinstance(r["likes"], int)]
if with_likes:
    # Agrupar por semana aproximada
    high = [r for r in with_likes if r["likes"] >= 1000]
    mid = [r for r in with_likes if 200 <= r["likes"] < 1000]
    low = [r for r in with_likes if r["likes"] < 200]
    print(f"  Alto (1k+ likes): {len(high)} videos")
    for r in high:
        print(f"    [{r['ts']}] {r['likes']} likes — {r['caption'][:50]}")
    print(f"  Medio (200-1k): {len(mid)} videos")
    print(f"  Bajo (<200): {len(low)} videos")

    avg_likes = sum(r["likes"] for r in with_likes) / len(with_likes)
    print(f"\n  Promedio likes (ultimos {len(with_likes)} posts): {avg_likes:.0f}")

    # Ver tendencia cronologica (los ultimos 7 vs anteriores)
    recent_7 = sorted(with_likes, key=lambda x: x["ts"], reverse=True)[:7]
    older = sorted(with_likes, key=lambda x: x["ts"], reverse=True)[7:]
    if recent_7 and older:
        avg_recent = sum(r["likes"] for r in recent_7) / len(recent_7)
        avg_older = sum(r["likes"] for r in older) / len(older)
        print(f"\n  Promedio likes ultimos 7 posts: {avg_recent:.0f}")
        print(f"  Promedio likes 7 posts anteriores: {avg_older:.0f}")
        delta = ((avg_recent - avg_older) / avg_older) * 100
        trend = "SUBE" if delta > 0 else "BAJA"
        print(f"  Tendencia: {trend} ({delta:+.0f}%)")

# --- 5. Demograficos si disponible ---
print("\n=== DEMOGRAFIA ===")
for metric in ["follower_demographics", "reached_audience_demographics"]:
    r = get(f"{USER_ID}/insights", {"metric": metric, "period": "lifetime", "timeframe": "this_month", "breakdown": "country"})
    if "error" in r:
        print(f"  {metric}: necesita periodo correcto — probando...")
    elif "data" in r:
        print(f"\n  {metric}:")
        print(json.dumps(r["data"][:3], indent=4, ensure_ascii=False))

# Fallback demografia
r = get(f"{USER_ID}/insights", {"metric": "follower_demographics", "period": "lifetime", "breakdown": "country", "timeframe": "this_month"})
if "data" in r:
    print(json.dumps(r, indent=2, ensure_ascii=False))
else:
    print(f"  follower_demographics error: {r.get('error', {}).get('message', '')[:100]}")
