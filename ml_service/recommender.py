"""
Hybrid News Recommendation System - Thesis Level (High Accuracy Edition)
========================================================================
Combines:
1. Content-Based Filtering: TF-IDF with Vietnamese NLP optimizations
2. Collaborative Filtering: Sparse SVD (Matrix Factorization) with implicit feedback
3. Profile Modeling: Category preference mapping with dwell-time weights
"""

import pandas as pd
import numpy as np
import os
import sys
import gc
import json
import joblib
import time
import sqlite3
import warnings
from collections import defaultdict

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize, LabelEncoder, MaxAbsScaler
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds

warnings.filterwarnings('ignore')

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# Optimized Constants for Accuracy
# ============================================================
ACTION_WEIGHTS = {
    'share': 10.0,
    'like': 8.0,
    'click': 5.0,
    'view': 2.0,
}

# Hybrid Weights (Adjustable)
CONTENT_WEIGHT = 0.35
COLLAB_WEIGHT = 0.45
CATEGORY_WEIGHT = 0.20

SVD_K = 100  # Increased latent factors for higher precision
MAX_BEHAVIORS = 1000000 # Increased limit for better coverage
MAX_TFIDF_FEATURES = 100000 # High feature count for news diversity
TFIDF_NGRAM = (1, 3) # Include trigrams for better Vietnamese phrase matching

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
DATA_TRAIN_DIR = os.path.join(BASE_DIR, "..", "data_train")
MODEL_DIR = os.path.join(BASE_DIR, "model")
DB_PATH = os.path.join(DATA_DIR, "news.db")


