import random
from utils.text_processing import (
    norm_text, sid, parse_location_city_detail, infer_role_canonical, 
    infer_role_raw, parse_year_range, exp_bucket, parse_salary, 
    salary_bucket_general, _combine_probs
)
from scoring.skill_variants import (
    extract_skills_probabilistic, add_skillraw_nodes_and_links
)
from kg.graph_init import add_node, add_edge

def build_job_nodes(G, df, job_info=None, rdf=None, ex_ns=None):
    """Build job nodes in the graph (and optionally RDF graph)."""
    job_nodes = []
    job_info = job_info or {}

    total = len(df)
    for i, (_, r) in enumerate(df.iterrows()):
        if i % 100 == 0:
            print(f"  [INIT] Processing job {i}/{total}...")
            
        jid = r["job_id"]
        title = r["job_title"]
        company = r["company"]

        job_n = f"job::{sid('job', jid)}"
        job_nodes.append(job_n)

        role_can = infer_role_canonical(title)
        role_raw = infer_role_raw(title)

        role_can_n = f"role_can::{sid('role_can', role_can)}"
        role_raw_n = f"role_raw::{sid('role_raw', role_raw)}"
        comp_n = f"company::{sid('company', company)}"

        # Use the full job title as the display label for job nodes
        # (previously used `role_can` which caused multiple postings to show identical labels)
        job_label = title
        add_node(G, job_n, "JobPosting", job_label, rdf=rdf, ex_ns=ex_ns, job_id=str(jid), url=str(r["job_url"]), role_can=role_can)
        add_node(G, role_can_n, "JobRoleCanonical", role_can, rdf=rdf, ex_ns=ex_ns)
        add_node(G, role_raw_n, "JobRoleRaw", role_raw, rdf=rdf, ex_ns=ex_ns)
        add_node(G, comp_n, "Company", company, rdf=rdf, ex_ns=ex_ns)

        add_edge(G, job_n, role_can_n, "HAS_ROLE_CANONICAL", rdf=rdf, ex_ns=ex_ns)
        add_edge(G, job_n, role_raw_n, "HAS_ROLE_RAW", rdf=rdf, ex_ns=ex_ns)
        add_edge(G, job_n, comp_n, "POSTED_BY", rdf=rdf, ex_ns=ex_ns)

        city, detail = parse_location_city_detail(f"{r['location']} {r['location_detail']}")
        loc_city_n = f"loc::{sid('loc', city)}"
        add_node(G, loc_city_n, "Location", city, rdf=rdf, ex_ns=ex_ns)
        add_edge(G, job_n, loc_city_n, "LOCATED_IN", rdf=rdf, ex_ns=ex_ns)

        e_min, e_max, _ = parse_year_range(r["experience"])
        exp_b = exp_bucket(e_min, e_max)
        exp_n = f"exp_bucket::{sid('exp', exp_b)}"
        add_node(G, exp_n, "ExperienceBucket", exp_b, rdf=rdf, ex_ns=ex_ns)
        add_edge(G, job_n, exp_n, "REQUIRES_EXP_BUCKET", rdf=rdf, ex_ns=ex_ns)

        s_min, s_max, cur, nego = parse_salary(r["salary"])
        sal_b = salary_bucket_general(s_min, s_max, cur, nego)
        sal_n = f"sal_bucket::{sid('sal', sal_b)}"
        add_node(G, sal_n, "SalaryBucket", sal_b, rdf=rdf, ex_ns=ex_ns)
        add_edge(G, job_n, sal_n, "HAS_SALARY_BUCKET", rdf=rdf, ex_ns=ex_ns)

        job_text_full = f"{r['requirements']} {r['job_desc']} {r['benefit']}"
        job_prob_raw, _ = extract_skills_probabilistic(job_text_full)

        raw2can_map, raw2can_best = add_skillraw_nodes_and_links(
            G, job_n, job_text_full, owner_rel_raw="REQUIRES_SKILL_RAW", skip_fuzzy=True
        )

        p_from_raw = {}
        if raw2can_map:
            for raw_phrase, vals in raw2can_map.items():
                for canon, p in vals:
                    p_from_raw.setdefault(canon, []).append(p)
            p_from_raw = {k: _combine_probs(vs) for k, vs in p_from_raw.items()}

        job_prob = dict(job_prob_raw)
        for sk, p_raw in p_from_raw.items():
            prev = job_prob.get(sk, 0.0)
            job_prob[sk] = round(_combine_probs([prev, p_raw]), 3)

        for sk, p in job_prob.items():
            sk_n = f"skill::{sid('skill', sk)}"
            add_node(G, sk_n, "Skill", sk, rdf=rdf, ex_ns=ex_ns)
            add_edge(G, job_n, sk_n, "REQUIRES_SKILL", rdf=rdf, ex_ns=ex_ns, prob=p)

        job_info[job_n] = {
            "job_id": str(jid),
            "title": title,
            "company": company,
            "url": str(r["job_url"]),
            "role_can": role_can,
            "exp_bucket": exp_b,
            "sal_bucket": sal_b,
            "city": city,
            "detail": detail,
            "requirements": str(r.get("requirements", "")),
            "description": str(r.get("job_desc", "")),
            "benefits": str(r.get("benefit", "")),
            "prob_skills_raw": job_prob_raw,
            "prob_skills": job_prob,
            "raw2can": raw2can_map,
            "raw2can_best": raw2can_best,
            "text": norm_text(
                f"{r['job_title']} {r['requirements']} "
                f"{r['job_desc']} {r['benefit']} {r['job_type']}"
            )
        }

    print(f"  [SUCCESS] Finished building {len(df)} job nodes.")
    return job_nodes, job_info

def find_job_node_by_id(G, val):
    if val is None:
        return None

    node = f"job::{sid('job', val)}"
    if G.has_node(node):
        return node

    val_str = str(val)
    for n in G.nodes:
        if G.nodes[n].get("job_id") == val_str:
            return n
    return None

def find_job_node_random(job_nodes, seed=42):
    rnd = random.Random(seed)
    return rnd.choice(job_nodes) if job_nodes else None
def pick_center_node(
    G,
    USER_ID,
    CENTER_MODE,
    scores,
    job_nodes,
    CENTER_JOB_ID=None,
    RANDOM_SEED=42
):
    if CENTER_MODE == "user":
        return USER_ID

    if CENTER_MODE == "top_job":
        return scores[0][0] if scores else job_nodes[0]

    if CENTER_MODE == "job_id":
        return (
            find_job_node_by_id(G, CENTER_JOB_ID)
            or (scores[0][0] if scores else job_nodes[0])
        )

    if CENTER_MODE == "random_job":
        return (
            find_job_node_random(job_nodes, RANDOM_SEED)
            or (scores[0][0] if scores else job_nodes[0])
        )

    return USER_ID