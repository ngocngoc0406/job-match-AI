# -*- coding: utf-8 -*-
"""
Train LambdaMART model for job matching weight optimization.

This script:
1. Loads the job data and builds the knowledge graph
2. Uses a sample CV to generate training features  
3. Creates pseudo-labels OR loads manual labels
4. Trains LambdaMART and saves the model
5. Compares learned vs fixed weights

Usage:
    # Train with pseudo-labels (no manual labeling needed):
    python evaluation/train_model.py --mode pseudo

    # Generate evaluation template for manual labeling:
    python evaluation/train_model.py --mode generate --cv path/to/cv.pdf

    # Train with manually labeled data:
    python evaluation/train_model.py --mode train
    
    # Analyze trained model:
    python evaluation/train_model.py --mode analyze
"""

import sys
import os
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np


def load_pipeline(cv_path=None):
    """Load the full pipeline (graph, job data, TF-IDF, etc.)
    
    Returns all components needed for feature extraction and scoring.
    """
    from config import COL
    from kg.graph_init import init_rdf_graph
    from kg.job_builder import build_job_nodes
    from kg.user_builder import build_user_node
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import normalize
    import networkx as nx
    
    # Load job data
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "merged_jobs.xlsx")
    print(f"[LOAD] Loading job data from {data_path}...")
    df = pd.read_excel(data_path, engine='openpyxl')
    df.rename(columns={v: k for k, v in COL.items()}, inplace=True)
    
    # Init graph
    G = nx.DiGraph()
    
    # Build job nodes
    print("[LOAD] Building job nodes...")
    job_info = {}
    job_nodes, job_info = build_job_nodes(G, df, job_info=job_info)
    
    # Build TF-IDF index (same as web/app.py init_application)
    print("[LOAD] Building TF-IDF index...")
    valid_job_nodes = [j for j in job_nodes if j in job_info]
    texts = [job_info[j]["text"] for j in valid_job_nodes]
    
    try:
        from sentence_transformers import SentenceTransformer
        print("[LOAD] Loading SentenceTransformer model...")
        tfidf = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        print("[LOAD] Embedding job texts...")
        X_dense = tfidf.encode(texts, show_progress_bar=False)
        X = normalize(X_dense)
    except ImportError:
        print("[WARN] sentence-transformers not found. Falling back to TF-IDF.")
        tfidf = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(3, 5),
            min_df=1, max_df=1.0, max_features=12000,
            sublinear_tf=True, lowercase=True
        )
        X = tfidf.fit_transform(texts)
        X = normalize(X)
    IDX = {j: i for i, j in enumerate(valid_job_nodes)}
    
    # Load CV
    cv_text = ""
    if cv_path and os.path.exists(cv_path):
        print(f"[LOAD] Loading CV from {cv_path}...")
        if cv_path.endswith('.pdf'):
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(cv_path)
                cv_text = "\n".join(page.get_text() for page in doc)
                doc.close()
            except Exception:
                try:
                    import pdfplumber
                    with pdfplumber.open(cv_path) as pdf:
                        cv_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
                except Exception as e:
                    print(f"[WARN] Could not read PDF: {e}")
        else:
            with open(cv_path, 'r', encoding='utf-8') as f:
                cv_text = f.read()
    
    if not cv_text:
        # Use a synthetic CV for pseudo-label generation
        print("[LOAD] No CV provided — using synthetic CV for training...")
        cv_text = _generate_synthetic_cv()
    
    # Build user node
    print("[LOAD] Building user node from CV...")
    USER_ID, user_prob, user_city, user_detail, user_raw2can_map, user_raw2can_best = \
        build_user_node(G, cv_text)
    
    from utils.text_processing import norm_text, infer_role_canonical, exp_bucket
    
    user_role_can = infer_role_canonical(cv_text[:500])
    user_exp_bucket = exp_bucket(1, 3)  # Default
    if hasattr(tfidf, 'encode'):
        cv_vec = normalize(tfidf.encode([norm_text(cv_text)]))
    else:
        cv_vec = normalize(tfidf.transform([norm_text(cv_text)]))
    
    pipeline = {
        "G": G,
        "job_info": job_info,
        "job_nodes": job_nodes,
        "user_prob": user_prob,
        "user_city": user_city,
        "user_detail": user_detail,
        "IDX": IDX, "X": X,
        "cv_vec": cv_vec,
        "tfidf": tfidf,
        "user_role_can": user_role_can,
        "user_exp_bucket": user_exp_bucket,
        "user_raw2can_best": user_raw2can_best,
        "user_raw2can_map": user_raw2can_map,
        "cv_text": cv_text,
    }
    
    print(f"[LOAD] Pipeline ready: {len(job_nodes)} jobs, {len(user_prob)} user skills")
    return pipeline


def _generate_synthetic_cv():
    """Generate a synthetic CV for pseudo-label training."""
    return """
    NGUYEN VAN A
    Software Engineer | Ha Noi
    
    SUMMARY
    Experienced software engineer with 3 years of experience in web development
    and data analysis. Passionate about building scalable applications.
    
    SKILLS
    Python, JavaScript, React, NodeJS, SQL, Docker, Git, AWS
    Machine Learning, Data Science, Pandas, NumPy
    
    EXPERIENCE
    Software Engineer - FPT Software (2022-2025)
    - Developed web applications using React and NodeJS
    - Built data pipelines using Python and SQL
    - Deployed services on AWS using Docker
    
    Junior Developer - TMA Solutions (2020-2022)
    - Frontend development with JavaScript and React
    - Database design and optimization with MySQL
    
    PROJECTS
    - E-commerce platform: React, NodeJS, MongoDB
    - Data analytics dashboard: Python, Pandas, Plotly
    
    EDUCATION
    Bachelor of Computer Science - Hanoi University of Science and Technology (2020)
    
    CERTIFICATIONS
    AWS Certified Cloud Practitioner
    """


