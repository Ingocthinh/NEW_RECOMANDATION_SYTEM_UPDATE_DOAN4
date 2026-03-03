import requests
import json
import time

API_BASE = "http://localhost:3000/api"
USER_ID = 1 # Change this if needed

def test_recommendations():
    print(f"--- Testing Recommendations for User {USER_ID} ---")
    
    # 1. Get initial recommendations
    try:
        res = requests.get(f"{API_BASE}/recommend/{USER_ID}")
        recs = res.json()
        print(f"Initial Recommendations (Top 3):")
        for r in recs[:3]:
            print(f"  - [{r.get('category')}] {r.get('title')} (Score: {r.get('score')})")
        
        # Check sorting
        scores = [r.get('score', 0) for r in recs]
        is_sorted = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
        print(f"Is sorted descending: {is_sorted}")
        
    except Exception as e:
        print(f"Error fetching recommendations: {e}")

    # 2. Record an interaction for a specific category (e.g., 'CÔNG NGHỆ')
    # Find a news article in Technology if possible, or just use a dummy one
    print(f"\n--- Recording Interaction for 'CÔNG NGHỆ' ---")
    try:
        # Find a news article with category 'CÔNG NGHỆ'
        res_news = requests.get(f"{API_BASE}/news/latest")
        news_list = res_news.json()
        tech_article = next((n for n in news_list if n.get('category') == 'CÔNG NGHỆ'), None)
        
        if tech_article:
            print(f"Interacting with article: {tech_article['title']}")
            log_res = requests.post(f"{API_BASE}/behavior", json={
                "user_id": USER_ID,
                "news_id": tech_article['id'],
                "action": "click"
            })
            print(f"Logged behavior status: {log_res.status_code}")
            
            # 3. Get recommendations again
            time.sleep(1) # Wait for sync
            res_new = requests.get(f"{API_BASE}/recommend/{USER_ID}")
            new_recs = res_new.json()
            print(f"\nNew Recommendations (Top 3):")
            for r in new_recs[:3]:
                print(f"  - [{r.get('category')}] {r.get('title')} (Score: {r.get('score')})")
        else:
            print("No 'CÔNG NGHỆ' article found to test with.")
            
    except Exception as e:
        print(f"Error in interaction test: {e}")

if __name__ == "__main__":
    test_recommendations()
