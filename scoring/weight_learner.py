# -*- coding: utf-8 -*-
"""
LambdaMART Weight Learner for Job Matching
==========================================
Replaces fixed weights with a learned ranking model.

Instead of:
    score = 0.40*skill + 0.20*role + 0.15*exp + 0.15*loc + 0.10*text
    
The model learns NON-LINEAR relationships:
    score = LambdaMART(skill, role, exp, loc, text, sal, ...)

Usage:
    1. Generate evaluation data:  python -m scoring.weight_learner generate
    2. Label the data (manually):  Edit evaluation/eval_dataset.xlsx
    3. Train model:               python -m scoring.weight_learner train
    4. Analyze weights:           python -m scoring.weight_learner analyze
"""

import os
import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "models"
EVAL_DIR = BASE_DIR / "evaluation"
MODEL_PATH = MODEL_DIR / "lambdamart_ranker.pkl"
FEATURE_NAMES_PATH = MODEL_DIR / "feature_names.json"
EVAL_DATASET_PATH = EVAL_DIR / "eval_dataset.xlsx"
EVAL_DATASET_LABELED_PATH = EVAL_DIR / "eval_dataset_labeled.xlsx"

# ─── Feature Names ────────────────────────────────────────────────────────────
FEATURE_COLS = [
    "f_skill_coverage",      # Skill coverage score (from XAI)
    "f_text_similarity",     # TF-IDF cosine similarity
    "f_location_match",      # Location match (0, 0.7, or 1.0)
    "f_role_similarity",     # Role similarity (0-1)
    "f_exp_similarity",      # Experience bucket similarity (0-1)
    "f_salary_known",        # Whether salary is known (0 or 1)
    # --- Extended features (advantage over linear weights) ---
    "f_num_matched_skills",  # Number of matched skills
    "f_num_missing_skills",  # Number of missing skills from job requirements
    "f_skill_match_ratio",   # Ratio of matched/total job skills
    "f_top_skill_contrib",   # Contribution of top matched skill
    "f_domain_match",        # Whether CV and job are in same domain (0 or 1)
    "f_skill_x_exp",         # Interaction: skill * experience
    "f_skill_x_role",        # Interaction: skill * role
]


def extract_features(s_skill, s_text, s_loc, s_role, s_exp, s_sal,
                      explain_data=None, cv_domain="general", job_domain="general"):
    """Extract feature vector from individual scoring components.
    
    Args:
        s_skill:  Skill coverage score (0-1)
        s_text:   TF-IDF text similarity (0-1)
        s_loc:    Location match score (0-1)
        s_role:   Role similarity (0-1)
        s_exp:    Experience similarity (0-1)
        s_sal:    Salary match (0 or 1)
        explain_data: XAI explain dict from explain_user_job()
        cv_domain:  Detected domain of CV
        job_domain: Detected domain of job
    
    Returns:
        np.array of shape (13,) — the feature vector
    """
    # Parse explain_data for extended features
    num_matched = 0
    num_missing = 0
    top_contrib = 0.0
    
    if explain_data and "evidence" in explain_data:
        evidence = explain_data["evidence"]
        matched_skills = evidence.get("matched_skills", [])
        missing_skills = evidence.get("missing_skills", [])
        num_matched = len(matched_skills)
        num_missing = len(missing_skills)
        if matched_skills:
            top_contrib = matched_skills[0].get("contrib", 0.0)

    total_skills = num_matched + num_missing
    skill_match_ratio = num_matched / total_skills if total_skills > 0 else 0.0
    
    domain_match = 1.0 if (cv_domain == job_domain or 
                           cv_domain == "general" or 
                           job_domain == "general") else 0.0

    features = np.array([
        float(s_skill),
        float(s_text),
        float(s_loc),
        float(s_role),
        float(s_exp),
        float(s_sal),
        float(num_matched),
        float(num_missing),
        float(skill_match_ratio),
        float(top_contrib),
        float(domain_match),
        float(s_skill * s_exp),   # Interaction feature
        float(s_skill * s_role),  # Interaction feature
    ], dtype=np.float32)
    
    return features


