from utils.text_processing import norm_text, role_sim, exp_sim, location_match_score
from scoring.xai import explain_user_job
from scoring.skill_variants import detect_domain
from config import (
    W_SKILL, W_ROLE, W_EXP, W_LOC, W_TEXT, W_SAL,
    DOMAIN_MISMATCH_PENALTY, USE_LAMBDAMART
)
import numpy as np

# ─── LambdaMART Integration ──────────────────────────────────────────────────
# Try to load the trained LambdaMART model at import time.
# If available, use learned weights instead of fixed weights.
# Falls back to fixed weights if no model exists.
_LAMBDAMART_MODEL = None
_LAMBDAMART_FEATURES = None

def _load_lambdamart():
    """Load LambdaMART model (lazy, called once)."""
    global _LAMBDAMART_MODEL, _LAMBDAMART_FEATURES
    try:
        from scoring.weight_learner import load_model
        _LAMBDAMART_MODEL, _LAMBDAMART_FEATURES = load_model()
        if _LAMBDAMART_MODEL is not None:
            print("[SCORING] LambdaMART model loaded — using LEARNED weights")
        else:
            print("[SCORING] No LambdaMART model found — using FIXED weights")
    except Exception as e:
        print(f"[SCORING] LambdaMART unavailable ({e}) — using FIXED weights")

_load_lambdamart()

def user_job_score(user_prob, user_city, user_detail, job_node, job_info, 
                   IDX, X, cv_vec, tfidf, user_role_can, user_exp_bucket,
                   pseudo_text="", user_raw2can_best=None, user_raw2can_map=None,
                   cv_domain="general"):
    """Calculate user-job match score.
    
    Uses LambdaMART model if available, otherwise falls back to fixed weights.
    """
    if job_node not in job_info:
        return 0.0, {"error": "job_not_in_job_info"}

    job = job_info[job_node]

    if user_raw2can_best:
        user_prob_max_raw = {
            canon: float(p)
            for canon, (_, p) in user_raw2can_best.items()
            if isinstance(p, (int, float))
        }
    else:
        user_prob_max_raw = user_prob

    xai = explain_user_job(user_prob_max_raw, job["prob_skills"], 
                          user_raw2can=user_raw2can_map, job_raw2can=job.get('raw2can'))
    s_skill = xai["components"]["skill_coverage"]
    ex_skill = xai["evidence"]

    i = IDX[job_node]
    if pseudo_text:
        from sklearn.preprocessing import normalize
        if hasattr(tfidf, 'encode'):
            pseudo_vec = normalize(tfidf.encode([norm_text(pseudo_text)]))
        else:
            pseudo_vec = normalize(tfidf.transform([norm_text(pseudo_text)]))
        if hasattr(pseudo_vec, 'toarray'):
            s_text = float((pseudo_vec @ X[i].T).sum())
        else:
            s_text = float(np.dot(pseudo_vec[0], X[i]))
    else:
        if hasattr(cv_vec, 'toarray'):
            s_text = float((cv_vec @ X[i].T).sum())
        else:
            s_text = float(np.dot(cv_vec[0], X[i]))

    s_loc, ex_loc = location_match_score(
        user_city, user_detail,
        job["city"], job["detail"]
    )

    s_role = role_sim(user_role_can, job["role_can"])
    s_exp = exp_sim(user_exp_bucket, job["exp_bucket"])
    
    try:
        s_sal = 1.0 if job["sal_bucket"] != "Salary_Unknown" else 0.0
    except:
        s_sal = 0.0

    # Domain detection for features
    job_text = f"{job['title']} {job.get('description', '')} {job.get('requirements', '')}"
    job_domain = detect_domain(job_text)

    # ─── Score calculation ────────────────────────────────────────────────
    scoring_method = "fixed"
    
    if USE_LAMBDAMART and _LAMBDAMART_MODEL is not None:
        # Use LambdaMART learned model
        try:
            from scoring.weight_learner import extract_features, predict_score
            
            features = extract_features(
                s_skill=s_skill, s_text=s_text, s_loc=s_loc,
                s_role=s_role, s_exp=s_exp, s_sal=s_sal,
                explain_data=xai, cv_domain=cv_domain, job_domain=job_domain
            )
            
            score = predict_score(_LAMBDAMART_MODEL, features)
            scoring_method = "lambdamart"
        except Exception as e:
            # Fallback to fixed weights on any error
            score = None
            scoring_method = "fixed"
    
    if scoring_method == "fixed":
        # Fixed linear weights (configurable via `config.py`)
        W = {
            'skill': W_SKILL,
            'text': W_TEXT,
            'location': W_LOC,
            'role': W_ROLE,
            'exp': W_EXP,
            'sal': W_SAL,
        }

        score = (
            W['skill'] * s_skill +
            W['text'] * s_text +
            W['location'] * s_loc +
            W['role'] * s_role +
            W['exp'] * s_exp +
            W['sal'] * s_sal
        )

        # Domain Filtering logic (only for fixed weights — LambdaMART handles this via features)
        if cv_domain != "general" and cv_domain != job_domain:
            score *= float(DOMAIN_MISMATCH_PENALTY)

    explain = {
        "components": {
            "skill": round(s_skill, 3),
            "text": round(s_text, 3),
            "location": round(s_loc, 3),
            "role": round(s_role, 3),
            "experience": round(s_exp, 3),
            "salary": round(s_sal, 3),
        },
        "evidence": {
            "skill": ex_skill,
            "location": ex_loc,
        },
        "meta": {
            "user_city": user_city,
            "job_city": job["city"],
            "job_role": job["role_can"],
            "exp_bucket": job["exp_bucket"],
            "sal_bucket": job["sal_bucket"],
            "scoring_method": scoring_method,
        }
    }

    return float(round(score, 3)), explain

def compute_user_job_scores(job_nodes, job_info, user_prob, user_city, user_detail,
                            IDX, X, cv_vec, tfidf, user_role_can, user_exp_bucket,
                            user_raw2can_best=None, user_raw2can_map=None,
                            cv_text=""):
    """Compute scores for all jobs"""
    scores = []
    valid_job_nodes = [j for j in job_nodes if j in job_info]
    
    cv_domain = detect_domain(cv_text) if cv_text else "general"

    for j in valid_job_nodes:
        sc, ex = user_job_score(
            user_prob, user_city, user_detail, j, job_info,
            IDX, X, cv_vec, tfidf, user_role_can, user_exp_bucket,
            user_raw2can_best=user_raw2can_best,
            user_raw2can_map=user_raw2can_map,
            cv_domain=cv_domain
        )
        scores.append((j, sc, ex))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores