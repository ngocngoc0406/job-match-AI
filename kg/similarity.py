import numpy as np
from utils.text_processing import norm_text, role_sim, exp_sim, location_match_score
from config import CORE_SKILLS_CANON, SIM_THRESHOLD, CANDIDATES_TOP, TOPK_SIMILAR

def prob_skill_sim_job_job(Aprob: dict, Bprob: dict):
    """Calculate skill probability similarity between two jobs"""
    if not Aprob or not Bprob:
        return 0.0

    keys = set(Aprob.keys()) | set(Bprob.keys())
    num, den = 0.0, 0.0

    for s in keys:
        w = 2.0 if s in CORE_SKILLS_CANON else 1.0
        a = float(Aprob.get(s, 0.0))
        b = float(Bprob.get(s, 0.0))
        num += min(a, b) * w
        den += b * w

    return float(num / den) if den > 0 else 0.0

def text_sim_job_job(j1, j2, IDX, X):
    """Calculate text similarity between two jobs using TF-IDF"""
    if j1 not in IDX or j2 not in IDX:
        return 0.0
    i, j = IDX[j1], IDX[j2]
    return float(X[i].multiply(X[j]).sum())

def sim_score_job_job(j1, j2, job_info, IDX, X):
    """Calculate similarity score between two jobs (from collab.py logic)"""
    a, b = job_info[j1], job_info[j2]

    # Skill probability similarity
    s_skill = prob_skill_sim_job_job(a["prob_skills"], b["prob_skills"])
    
    # Text similarity
    s_text = text_sim_job_job(j1, j2, IDX, X)
    
    # Role similarity
    s_role = role_sim(a["role_can"], b["role_can"])
    
    # Experience similarity
    s_exp = exp_sim(a["exp_bucket"], b["exp_bucket"])
    
    # Location similarity
    s_loc = (
        1.0
        if norm_text(a["city"]) == norm_text(b["city"])
        and a["city"] != "Unknown"
        else 0.0
    )

    # Weights from collab.py
    W = {
        "skill": 0.40,
        "text":  0.35,
        "exp":   0.15,
        "loc":   0.10,
    }

    score = (
        W["skill"] * s_skill +
        W["text"]  * s_text  +
        W["exp"]   * s_exp   +
        W["loc"]   * s_loc
    )

    explain = {
        "skill": round(s_skill, 3),
        "text":  round(s_text, 3),
        "role":  round(s_role, 3),
        "exp":   round(s_exp, 3),
        "loc":   round(s_loc, 3),
    }

    return float(round(score, 3)), explain

def build_job_job_similar_edges(G, valid_job_nodes, job_info, IDX, X):
    """Build SIMILAR_TO edges between jobs based on similarity score (from collab.py logic)"""
    # Remove existing SIMILAR_TO edges
    edges_to_remove = [
        (u, v) for u, v, d in list(G.edges(data=True))
        if d.get("rel") == "SIMILAR_TO"
    ]
    G.remove_edges_from(edges_to_remove)

    sim_edge_count = 0

    for a_idx, j1 in enumerate(valid_job_nodes):
        if j1 not in IDX:
            continue
            
        v = X[a_idx]
        sims = (v @ X.T).toarray().ravel()
        sims[a_idx] = 0.0

        # Get top candidates
        if CANDIDATES_TOP < len(sims):
            cand_pos = np.argpartition(-sims, CANDIDATES_TOP)[:CANDIDATES_TOP]
        else:
            cand_pos = np.arange(len(sims))

        scored = []
        for b_pos in cand_pos:
            j2 = valid_job_nodes[b_pos]
            if j1 == j2 or j2 not in job_info:
                continue

            s, ex = sim_score_job_job(j1, j2, job_info, IDX, X)
            if s >= SIM_THRESHOLD:
                scored.append((j2, s, ex))

        scored.sort(key=lambda x: x[1], reverse=True)

        # Add top TOPK_SIMILAR edges
        for j2, s, ex in scored[:TOPK_SIMILAR]:
            G.add_edge(j1, j2, rel="SIMILAR_TO", score=s, explain=ex)
            G.add_edge(j2, j1, rel="SIMILAR_TO", score=s, explain=ex)
            sim_edge_count += 2

    return sim_edge_count