def generate_eval_template(job_info, job_nodes, user_prob, user_city, user_detail,
                           IDX, X, cv_vec, tfidf, user_role_can, user_exp_bucket,
                           user_raw2can_best=None, user_raw2can_map=None,
                           cv_text="", sample_n=100, random_seed=42):
    """Generate evaluation dataset template for manual labeling.
    
    Creates an Excel file with CV-Job pairs and their computed features.
    The evaluator needs to add a 'relevance' column (0-3):
        0 = Irrelevant
        1 = Marginally relevant  
        2 = Relevant
        3 = Highly relevant
    
    Returns:
        Path to the generated Excel file
    """
    from scoring.user_job_score import user_job_score
    from scoring.skill_variants import detect_domain
    
    rng = np.random.RandomState(random_seed)
    
    # Sample jobs: mix of top-scored and random
    valid_jobs = [j for j in job_nodes if j in job_info]
    
    # Compute all scores first
    all_scores = []
    for j in valid_jobs:
        sc, ex = user_job_score(
            user_prob, user_city, user_detail, j, job_info,
            IDX, X, cv_vec, tfidf, user_role_can, user_exp_bucket,
            user_raw2can_best=user_raw2can_best,
            user_raw2can_map=user_raw2can_map,
            cv_domain=detect_domain(cv_text) if cv_text else "general"
        )
        all_scores.append((j, sc, ex))
    
    all_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Stratified sampling: top 40%, middle 30%, bottom 30%
    n = min(sample_n, len(all_scores))
    n_top = int(n * 0.4)
    n_mid = int(n * 0.3)
    n_bot = n - n_top - n_mid
    
    top_jobs = all_scores[:n_top]
    
    mid_start = len(all_scores) // 4
    mid_end = 3 * len(all_scores) // 4
    mid_pool = all_scores[mid_start:mid_end]
    if len(mid_pool) > n_mid:
        mid_indices = rng.choice(len(mid_pool), n_mid, replace=False)
        mid_jobs = [mid_pool[i] for i in mid_indices]
    else:
        mid_jobs = mid_pool[:n_mid]
    
    bot_pool = all_scores[len(all_scores)//2:]
    if len(bot_pool) > n_bot:
        bot_indices = rng.choice(len(bot_pool), n_bot, replace=False)
        bot_jobs = [bot_pool[i] for i in bot_indices]
    else:
        bot_jobs = bot_pool[:n_bot]
    
    sampled = top_jobs + mid_jobs + bot_jobs
    
    # Build DataFrame
    rows = []
    cv_domain = detect_domain(cv_text) if cv_text else "general"
    
    for job_node, current_score, explain in sampled:
        job = job_info[job_node]
        comp = explain.get("components", {})
        
        job_text = f"{job['title']} {job.get('description', '')} {job.get('requirements', '')}"
        job_domain = detect_domain(job_text)
        
        features = extract_features(
            s_skill=comp.get("skill", 0),
            s_text=comp.get("text", 0),
            s_loc=comp.get("location", 0),
            s_role=comp.get("role", 0),
            s_exp=comp.get("experience", 0),
            s_sal=comp.get("salary", 0),
            explain_data=explain,
            cv_domain=cv_domain,
            job_domain=job_domain
        )
        
        row = {
            "job_node": job_node,
            "job_title": job["title"],
            "company": job["company"],
            "current_score": round(current_score, 4),
            "relevance": "",  # TO BE FILLED BY EVALUATOR
        }
        
        # Add feature columns
        for fname, fval in zip(FEATURE_COLS, features):
            row[fname] = round(float(fval), 4)
        
        # Add context for the evaluator
        row["job_skills_required"] = ", ".join(
            list(job.get("prob_skills", {}).keys())[:10]
        )
        row["user_skills"] = ", ".join(
            list(user_prob.keys())[:10]
        )
        row["job_city"] = job.get("city", "")
        row["user_city"] = user_city
        row["job_exp"] = job.get("exp_bucket", "")
        row["user_exp"] = user_exp_bucket
        
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    # Save
    os.makedirs(EVAL_DIR, exist_ok=True)
    df.to_excel(str(EVAL_DATASET_PATH), index=False, engine='openpyxl')
    
    print(f"[EVAL] Generated evaluation template: {EVAL_DATASET_PATH}")
    print(f"[EVAL] {len(df)} job pairs to evaluate")
    print(f"[EVAL] Please fill the 'relevance' column (0=Irrelevant, 1=Marginal, 2=Relevant, 3=Highly Relevant)")
    print(f"[EVAL] Then save as: {EVAL_DATASET_LABELED_PATH}")
    
    return str(EVAL_DATASET_PATH)


def generate_pseudo_labels(job_info, job_nodes, user_prob, user_city, user_detail,
                           IDX, X, cv_vec, tfidf, user_role_can, user_exp_bucket,
                           user_raw2can_best=None, user_raw2can_map=None,
                           cv_text="", n_samples=200):
    """Generate pseudo-labels from the current fixed-weight scoring.
    
    Use this if you don't have manual labels yet.
    The current system's ranking is used as ground truth.
    This helps the model learn the non-linear relationships
    while starting from the current baseline.
    
    Returns:
        DataFrame with features and pseudo relevance labels
    """
    from scoring.user_job_score import user_job_score
    from scoring.skill_variants import detect_domain
    
    valid_jobs = [j for j in job_nodes if j in job_info]
    cv_domain = detect_domain(cv_text) if cv_text else "general"
    
    all_data = []
    for j in valid_jobs:
        sc, ex = user_job_score(
            user_prob, user_city, user_detail, j, job_info,
            IDX, X, cv_vec, tfidf, user_role_can, user_exp_bucket,
            user_raw2can_best=user_raw2can_best,
            user_raw2can_map=user_raw2can_map,
            cv_domain=cv_domain
        )
        
        job = job_info[j]
        comp = ex.get("components", {})
        job_text = f"{job['title']} {job.get('description', '')} {job.get('requirements', '')}"
        job_domain = detect_domain(job_text)
        
        features = extract_features(
            s_skill=comp.get("skill", 0),
            s_text=comp.get("text", 0),
            s_loc=comp.get("location", 0),
            s_role=comp.get("role", 0),
            s_exp=comp.get("experience", 0),
            s_sal=comp.get("salary", 0),
            explain_data=ex,
            cv_domain=cv_domain,
            job_domain=job_domain
        )
        
        all_data.append({
            "job_node": j,
            "score": sc,
            "features": features
        })
    
    # Sort by score to assign pseudo-labels
    all_data.sort(key=lambda x: x["score"], reverse=True)
    n = len(all_data)
    
    # Assign relevance labels based on percentile ranking
    for i, item in enumerate(all_data):
        pct = i / n
        if pct < 0.05:       # Top 5% → highly relevant
            item["relevance"] = 3
        elif pct < 0.15:     # Top 5-15% → relevant
            item["relevance"] = 2
        elif pct < 0.35:     # Top 15-35% → marginally relevant
            item["relevance"] = 1
        else:                # Bottom 65% → irrelevant
            item["relevance"] = 0
    
    # Sample if needed
    if n_samples and n > n_samples:
        rng = np.random.RandomState(42)
        indices = rng.choice(n, n_samples, replace=False)
        all_data = [all_data[i] for i in sorted(indices)]
    
    # Build feature matrix
    rows = []
    for item in all_data:
        row = {"job_node": item["job_node"], "relevance": item["relevance"]}
        for fname, fval in zip(FEATURE_COLS, item["features"]):
            row[fname] = float(fval)
        rows.append(row)
    
    return pd.DataFrame(rows)


def train_lambdamart(labeled_data=None, labeled_path=None, 
                      n_estimators=200, learning_rate=0.05, 
                      num_leaves=31, max_depth=6,
                      use_pseudo=False, **pseudo_kwargs):
    """Train LambdaMART ranking model.
    
    Args:
        labeled_data: DataFrame with columns [relevance, f_skill_coverage, ...]
        labeled_path: Path to labeled Excel file (alternative to labeled_data)
        n_estimators: Number of boosting rounds
        learning_rate: Learning rate
        num_leaves: Max leaves per tree
        max_depth: Max tree depth
        use_pseudo: If True, generate pseudo labels (needs pseudo_kwargs)
        
    Returns:
        dict with model, metrics, and feature importances
    """
    try:
        import lightgbm as lgb  # type: ignore[import-not-found]
    except ImportError:
        raise ImportError(
            "lightgbm is required for LambdaMART training.\n"
            "Install with: pip install lightgbm"
        )
    
    # Load data
    if use_pseudo:
        df = generate_pseudo_labels(**pseudo_kwargs)
        print(f"[TRAIN] Using {len(df)} pseudo-labeled samples")
    elif labeled_data is not None:
        df = labeled_data
    elif labeled_path:
        df = pd.read_excel(labeled_path, engine='openpyxl')
    else:
        # Try default path
        if EVAL_DATASET_LABELED_PATH.exists():
            df = pd.read_excel(str(EVAL_DATASET_LABELED_PATH), engine='openpyxl')
        else:
            raise FileNotFoundError(
                f"No labeled data found. Either:\n"
                f"  1. Provide labeled_data DataFrame\n"
                f"  2. Create {EVAL_DATASET_LABELED_PATH}\n"
                f"  3. Use use_pseudo=True with pseudo_kwargs"
            )
    
    # Validate
    if "relevance" not in df.columns:
        raise ValueError("DataFrame must have a 'relevance' column (values 0-3)")
    
    df = df.dropna(subset=["relevance"])
    df["relevance"] = df["relevance"].astype(int)
    
    # Prepare features
    available_features = [c for c in FEATURE_COLS if c in df.columns]
    X = df[available_features].values.astype(np.float32)
    y = df["relevance"].values.astype(np.int32)
    
    print(f"[TRAIN] Features: {len(available_features)}")
    print(f"[TRAIN] Samples: {len(X)}")
    print(f"[TRAIN] Label distribution: {dict(pd.Series(y).value_counts().sort_index())}")
    
    # For LambdaMART, we need query groups
    # In our case, all samples belong to the same query (single CV)
    # For multi-CV training, we'd group by CV
    if "query_id" in df.columns:
        groups = df.groupby("query_id").size().values
    else:
        # Single query group
        groups = np.array([len(X)])
    
    # Train/validation split (80/20 within each query)
    from sklearn.model_selection import train_test_split
    
    if len(X) >= 20:
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        train_groups = np.array([len(X_train)])
        val_groups = np.array([len(X_val)])
        
        train_set = lgb.Dataset(X_train, label=y_train, group=train_groups,
                                feature_name=available_features)
        val_set = lgb.Dataset(X_val, label=y_val, group=val_groups,
                              feature_name=available_features, reference=train_set)
        eval_sets = [val_set]
        eval_names = ["valid"]
    else:
        train_set = lgb.Dataset(X, label=y, group=groups,
                                feature_name=available_features)
        eval_sets = []
        eval_names = []
    
    # LambdaMART parameters
    params = {
        "objective": "lambdarank",
        "metric": "ndcg",
        "ndcg_eval_at": [1, 3, 5, 10],
        "learning_rate": learning_rate,
        "num_leaves": num_leaves,
        "max_depth": max_depth,
        "min_child_samples": max(1, len(X) // 20),
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "feature_pre_filter": False,
        "verbose": -1,
        "seed": 42,
        "label_gain": [0, 1, 3, 7],  # Gain for labels 0, 1, 2, 3
    }
    
    # Train
    callbacks = [lgb.log_evaluation(period=50)]
    if eval_sets:
        callbacks.append(lgb.early_stopping(stopping_rounds=30, verbose=True))
    
    model = lgb.train(
        params,
        train_set,
        num_boost_round=n_estimators,
        valid_sets=eval_sets,
        valid_names=eval_names,
        callbacks=callbacks,
    )
    
    # Feature importance
    importance_gain = model.feature_importance(importance_type='gain')
    importance_split = model.feature_importance(importance_type='split')
    
    total_gain = importance_gain.sum()
    feature_weights = {}
    for fname, gain, split in zip(available_features, importance_gain, importance_split):
        feature_weights[fname] = {
            "gain": float(gain),
            "split": int(split),
            "relative_weight": round(float(gain / total_gain), 4) if total_gain > 0 else 0.0,
        }
    
    # Sort by gain
    feature_weights = dict(
        sorted(feature_weights.items(), key=lambda x: x[1]["gain"], reverse=True)
    )
    
    # Save model
    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(str(MODEL_PATH), "wb") as f:
        pickle.dump(model, f)
    
    with open(str(FEATURE_NAMES_PATH), "w") as f:
        json.dump(available_features, f)
    
    print(f"\n[TRAIN] Model saved to: {MODEL_PATH}")
    print(f"[TRAIN] Feature importance (by relative weight):")
    for fname, info in feature_weights.items():
        bar = "#" * int(info["relative_weight"] * 50)
        print(f"  {fname:30s} {info['relative_weight']:.4f}  {bar}")
    
    # Compare with fixed weights
    print(f"\n[COMPARE] Fixed weights vs Learned weights:")
    fixed_map = {
        "f_skill_coverage": 0.40,
        "f_text_similarity": 0.10,
        "f_location_match": 0.15,
        "f_role_similarity": 0.20,
        "f_exp_similarity": 0.15,
        "f_salary_known": 0.00,
    }
    print(f"  {'Feature':30s} {'Fixed':>8s} {'Learned':>8s} {'Delta':>8s}")
    print(f"  {'-'*30} {'-'*8} {'-'*8} {'-'*8}")
    for fname in FEATURE_COLS[:6]:
        fixed = fixed_map.get(fname, 0.0)
        learned = feature_weights.get(fname, {}).get("relative_weight", 0.0)
        delta = learned - fixed
        sign = "+" if delta > 0 else ""
        print(f"  {fname:30s} {fixed:8.4f} {learned:8.4f} {sign}{delta:7.4f}")
    
    result = {
        "model": model,
        "feature_names": available_features,
        "feature_weights": feature_weights,
        "n_samples": len(X),
        "label_distribution": dict(pd.Series(y).value_counts().sort_index()),
        "model_path": str(MODEL_PATH),
    }
    
    return result


def load_model():
    """Load trained LambdaMART model.
    
    Returns:
        tuple: (model, feature_names) or (None, None) if no model exists
    """
    if not MODEL_PATH.exists():
        return None, None
    
    try:
        with open(str(MODEL_PATH), "rb") as f:
            model = pickle.load(f)
        with open(str(FEATURE_NAMES_PATH), "r") as f:
            feature_names = json.load(f)
        return model, feature_names
    except Exception as e:
        print(f"[WARN] Failed to load LambdaMART model: {e}")
        return None, None


def predict_score(model, features):
    """Predict relevance score using trained model.
    
    Args:
        model: Trained LightGBM model
        features: np.array of shape (13,) from extract_features()
    
    Returns:
        float: Predicted relevance score (higher = more relevant)
    """
    if model is None:
        return None
    
    # LightGBM expects 2D input
    X = features.reshape(1, -1)
    score = model.predict(X)[0]
    
    # Normalize to [0, 1] range using sigmoid
    normalized = 1.0 / (1.0 + np.exp(-score))
    return float(round(normalized, 4))


def tune_lambdamart(labeled_data=None, labeled_path=None, n_trials=50, use_pseudo=False, **pseudo_kwargs):
    """Tune LambdaMART hyperparameters using Optuna."""
    try:
        import optuna
        import lightgbm as lgb
    except ImportError:
        raise ImportError("optuna and lightgbm are required for tuning.")
        
    # Load data
    if use_pseudo:
        df = generate_pseudo_labels(**pseudo_kwargs)
        print(f"[TUNE] Using {len(df)} pseudo-labeled samples")
    elif labeled_data is not None:
        df = labeled_data
    elif labeled_path:
        df = pd.read_excel(labeled_path, engine='openpyxl')
    else:
        if EVAL_DATASET_LABELED_PATH.exists():
            df = pd.read_excel(str(EVAL_DATASET_LABELED_PATH), engine='openpyxl')
        else:
            raise FileNotFoundError("No labeled data found for tuning.")
            
    df = df.dropna(subset=["relevance"])
    df["relevance"] = df["relevance"].astype(int)
    
    available_features = [c for c in FEATURE_COLS if c in df.columns]
    X = df[available_features].values.astype(np.float32)
    y = df["relevance"].values.astype(np.int32)
    
    if len(X) < 20:
        print("[TUNE] Too few samples for meaningful tuning. Need at least 20.")
        return None
        
    from sklearn.model_selection import train_test_split
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    train_groups = np.array([len(X_train)])
    val_groups = np.array([len(X_val)])
    
    train_set = lgb.Dataset(X_train, label=y_train, group=train_groups, feature_name=available_features)
    val_set = lgb.Dataset(X_val, label=y_val, group=val_groups, feature_name=available_features, reference=train_set)
    
    def objective(trial):
        params = {
            "objective": "lambdarank",
            "metric": "ndcg",
            "ndcg_eval_at": [1, 3, 5],
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 15, 63),
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "min_child_samples": trial.suggest_int("min_child_samples", 1, max(2, len(X_train)//10)),
            "feature_fraction": trial.suggest_float("feature_fraction", 0.5, 1.0),
            "bagging_fraction": trial.suggest_float("bagging_fraction", 0.5, 1.0),
            "bagging_freq": trial.suggest_int("bagging_freq", 1, 7),
            "feature_pre_filter": False,
            "verbose": -1,
            "seed": 42,
            "label_gain": [0, 1, 3, 7],
        }
        
        evals_result = {}
        model = lgb.train(
            params,
            train_set,
            num_boost_round=150,
            valid_sets=[val_set],
            valid_names=["valid"],
            callbacks=[
                lgb.early_stopping(stopping_rounds=15, verbose=False),
                lgb.record_evaluation(evals_result)
            ],
        )
        
        # Get best ndcg@3
        try:
            best_score = max(evals_result["valid"]["ndcg@3"])
        except Exception:
            best_score = 0.0
        return best_score
        
    study = optuna.create_study(direction="maximize")
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
    
    print(f"\n[OPTUNA] Best trial:")
    print(f"  Value (NDCG@3): {study.best_trial.value:.4f}")
    print(f"  Params: ")
    for key, value in study.best_trial.params.items():
        print(f"    {key}: {value}")
        
    # Generate visualization
    try:
        import plotly
        import optuna.visualization as vis
        vis_dir = BASE_DIR / "visualization"
        os.makedirs(vis_dir, exist_ok=True)
        
        fig1 = vis.plot_optimization_history(study)
        fig1.write_image(str(vis_dir / "optuna_history.png"))
        
        fig2 = vis.plot_param_importances(study)
        fig2.write_image(str(vis_dir / "optuna_param_importances.png"))
        print(f"[OPTUNA] Visualizations saved to {vis_dir}")
    except Exception as e:
        print(f"[OPTUNA] Failed to generate visualizations: {e}")
        
    return study.best_trial.params


def analyze_model():
    """Analyze the trained model and print insights."""
    model, feature_names = load_model()
    if model is None:
        print("[ERROR] No trained model found. Run training first.")
        return None
    
    importance_gain = model.feature_importance(importance_type='gain')
    importance_split = model.feature_importance(importance_type='split')
    total_gain = importance_gain.sum()
    
    print("=" * 65)
    print("  LambdaMART Model Analysis")
    print("=" * 65)
    print(f"\n  Number of trees: {model.num_trees()}")
    print(f"  Features used: {len(feature_names)}")
    
    print(f"\n  Feature Importance (sorted by gain):")
    print(f"  {'Feature':35s} {'Weight':>8s} {'Splits':>8s}")
    print(f"  {'-'*35} {'-'*8} {'-'*8}")
    
    pairs = sorted(
        zip(feature_names, importance_gain, importance_split),
        key=lambda x: x[1], reverse=True
    )
    
    for fname, gain, split in pairs:
        w = gain / total_gain if total_gain > 0 else 0
        bar = "#" * int(w * 40)
        print(f"  {fname:35s} {w:8.4f} {int(split):8d}  {bar}")
    
    # Interpret top features
    print(f"\n  Key Insights:")
    top_3 = [p[0] for p in pairs[:3]]
    print(f"  > Top 3 most important features: {', '.join(top_3)}")
    
    if "f_skill_x_exp" in top_3 or "f_skill_x_role" in top_3:
        print(f"  > Model learned INTERACTION effects (non-linear!)")
        print(f"    This means skill importance VARIES by experience/role level")
    
    if "f_domain_match" in top_3:
        print(f"  > Domain matching is critical for accurate ranking")
    
    return {
        "feature_names": feature_names,
        "importance": dict(zip(feature_names, importance_gain.tolist())),
    }


# ─── CLI ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m scoring.weight_learner generate   # Generate eval template")
        print("  python -m scoring.weight_learner train      # Train from labeled data")
        print("  python -m scoring.weight_learner pseudo     # Train from pseudo labels")
        print("  python -m scoring.weight_learner analyze    # Analyze trained model")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "analyze":
        analyze_model()
    
    elif cmd == "train":
        result = train_lambdamart()
        print(f"\n[DONE] Training complete. Model saved to {result['model_path']}")
    
    elif cmd in ("generate", "pseudo"):
        # These require the full pipeline to be loaded
        print(f"[INFO] Command '{cmd}' requires the full pipeline.")
        print(f"[INFO] Use the web app or call the function from Python:")
        print(f"  from scoring.weight_learner import generate_eval_template")
        print(f"  generate_eval_template(job_info, job_nodes, ...)")
    
    else:
        print(f"Unknown command: {cmd}")
