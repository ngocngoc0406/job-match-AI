from config import CORE_SKILLS_CANON

def explain_user_job(user_prob, job_prob, user_raw2can=None, job_raw2can=None):
    """Generate XAI explanation for user-job match"""
    if not job_prob:
        return {
            "components": {"skill_coverage": 0.0},
            "evidence": {"matched_skills": [], "missing_skills": []},
            "paths": []
        }

    num = 0.0
    den = 0.0
    matched = []
    missing = []

    for sk, pj in job_prob.items():
        w = 2.0 if sk in CORE_SKILLS_CANON else 1.0
        pu = float(user_prob.get(sk, 0.0))

        den += pj * w

        if pu > 0:
            # Use a smoother contribution function (square root of ratio)
            # This rewards partial matches more than linear min
            if pu < pj:
                rel_sim = (pu / pj) ** 0.5
                contrib = pj * rel_sim * w
            else:
                contrib = pj * w

            num += contrib
            matched.append({
                "skill": sk,
                "user_prob": round(pu, 3),
                "job_prob": round(pj, 3),
                "weight": w,
                "contrib": round(contrib, 4)
            })
        else:
            missing.append({
                "skill": sk,
                "job_prob": round(pj, 3),
                "weight": w
            })

    coverage = num / den if den > 0 else 0.0

    matched.sort(key=lambda x: x["contrib"], reverse=True)
    missing.sort(key=lambda x: x["job_prob"] * x["weight"], reverse=True)

    paths = []
    for m in matched[:5]:
        sk = m['skill']
        raw_evidence = []
        
        if user_raw2can:
            for r, vals in user_raw2can.items():
                for canon, p in vals:
                    if canon == sk:
                        raw_evidence.append((r, p, 'user'))
        if job_raw2can:
            for r, vals in job_raw2can.items():
                for canon, p in vals:
                    if canon == sk:
                        raw_evidence.append((r, p, 'job'))

        raw_evidence.sort(key=lambda x: x[1], reverse=True)
        top_raw = raw_evidence[:2]

        if top_raw:
            for r, p, source in top_raw:
                if source == 'user':
                    paths.append(f"User → HAS_SKILL_RAW → SkillRaw('{r}') → NORMALIZES_TO({p}) → Skill('{sk}') → REQUIRES_SKILL → Job")
                else:
                    paths.append(f"Job → MENTIONS_SKILL_RAW → SkillRaw('{r}') → NORMALIZES_TO({p}) → Skill('{sk}') ← User")
        else:
            paths.append(f"User → HAS_SKILL → {sk} → REQUIRED_BY → Job")

    return {
        "components": {
            "skill_coverage": round(coverage, 3)
        },
        "evidence": {
            "matched_skills": matched,
            "missing_skills": missing
        },
        "paths": paths
    }