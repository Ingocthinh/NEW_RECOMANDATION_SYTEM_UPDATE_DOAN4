"""
Training & Evaluation Script for Hybrid News Recommender
==========================================================
Trains the model, splits behaviors into train/test, and evaluates with:
- Hit Rate@K
- Precision@K  
- Recall@K
- NDCG@K
"""

import sys
import os
import json
import time
import numpy as np
import pandas as pd
from collections import defaultdict
from tqdm import tqdm


if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Add parent to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "model")
sys.path.insert(0, BASE_DIR)
from recommender import HybridNewsRecommender

def dcg_at_k(relevances, k):
    """Compute DCG@K"""
    relevances = np.array(relevances[:k])
    if len(relevances) == 0:
        return 0.0
    return np.sum(relevances / np.log2(np.arange(2, len(relevances) + 2)))

def ndcg_at_k(relevances, k):
    """Compute NDCG@K"""
    actual_dcg = dcg_at_k(relevances, k)
    ideal_dcg = dcg_at_k(sorted(relevances, reverse=True), k)
    if ideal_dcg == 0:
        return 0.0
    return actual_dcg / ideal_dcg

def evaluate_all_modes(recommender, test_behaviors, k_values=[5, 10]):
    """
    Evaluate all recommendation modes for comparison.
    """
    modes = ['popularity', 'content', 'collaborative', 'hybrid']
    all_results = {}

    print("\n" + "=" * 60)
    print("  COMPREHENSIVE EVALUATION (THESIS LEVEL)")
    print("=" * 60)

    # Group test behaviors by user
    test_by_user = defaultdict(set)
    for _, row in test_behaviors.iterrows():
        test_by_user[str(row['user_id'])].add(row['news_id'])

    # Sample users for faster evaluation
    valid_users = [u for u in test_by_user.keys()]
    max_eval = min(500, len(valid_users))
    eval_users = np.random.choice(valid_users, size=max_eval, replace=False)
    
    print(f"  Evaluating on {max_eval} users with {len(test_behaviors)} test behaviors.")

    for mode in modes:
        print(f"\n  Evaluating Mode: {mode.upper()}...")
        results = {k: {'precision': [], 'recall': [], 'ndcg': [], 'hits': 0} for k in k_values}
        
        for user_id in tqdm(eval_users, desc=f"  {mode}"):
            held_out = test_by_user[user_id]
            if not held_out: continue
            
            try:
                recs = recommender.get_recommendations(user_id, top_n=max(k_values), mode=mode)
                rec_ids = [r['news_id'] for r in recs]
            except Exception as e: 
                # print(f"Error for user {user_id}: {e}")
                continue

            for k in k_values:
                top_k = rec_ids[:k]
                hits = len(set(top_k) & held_out)
                
                results[k]['precision'].append(hits / k)
                results[k]['recall'].append(hits / len(held_out) if held_out else 0)
                rel = [1.0 if nid in held_out else 0.0 for nid in top_k]
                results[k]['ndcg'].append(ndcg_at_k(rel, k))
                if hits > 0: results[k]['hits'] += 1

        # Summarize
        mode_metrics = {}
        for k in k_values:
            mode_metrics[f'P@{k}'] = np.mean(results[k]['precision']) if results[k]['precision'] else 0
            mode_metrics[f'R@{k}'] = np.mean(results[k]['recall']) if results[k]['recall'] else 0
            mode_metrics[f'NDCG@{k}'] = np.mean(results[k]['ndcg']) if results[k]['ndcg'] else 0
            mode_metrics[f'HR@{k}'] = results[k]['hits'] / len(eval_users) if len(eval_users) > 0 else 0
        
        all_results[mode] = mode_metrics


    # Print Comparison Table
    print("\n" + "=" * 80)
    print(f"{'Mode':<15} | {'P@10':<8} | {'R@10':<8} | {'NDCG@10':<8} | {'HR@10':<8}")
    print("-" * 80)
    for mode, m in all_results.items():
        print(f"{mode:<15} | {m.get('P@10',0):<8.4f} | {m.get('R@10',0):<8.4f} | {m.get('NDCG@10',0):<8.4f} | {m.get('HR@10',0):<8.4f}")
    print("=" * 80)
    
    return all_results

def main():
    print("Starting Thesis Model Training...")
    recommender = HybridNewsRecommender()
    recommender.load_all_data()

    # Chronological Split
    print("\nSplitting data 80/20 (Chronological)...")
    bhv = recommender.behaviors_df.sort_values('timestamp')
    split_idx = int(len(bhv) * 0.8)
    train_bhv = bhv.iloc[:split_idx]
    test_bhv = bhv.iloc[split_idx:]
    print(f"  -> Train size: {len(train_bhv)}, Test size: {len(test_bhv)}")

    # Train on training set
    recommender.behaviors_df = train_bhv
    # Update popular news based on training set
    recommender.popular_news = train_bhv.groupby('news_id').size().sort_values(ascending=False).index.tolist()
    
    recommender.build_content_model()
    recommender.build_collaborative_model()
    recommender.build_category_model()

    # Evaluate
    metrics = evaluate_all_modes(recommender, test_bhv)

    # Save metrics and report
    os.makedirs(MODEL_DIR, exist_ok=True)
    report_path = os.path.join(MODEL_DIR, "evaluation_report.json")
    with open(report_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    # Save final production model (trained on all data)
    print("\nTraining final production model...")
    recommender.behaviors_df = bhv
    recommender.popular_news = bhv.groupby('news_id').size().sort_values(ascending=False).index.tolist()
    recommender.build_collaborative_model() 
    recommender.build_category_model()      
    recommender.save_model()

    print("\nTraining Complete. Report saved to model/evaluation_report.json")

if __name__ == "__main__":
    main()
