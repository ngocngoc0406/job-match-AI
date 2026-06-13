import os
import sys
import pandas as pd
import numpy as np

# Force sys.stdout to output in UTF-8
if sys.version_info >= (3, 7):
    sys.stdout.reconfigure(encoding='utf-8')

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from evaluation.train_model import load_pipeline
from scoring.user_job_score import user_job_score, compute_user_job_scores
from scoring.weight_learner import load_model, extract_features, predict_score
from scoring.skill_variants import detect_domain

def run_test():
    # 1. Load pipeline with a synthetic CV
    # Let's test with a CV that is clearly in IT (Software Engineer)
    it_cv = """
    NGUYEN VAN A
    Software Engineer | Ha Noi
    
    SKILLS
    Python, JavaScript, React, NodeJS, SQL, Docker, Git, AWS
    
    EXPERIENCE
    Software Engineer - FPT Software (2022-2025)
    - Developed web applications using React and NodeJS
    """
    
    print("Loading pipeline for IT CV...")
    pipeline = load_pipeline() # will use synthetic CV if not found, let's write it to a temp file
    temp_cv_path = os.path.join(project_root, "scratch", "temp_it_cv.txt")
    with open(temp_cv_path, "w", encoding="utf-8") as f:
        f.write(it_cv)
        
    pipeline = load_pipeline(cv_path=temp_cv_path)
    
    # Let's print out what skills are extracted
    print("\nExtracted skills:", list(pipeline["user_prob"].keys()))
    print("User city:", pipeline["user_city"])
    print("User canonical role:", pipeline["user_role_can"])
    print("User exp bucket:", pipeline["user_exp_bucket"])
    
    # 2. Get top matches using LambdaMART (forces USE_LAMBDAMART = True)
    print("\n--- TOP MATCHES WITH LAMBDAMART SCORING (200 Trees Model) ---")
    import scoring.user_job_score
    scoring.user_job_score.USE_LAMBDAMART = True
    
    scores = compute_user_job_scores(
        pipeline["job_nodes"], pipeline["job_info"], pipeline["user_prob"],
        pipeline["user_city"], pipeline["user_detail"], pipeline["IDX"],
        pipeline["X"], pipeline["cv_vec"], pipeline["tfidf"],
        pipeline["user_role_can"], pipeline["user_exp_bucket"],
        user_raw2can_best=pipeline["user_raw2can_best"],
        user_raw2can_map=pipeline["user_raw2can_map"],
        cv_text=pipeline["cv_text"]
    )
    
    for rank, (job_node, score, explain) in enumerate(scores[:5], start=1):
        job = pipeline["job_info"][job_node]
        print(f"{rank}. Score: {score:.3f} | Title: {job['title']} | Company: {job['company']} | City: {job['city']} | Method: {explain['meta']['scoring_method']}")
        print(f"   Role: {job['role_can']} | Exp: {job['exp_bucket']}")
        print(f"   Components: {explain['components']}")
        print(f"   Matched Skills: {explain['evidence']['skill'].get('matched_skills', [])}")
        print()
        
    # 3. Use fixed weights
    print("\n--- TOP MATCHES WITH FIXED WEIGHTS (config.py) ---")
    scoring.user_job_score.USE_LAMBDAMART = False
    
    scores_fixed = compute_user_job_scores(
        pipeline["job_nodes"], pipeline["job_info"], pipeline["user_prob"],
        pipeline["user_city"], pipeline["user_detail"], pipeline["IDX"],
        pipeline["X"], pipeline["cv_vec"], pipeline["tfidf"],
        pipeline["user_role_can"], pipeline["user_exp_bucket"],
        user_raw2can_best=pipeline["user_raw2can_best"],
        user_raw2can_map=pipeline["user_raw2can_map"],
        cv_text=pipeline["cv_text"]
    )
    
    for rank, (job_node, score, explain) in enumerate(scores_fixed[:5], start=1):
        job = pipeline["job_info"][job_node]
        print(f"{rank}. Score: {score:.3f} | Title: {job['title']} | Company: {job['company']} | City: {job['city']} | Method: {explain['meta']['scoring_method']}")
        print(f"   Role: {job['role_can']} | Exp: {job['exp_bucket']}")
        print(f"   Components: {explain['components']}")
        print(f"   Matched Skills: {explain['evidence']['skill'].get('matched_skills', [])}")
        print()

    # Clean up
    if os.path.exists(temp_cv_path):
        os.remove(temp_cv_path)

if __name__ == "__main__":
    run_test()