class HybridNewsRecommender:
    def __init__(self):
        os.makedirs(MODEL_DIR, exist_ok=True)
        self.news_df = None
        self.behaviors_df = None
        self.users_df = None

        # Components
        self.tfidf_vectorizer = None
        self.tfidf_matrix = None
        self.user_factors = None
        self.news_factors = None
        self.user_means = None
        self.collab_user_to_idx = None
        self.collab_news_to_idx = None
        self.category_map = None
        self.news_id_to_idx = None
        self.news_id_to_category = None
        self.popular_news = []
        self._news_categories_series = None

    def load_all_data(self):
        """Unified data loader from CSV and Database"""
        print("\n[1/3] Loading Data Sources...")
        all_news = []
        
        # 1. DB Content
        if os.path.exists(DB_PATH):
            try:
                conn = sqlite3.connect(DB_PATH)
                db_news = pd.read_sql_query("SELECT id, title, content, summary, category FROM News", conn)
                conn.close()
                db_news['news_id'] = db_news['id'] # Store as integer to match DB
                db_news['text_combined'] = db_news['title'].fillna('') + ' ' + db_news['summary'].fillna('') + ' ' + db_news['content'].fillna('')
                all_news.append(db_news[['news_id', 'title', 'text_combined', 'category']])
                print(f"  -> {len(db_news)} DB articles loaded")
            except Exception as e:
                print(f"  !! DB Load Error: {e}")

        # 2. CSV Content (Training Set)
        csv_news_path = os.path.join(DATA_TRAIN_DIR, "vietnamese_news_train.csv")
        if os.path.exists(csv_news_path):
            csv_news = pd.read_csv(csv_news_path, encoding='utf-8')
            csv_news['news_id'] = csv_news.index.map(lambda x: f"news_{x:06d}")
            csv_news['text_combined'] = csv_news['title'].fillna('') + ' ' + csv_news['description'].fillna('') + ' ' + csv_news['text'].fillna('')
            csv_news = csv_news.rename(columns={'Vietnamese_Label': 'category'})
            all_news.append(csv_news[['news_id', 'title', 'text_combined', 'category']])
            print(f"  -> {len(csv_news)} CSV articles loaded")

        if not all_news:
             raise ValueError("No news data found! Check paths.")

        self.news_df = pd.concat(all_news, ignore_index=True).drop_duplicates('news_id')
        self.news_df = self.news_df.dropna(subset=['text_combined'])
        self.news_id_to_idx = {nid: i for i, nid in enumerate(self.news_df['news_id'])}
        self.news_id_to_category = dict(zip(self.news_df['news_id'], self.news_df['category']))
        self._news_categories_series = self.news_df['category'].values

        # 3. Load Interaction Data
        bhv_csv_path = os.path.join(DATA_TRAIN_DIR, "behaviors.csv")
        if os.path.exists(bhv_csv_path):
            self.behaviors_df = pd.read_csv(bhv_csv_path, encoding='utf-8')
            # Use dwell_time to boost ratings if available
            self.behaviors_df['rating'] = self.behaviors_df['action'].map(ACTION_WEIGHTS).fillna(1.0)
            if 'dwell_time' in self.behaviors_df.columns:
                # Add dwell time boost: log(dwell_time + 1)
                self.behaviors_df['rating'] += np.log1p(self.behaviors_df['dwell_time'].fillna(0))
            print(f"  -> {len(self.behaviors_df)} behaviors loaded with dwell-time weighting")

        users_csv_path = os.path.join(DATA_TRAIN_DIR, "users.csv")
        if os.path.exists(users_csv_path):
            self.users_df = pd.read_csv(users_csv_path, encoding='utf-8')
            print(f"  -> {len(self.users_df)} user profiles loaded")

        # Global Popularity for Cold Start
        if self.behaviors_df is not None:
            self.popular_news = self.behaviors_df.groupby('news_id').size().sort_values(ascending=False).index.tolist()

    def build_content_model(self):
        """Advanced TF-IDF with Trigrams and Sublinear Scaling"""
        print("\n[2/3] Building Content-Based Model...")
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=MAX_TFIDF_FEATURES, 
            ngram_range=TFIDF_NGRAM, 
            sublinear_tf=True, 
            min_df=3,
            max_df=0.9
        )
        self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(self.news_df['text_combined'])
        print(f"  -> Content Matrix: {self.tfidf_matrix.shape}")

    def build_collaborative_model(self):
        """Highly Optimized Sparse SVD Factorization"""
        print("\n[3/3] Building Collaborative Model...")
        if self.behaviors_df is None: return
        
        bhv = self.behaviors_df.copy()
        bhv = bhv[bhv['news_id'].isin(self.news_id_to_idx)]
        
        if len(bhv) > MAX_BEHAVIORS:
            bhv = bhv.sample(n=MAX_BEHAVIORS, random_state=42)

        bhv_agg = bhv.groupby(['user_id', 'news_id'])['rating'].sum().reset_index()
        
        u_enc = LabelEncoder()
        n_enc = LabelEncoder()
        bhv_agg['u_idx'] = u_enc.fit_transform(bhv_agg['user_id'])
        bhv_agg['n_idx'] = n_enc.fit_transform(bhv_agg['news_id'])

        n_users, n_news = bhv_agg['u_idx'].nunique(), bhv_agg['n_idx'].nunique()
        interactions = csr_matrix((bhv_agg['rating'], (bhv_agg['u_idx'], bhv_agg['n_idx'])), shape=(n_users, n_news))
        
        # SVD Computation
        k = min(SVD_K, min(n_users, n_news) - 1)
        if k < 5: return
        
        U, sigma, Vt = svds(interactions.astype(float), k=k)
        
        # Matrix Reconstruction Components
        self.user_factors = U @ np.diag(sigma)
        self.news_factors = Vt.T
        self.user_means = np.array(interactions.mean(axis=1)).flatten()
        
        self.collab_user_to_idx = dict(zip(u_enc.classes_, range(len(u_enc.classes_))))
        self.collab_news_to_idx = dict(zip(n_enc.classes_, range(len(n_enc.classes_))))
        print(f"  -> CF Factors ready: {self.user_factors.shape}")

    def build_category_model(self):
        """User Personality Profiling via Category Weights"""
        print("Building Category Profiles...")
        self.category_map = defaultdict(lambda: defaultdict(float))
        
        if self.users_df is not None:
            for _, row in self.users_df.iterrows():
                uid = str(row['user_id'])
                for cat in str(row.get('preferred_categories', '')).split(','):
                    c = cat.strip()
                    if c: self.category_map[uid][c] += 10.0 # High weight for explicit preference

        if self.behaviors_df is not None:
            for _, row in self.behaviors_df.iterrows():
                uid, nid, rating = str(row['user_id']), row['news_id'], row['rating']
                cat = self.news_id_to_category.get(nid)
                if cat: self.category_map[uid][cat] += rating
        
        self.category_map = {k: dict(v) for k, v in self.category_map.items()}

    def _normalize(self, scores):
        """Safe normalization [0, 1]"""
        if scores is None or len(scores) == 0: return np.zeros(len(self.news_df))
        mn, mx = scores.min(), scores.max()
        if mx > mn: return (scores - mn) / (mx - mn)
        return np.zeros_like(scores)

    def get_content_scores(self, user_id):
        if self.behaviors_df is None: return np.zeros(len(self.news_df))
        user_bhv = self.behaviors_df[self.behaviors_df['user_id'] == user_id]
        if user_bhv.empty: return np.zeros(len(self.news_df))
        
        # Build user profile vector from history
        weighted_vectors = []
        total_weight = 0
        for _, row in user_bhv.iterrows():
            if row['news_id'] in self.news_id_to_idx:
                idx = self.news_id_to_idx[row['news_id']]
                weighted_vectors.append(self.tfidf_matrix[idx] * row['rating'])
                total_weight += row['rating']
        
        if not weighted_vectors: return np.zeros(len(self.news_df))
        
        user_profile = sum(weighted_vectors) / total_weight
        scores = self.tfidf_matrix.dot(user_profile.T).toarray().flatten()
        return scores

    def get_collab_scores(self, user_id):
        if self.user_factors is None or user_id not in self.collab_user_to_idx: return None
        u_idx = self.collab_user_to_idx[user_id]
        preds = self.user_factors[u_idx] @ self.news_factors.T + self.user_means[u_idx]
        
        full_scores = np.zeros(len(self.news_df))
        for nid, col_idx in self.collab_news_to_idx.items():
            if nid in self.news_id_to_idx:
                full_scores[self.news_id_to_idx[nid]] = preds[col_idx]
        return full_scores

    def get_category_scores(self, user_id):
        if user_id not in self.category_map: return np.zeros(len(self.news_df))
        prefs = self.category_map[user_id]
        total = sum(prefs.values())
        if total == 0: return np.zeros(len(self.news_df))
        
        norm_prefs = {k: v/total for k, v in prefs.items()}
        scores = np.array([norm_prefs.get(cat, 0.0) for cat in self._news_categories_series])
        return scores

    def get_recommendations(self, user_id, top_n=10, mode='hybrid'):
        try:
            user_id = int(float(user_id)) # Handle numeric user_id from backend
        except:
            user_id = str(user_id)
        interacted = set(self.behaviors_df[self.behaviors_df['user_id'] == user_id]['news_id']) if self.behaviors_df is not None else set()

        # Generate scores
        c_scores = self.get_content_scores(user_id)
        cf_scores = self.get_collab_scores(user_id)
        cat_scores = self.get_category_scores(user_id)

        # Merge Logic
        if mode == 'content':
            final_scores = c_scores
        elif mode == 'collaborative':
            final_scores = cf_scores if cf_scores is not None else np.zeros(len(self.news_df))
        elif mode == 'popularity':
            final_scores = np.zeros(len(self.news_df))
            for i, nid in enumerate(self.popular_news[:100]):
                if nid in self.news_id_to_idx: final_scores[self.news_id_to_idx[nid]] = 100 - i
        else: # Hybrid
            c_norm = self._normalize(c_scores)
            cat_norm = self._normalize(cat_scores)
            if cf_scores is not None:
                cf_norm = self._normalize(cf_scores)
                final_scores = (CONTENT_WEIGHT * c_norm + COLLAB_WEIGHT * cf_norm + CATEGORY_WEIGHT * cat_norm)
            else:
                # Fallback for cold start users (Content + Category)
                final_scores = 0.6 * c_norm + 0.4 * cat_norm

        # Ranking with Diversity (Category Penalty)
        ranked_indices = np.argsort(final_scores)[::-1]
        results = []
        seen_categories = defaultdict(int)
        
        max_f = np.max(final_scores) if len(final_scores) > 0 else 0
        
        for idx in ranked_indices:
            news_row = self.news_df.iloc[idx]
            nid = news_row['news_id']
            cat = news_row['category']
            
            if nid not in interacted:
                # ONLY suggest articles that are in the database (integer IDs)
                if not isinstance(nid, int) and not str(nid).startswith('db_'):
                    continue
                    
                # Stronger diversity: Hard cap + dynamic penalty
                if seen_categories[cat] >= 3:
                    continue
                    
                diversity_penalty = 0.25 * seen_categories[cat]
                
                raw_score = float(final_scores[idx])
                adjusted_raw = max(0, raw_score - diversity_penalty)
                
                scaled_score = 0.5 + (adjusted_raw / (max_f + 1e-9)) * 0.49 if max_f > 0 else 0.0
                
                if scaled_score > 0.0:
                    scaled_score = min(0.9999, scaled_score + 0.1)

                results.append({
                    "news_id": nid,
                    "title": news_row['title'],
                    "category": cat,
                    "score": round(scaled_score, 4)
                })
                seen_categories[cat] += 1
                
            if len(results) >= top_n: break

        # Background Fallback
        if not results:
            for nid in self.popular_news[:top_n]:
                if nid in self.news_id_to_idx:
                    idx = self.news_id_to_idx[nid]
                    results.append({
                        "news_id": nid, 
                        "title": self.news_df.iloc[idx]['title'], 
                        "category": self.news_df.iloc[idx]['category'], 
                        "score": 0.1 # Popularity score baseline
                    })
        
        return results

    def record_interaction(self, user_id, news_id, action, dwell_time=0):
        """Record a new interaction in real-time (in-memory)"""
        try:
            user_id = int(float(user_id))
        except:
            user_id = str(user_id)
            
        try:
            news_id = int(float(news_id))
        except:
            news_id = str(news_id)
        rating = ACTION_WEIGHTS.get(action, 1.0)
        if dwell_time > 0:
            rating += np.log1p(dwell_time)
            
        # 1. Update behaviors_df
        new_row = pd.DataFrame([{
            'user_id': user_id,
            'news_id': news_id,
            'action': action,
            'dwell_time': dwell_time,
            'rating': rating,
            'timestamp': time.time()
        }])
        
        if self.behaviors_df is not None:
            self.behaviors_df = pd.concat([self.behaviors_df, new_row], ignore_index=True)
        else:
            self.behaviors_df = new_row
            
        # 2. Update category_map for personalized ranking
        cat = self.news_id_to_category.get(news_id)
        if cat:
            if user_id not in self.category_map:
                self.category_map[user_id] = {}
            self.category_map[user_id][cat] = self.category_map[user_id].get(cat, 0.0) + rating
            
        print(f"Recorded real-time interaction: User {user_id} -> News {news_id} ({action})")
        return True

    def save_model(self):
        print("\nSaving Production Model...")
        joblib.dump(self.news_df, os.path.join(MODEL_DIR, "news_df.pkl"))
        joblib.dump(self.tfidf_vectorizer, os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl"))
        joblib.dump(self.tfidf_matrix, os.path.join(MODEL_DIR, "tfidf_matrix.pkl"))
        joblib.dump(self.news_id_to_idx, os.path.join(MODEL_DIR, "news_id_to_idx.pkl"))
        joblib.dump(self.news_id_to_category, os.path.join(MODEL_DIR, "news_id_to_category.pkl"))
        joblib.dump(self.category_map, os.path.join(MODEL_DIR, "category_map.pkl"))
        joblib.dump(self.behaviors_df, os.path.join(MODEL_DIR, "behaviors_df.pkl"))
        joblib.dump(self.popular_news, os.path.join(MODEL_DIR, "popular_news.pkl"))
        
        joblib.dump({
            'user_factors': self.user_factors, 'news_factors': self.news_factors,
            'user_means': self.user_means, 'collab_user_to_idx': self.collab_user_to_idx,
            'collab_news_to_idx': self.collab_news_to_idx
        }, os.path.join(MODEL_DIR, "collab_model.pkl"))
        print(f"Model successfully saved to {MODEL_DIR}")

    def load_model(self):
        try:
            self.news_df = joblib.load(os.path.join(MODEL_DIR, "news_df.pkl"))
            self.tfidf_vectorizer = joblib.load(os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl"))
            self.tfidf_matrix = joblib.load(os.path.join(MODEL_DIR, "tfidf_matrix.pkl"))
            self.news_id_to_idx = joblib.load(os.path.join(MODEL_DIR, "news_id_to_idx.pkl"))
            self.news_id_to_category = joblib.load(os.path.join(MODEL_DIR, "news_id_to_category.pkl"))
            self.category_map = joblib.load(os.path.join(MODEL_DIR, "category_map.pkl"))
            self.behaviors_df = joblib.load(os.path.join(MODEL_DIR, "behaviors_df.pkl"))
            self.popular_news = joblib.load(os.path.join(MODEL_DIR, "popular_news.pkl"))
            self._news_categories_series = self.news_df['category'].values
            
            c = joblib.load(os.path.join(MODEL_DIR, "collab_model.pkl"))
            self.user_factors, self.news_factors = c['user_factors'], c['news_factors']
            self.user_means, self.collab_user_to_idx, self.collab_news_to_idx = c['user_means'], c['collab_user_to_idx'], c['collab_news_to_idx']
            return True
        except: return False

if __name__ == "__main__":
    recommender = HybridNewsRecommender()
    recommender.load_all_data()
    recommender.build_content_model()
    recommender.build_collaborative_model()
    recommender.build_category_model()
    recommender.save_model()
