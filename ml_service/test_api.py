import sys
import requests
import json
import time

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

base_url = "http://127.0.0.1:5000"

print("--- Testing Health ---")
try:
    health = requests.get(f"{base_url}/health")
    print(f"Health: {health.status_code}")
    print(json.dumps(health.json(), indent=2))
except Exception as e:
    print(f"Health Error: {e}")

print("\n--- Testing Recommendations for user_080827 ---")
start_time = time.time()
try:
    resp = requests.get(f"{base_url}/recommend/user_080827?top_n=5")
    print(f"Recommend: {resp.status_code} (took {time.time() - start_time:.2f}s)")
    recs = resp.json()
    for i, r in enumerate(recs):
        print(f"{i+1}. {r['title']} | Score: {r['score']} | Cat: {r['category']}")
except Exception as e:
    print(f"Recommend Error: {e}")

print("\n--- Testing Cold-start user ---")
try:
    resp = requests.get(f"{base_url}/recommend/new_user_999?top_n=3")
    print(f"Cold-start: {resp.status_code}")
    recs = resp.json()
    for i, r in enumerate(recs):
        print(f"{i+1}. {r['title']} | Score: {r['score']} | Cat: {r['category']}")
except Exception as e:
    print(f"Recommend Error: {e}")
