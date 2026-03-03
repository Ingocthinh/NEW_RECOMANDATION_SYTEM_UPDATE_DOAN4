import sys
import requests
import json
import time
import sqlite3

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

base_url = "http://127.0.0.1:5000"
user_id = "vinh113"

def get_recs(msg):
    print(f"\n--- {msg} ---")
    try:
        resp = requests.get(f"{base_url}/recommend/{user_id}?top_n=10")
        recs = resp.json()
        cats = {}
        for i, r in enumerate(recs):
            print(f"{i+1}. {r['title']} | Score: {r['score']} | Cat: {r['category']}")
            cats[r['category']] = cats.get(r['category'], 0) + 1
        print(f"Category Distribution: {dict(cats)}")
        return recs
    except Exception as e:
        print(f"Error: {e}")
        return []

# 1. Initial
get_recs("Initial Recommendations (Cold Start)")

# 2. Find target news IDs (Kinh doanh or any other)
conn = sqlite3.connect('I:\\newrecomandationsystem\\data\\news.db')
cur = conn.cursor()
cur.execute("SELECT id, category FROM News WHERE category = 'Kinh doanh' LIMIT 3")
rows = cur.fetchall()
target_ids = [f"db_{r[0]}" for r in rows]
conn.close()

if not target_ids:
    print("Could not find 'Kinh doanh' news in DB, trying 'Thể thao'...")
    # fallback
    conn = sqlite3.connect('I:\\newrecomandationsystem\\data\\news.db')
    cur = conn.cursor()
    cur.execute("SELECT id, category FROM News WHERE category != 'Pháp luật' LIMIT 3")
    rows = cur.fetchall()
    target_ids = [f"db_{r[0]}" for r in rows]
    conn.close()

print(f"\n--- Simulating 3 clicks on {target_ids} ---")
for nid in target_ids:
    try:
        requests.post(f"{base_url}/record-action", json={
            "user_id": user_id,
            "news_id": nid,
            "action": "click",
            "dwell_time": 60
        })
    except Exception as e:
        print(f"Record Error: {e}")

# 3. After clicks
get_recs("Recommendations after clicks (Should show diversity)")
