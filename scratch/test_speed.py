import sys
import os
import time
import pandas as pd
import networkx as nx

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from kg.job_builder import build_job_nodes
from kg.graph_init import init_rdf_graph

def test_init_speed():
    excel_path = 'merged_jobs.xlsx'
    if not os.path.exists(excel_path):
        print("Excel file not found")
        return

    print("Loading Excel...")
    df = pd.read_excel(excel_path).fillna("").iloc[:100] # Test with 100 jobs
    print(f"Loaded {len(df)} jobs.")

    G = nx.DiGraph()
    job_info = {}
    
    start_time = time.time()
    print("Building job nodes (optimized)...")
    job_nodes, job_info = build_job_nodes(G, df, job_info)
    end_time = time.time()

    print(f"Time taken for 100 jobs: {end_time - start_time:.2f} seconds")
    print(f"Estimated time for 1000 jobs: {(end_time - start_time) * 10:.2f} seconds")

if __name__ == "__main__":
    test_init_speed()