def run_generate(pipeline, sample_n=100):
    """Generate evaluation template for manual labeling."""
    from scoring.weight_learner import generate_eval_template
    
    path = generate_eval_template(
        job_info=pipeline["job_info"],
        job_nodes=pipeline["job_nodes"],
        user_prob=pipeline["user_prob"],
        user_city=pipeline["user_city"],
        user_detail=pipeline["user_detail"],
        IDX=pipeline["IDX"],
        X=pipeline["X"],
        cv_vec=pipeline["cv_vec"],
        tfidf=pipeline["tfidf"],
        user_role_can=pipeline["user_role_can"],
        user_exp_bucket=pipeline["user_exp_bucket"],
        user_raw2can_best=pipeline["user_raw2can_best"],
        user_raw2can_map=pipeline["user_raw2can_map"],
        cv_text=pipeline["cv_text"],
        sample_n=sample_n,
    )
    
    print(f"\n{'='*60}")
    print(f"  NEXT STEPS:")
    print(f"  1. Open: {path}")
    print(f"  2. Fill the 'relevance' column:")
    print(f"     0 = Irrelevant")
    print(f"     1 = Marginally relevant")
    print(f"     2 = Relevant")
    print(f"     3 = Highly relevant")
    print(f"  3. Save as: evaluation/eval_dataset_labeled.xlsx")
    print(f"  4. Run: python evaluation/train_model.py --mode train")
    print(f"{'='*60}")


def run_pseudo_train(pipeline, n_samples=200):
    """Train with pseudo-labels from current system."""
    from scoring.weight_learner import train_lambdamart
    
    print(f"\n{'='*60}")
    print(f"  TRAINING WITH PSEUDO-LABELS")
    print(f"  (Using current fixed-weight scoring as ground truth)")
    print(f"{'='*60}\n")
    
    result = train_lambdamart(
        use_pseudo=True,
        job_info=pipeline["job_info"],
        job_nodes=pipeline["job_nodes"],
        user_prob=pipeline["user_prob"],
        user_city=pipeline["user_city"],
        user_detail=pipeline["user_detail"],
        IDX=pipeline["IDX"],
        X=pipeline["X"],
        cv_vec=pipeline["cv_vec"],
        tfidf=pipeline["tfidf"],
        user_role_can=pipeline["user_role_can"],
        user_exp_bucket=pipeline["user_exp_bucket"],
        user_raw2can_best=pipeline["user_raw2can_best"],
        user_raw2can_map=pipeline["user_raw2can_map"],
        cv_text=pipeline["cv_text"],
        n_samples=n_samples,
    )
    
    print(f"\n{'='*60}")
    print(f"  TRAINING COMPLETE!")
    print(f"  Model saved to: {result['model_path']}")
    print(f"  Samples used: {result['n_samples']}")
    print(f"{'='*60}")
    
    return result


def run_train():
    """Train with manually labeled data."""
    from scoring.weight_learner import train_lambdamart, EVAL_DATASET_LABELED_PATH
    
    if not os.path.exists(str(EVAL_DATASET_LABELED_PATH)):
        print(f"[ERROR] No labeled data found at: {EVAL_DATASET_LABELED_PATH}")
        print(f"[ERROR] Run with --mode generate first, then label the data.")
        return None
    
    print(f"\n{'='*60}")
    print(f"  TRAINING WITH MANUAL LABELS")
    print(f"  Data: {EVAL_DATASET_LABELED_PATH}")
    print(f"{'='*60}\n")
    
    result = train_lambdamart(labeled_path=str(EVAL_DATASET_LABELED_PATH))
    
    print(f"\n{'='*60}")
    print(f"  TRAINING COMPLETE!")
    print(f"  Model saved to: {result['model_path']}")
    print(f"{'='*60}")
    
    return result


def run_analyze():
    """Analyze the trained model."""
    from scoring.weight_learner import analyze_model
    analyze_model()


def run_optimize(trials=50):
    """Run Optuna hyperparameter optimization."""
    from scoring.weight_learner import tune_lambdamart
    print(f"\n{'='*60}")
    print(f"  RUNNING OPTUNA HYPERPARAMETER TUNING ({trials} trials)")
    print(f"{'='*60}\n")
    tune_lambdamart(n_trials=trials)
    print(f"\n{'='*60}")
    print(f"  OPTIMIZATION COMPLETE")
    print(f"  Check visualization/ directory for plots.")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="Train LambdaMART job matching model")
    parser.add_argument("--mode", choices=["generate", "train", "pseudo", "analyze", "optimize"],
                        required=True, help="Operation mode")
    parser.add_argument("--cv", type=str, default=None,
                        help="Path to CV file (PDF or TXT) for generate/pseudo modes")
    parser.add_argument("--samples", type=int, default=200,
                        help="Number of samples for training (default: 200)")
    parser.add_argument("--trials", type=int, default=50,
                        help="Number of Optuna trials for optimize mode")
    
    args = parser.parse_args()
    
    if args.mode == "analyze":
        run_analyze()
        return
    
    if args.mode == "optimize":
        run_optimize(trials=args.trials)
        return
    
    if args.mode == "train":
        run_train()
        return
    
    # For generate and pseudo modes, we need the full pipeline
    pipeline = load_pipeline(cv_path=args.cv)
    
    if args.mode == "generate":
        run_generate(pipeline, sample_n=args.samples)
    elif args.mode == "pseudo":
        run_pseudo_train(pipeline, n_samples=args.samples)


if __name__ == "__main__":
    main()
