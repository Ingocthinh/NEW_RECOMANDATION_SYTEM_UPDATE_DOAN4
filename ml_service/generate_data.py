import os
import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
from tqdm import tqdm

# Constants
NUM_USERS = 100000
NUM_BEHAVIORS = 1000000
DATA_TRAIN_DIR = r'i:\newrecomandationsystem\data_train'
NEWS_CSV = os.path.join(DATA_TRAIN_DIR, 'vietnamese_news_train.csv')

def generate_data():
    print("Loading news data...")
    news_df = pd.read_csv(NEWS_CSV)
    news_df['news_id'] = news_df.index.map(lambda x: f"news_{x:06d}")
    categories = news_df['Vietnamese_Label'].unique().tolist()
    
    # Map news to categories for fast lookup
    cat_to_news = {cat: np.array(news_df[news_df['Vietnamese_Label'] == cat]['news_id'].tolist()) for cat in categories}
    
    print(f"Generating {NUM_USERS} users...")
    user_ids = [f"user_{i:06d}" for i in range(NUM_USERS)]
    user_prefs = []
    users = []
    
    for uid in user_ids:
        num_prefs = random.randint(1, 3)
        prefs = random.sample(categories, num_prefs)
        user_prefs.append(prefs)
        users.append({
            'user_id': uid,
            'age': random.randint(18, 65),
            'gender': random.choice(['M', 'F', 'O']),
            'preferred_categories': ','.join(prefs),
            'created_at': (datetime.now() - timedelta(days=random.randint(30, 365))).strftime('%Y-%m-%d %H:%M:%S')
        })
        
    users_df = pd.DataFrame(users)
    users_df.to_csv(os.path.join(DATA_TRAIN_DIR, 'users.csv'), index=False)
    print(f"Saved users.csv.")

    print(f"Generating {NUM_BEHAVIORS} behaviors...")
    actions = ['view', 'click', 'like', 'share']
    action_probs = [0.7, 0.2, 0.07, 0.03]
    
    # Pre-select users for all behaviors
    behavior_user_indices = np.random.randint(0, NUM_USERS, size=NUM_BEHAVIORS)
    
    # Pre-select actions
    behavior_actions = np.random.choice(actions, size=NUM_BEHAVIORS, p=action_probs)
    
    # Pre-select categories (80% preferred, 20% random)
    is_preferred = np.random.random(NUM_BEHAVIORS) < 0.8
    
    behaviors = []
    
    # We still need a loop for the news picking because it depends on the user preference
    # but we can optimize the choosing
    for i in tqdm(range(NUM_BEHAVIORS)):
        uid_idx = behavior_user_indices[i]
        uid = user_ids[uid_idx]
        action = behavior_actions[i]
        
        if is_preferred[i]:
            cat = random.choice(user_prefs[uid_idx])
        else:
            cat = random.choice(categories)
            
        nid = random.choice(cat_to_news[cat])
        
        # Dwell time
        if action == 'view':
            dwell = random.randint(5, 30)
        elif action == 'click':
            dwell = random.randint(20, 120)
        else:
            dwell = random.randint(60, 300)
            
        behaviors.append([uid, nid, action, dwell])
    
    print("Converting to DataFrame and adding timestamps...")
    behaviors_df = pd.DataFrame(behaviors, columns=['user_id', 'news_id', 'action', 'dwell_time'])
    
    # Add timestamps (somewhat vectorized)
    base_time = datetime.now()
    timestamps = [
        (base_time - timedelta(days=random.randint(0, 30), seconds=random.randint(0, 86400))).strftime('%Y-%m-%d %H:%M:%S')
        for _ in range(NUM_BEHAVIORS)
    ]
    behaviors_df['timestamp'] = timestamps
    
    behaviors_df = behaviors_df.sort_values('timestamp')
    behaviors_df.to_csv(os.path.join(DATA_TRAIN_DIR, 'behaviors.csv'), index=False)
    print(f"Saved behaviors.csv with {len(behaviors_df)} records.")

if __name__ == "__main__":
    generate_data()
