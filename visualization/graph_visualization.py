# graph_visualization.py
import math
import numpy as np
import networkx as nx
from collections import defaultdict
from config import TOPK_USER_JOB, TOPK_SIMILAR
from kg.user_builder import build_strict_user_job_graph


def clean_focus_layout(H, center_node):
    """
    Create a focused layout with the center node in the middle,
    top-k matches/similar jobs prominently positioned,
    and other entities grouped by type in radial patterns.
    """
    pos = {}
    pos[center_node] = (0.0, 0.0)

    # Determine if center is a User or Job node
    center_is_user = H.nodes[center_node].get("ntype") == "User"

    if center_is_user:
        # User-centric layout: show top matching jobs prominently
        matches = [
            v for u, v, d in H.edges(data=True)
            if u == center_node and d.get("rel") == "MATCHES_JOB"
        ]
        matches = sorted(
            matches,
            key=lambda v: H.edges[center_node, v].get("score", 0),
            reverse=True
        )[:TOPK_USER_JOB]

        # Position top 3 matches prominently
        if len(matches) >= 1: pos[matches[0]] = (-0.8,  0.75)
        if len(matches) >= 2: pos[matches[1]] = ( 0.8,  0.75)
        if len(matches) >= 3: pos[matches[2]] = ( 0.0, -0.85)
    else:
        # Job-centric layout: show similar jobs prominently
        sims = [
            v for u, v, d in H.edges(data=True)
            if u == center_node and d.get("rel") == "SIMILAR_TO"
        ]
        sims = sorted(
            sims,
            key=lambda v: H.edges[center_node, v].get("score", 0),
            reverse=True
        )[:TOPK_SIMILAR]

        # Position top 3 similar jobs prominently
        if len(sims) >= 1: pos[sims[0]] = (-0.8,  0.75)
        if len(sims) >= 2: pos[sims[1]] = ( 0.8,  0.75)
        if len(sims) >= 3: pos[sims[2]] = ( 0.0, -0.85)

    # Group remaining nodes by type
    groups = defaultdict(list)
    for n in H.nodes:
        if n not in pos:  # Skip already positioned nodes
            groups[H.nodes[n].get("ntype", "Other")].append(n)

    def spread(nodes, center_xy, radius, start, end):
        """Position a group of nodes in an arc around a center point"""
        nodes = [n for n in nodes if n not in pos]
        if not nodes:
            return
        if len(nodes) == 1:
            pos[nodes[0]] = (
                center_xy[0] + radius * math.cos(start),
                center_xy[1] + radius * math.sin(start),
            )
            return
        angles = np.linspace(start, end, len(nodes), endpoint=False)
        for n, a in zip(nodes, angles):
            pos[n] = (
                center_xy[0] + radius * math.cos(a),
                center_xy[1] + radius * math.sin(a),
            )

    # Position different node types in structured locations
    spread(groups.get("Company", []),           (-1.1,  0.20), 0.35,  2.5,  3.6)
    spread(groups.get("Location", []),          ( 0.0, -1.15), 0.50, -2.9, -0.2)
    spread(groups.get("ExperienceBucket", []),  ( 1.1,  0.70), 0.30,  0.1,  1.0)
    spread(groups.get("SalaryBucket", []),      ( 1.1, -0.60), 0.30, -1.1, -0.2)
    spread(groups.get("JobRoleCanonical", []),  ( 0.85, 0.05), 0.20, -0.1,  0.1)
    spread(groups.get("JobRoleRaw", []),        ( 0.85,-0.20), 0.20, -0.1,  0.1)
    spread(groups.get("Skill", []),             ( 0.0,  0.0), 1.50,  0.0,  2 * math.pi)
    spread(groups.get("SkillRaw", []),          ( 0.0,  0.0), 1.65,  0.0,  2 * math.pi)

    # Handle any remaining unpositioned nodes with spring layout
    missing = [n for n in H.nodes if n not in pos]
    if missing:
        try:
            sp = nx.spring_layout(H.subgraph(missing), seed=42, k=1.8, iterations=30)
            for n in missing:
                pos[n] = sp[n]
        except:
            # Fallback: random positioning
            import random
            for n in missing:
                pos[n] = (random.uniform(-1, 1), random.uniform(-1, 1))

    # Validate result
    if not isinstance(H, nx.DiGraph):
        raise ValueError("H must be a NetworkX DiGraph")
    if center_node not in H:
        raise ValueError(f"center_node {center_node} not in graph")
    
    return pos
#         )[:TOPK_USER_JOB]

#         if len(recs) >= 1: pos[recs[0]] = (-0.85,  0.80)
#         if len(recs) >= 2: pos[recs[1]] = ( 0.85,  0.80)
#         if len(recs) >= 3: pos[recs[2]] = ( 0.00, -0.95)

#     else:
#         sims = [
#             v for u, v, d in H.edges(data=True)
#             if u == center_node and d.get("rel") == "SIMILAR_TO"
#         ]
#         sims = sorted(
#             sims,
#             key=lambda v: H.edges[center_node, v].get("score", 0),
#             reverse=True
#         )[:TOPK_SIMILAR]

#         if len(sims) >= 1: pos[sims[0]] = (-0.85,  0.80)
#         if len(sims) >= 2: pos[sims[1]] = ( 0.85,  0.80)
#         if len(sims) >= 3: pos[sims[2]] = ( 0.00, -0.95)

#     groups = defaultdict(list)
#     for n in H.nodes:
#         groups[H.nodes[n].get("ntype", "Other")].append(n)

#     def spread(nodes, center_xy, radius, start, end):
#         nodes = [n for n in nodes if n not in pos]
#         if not nodes:
#             return
#         if len(nodes) == 1:
#             pos[nodes[0]] = (
#                 center_xy[0] + radius * math.cos(start),
#                 center_xy[1] + radius * math.sin(start),
#             )
#             return
#         angles = np.linspace(start, end, len(nodes))
#         for n, a in zip(nodes, angles):
#             pos[n] = (
#                 center_xy[0] + radius * math.cos(a),
#                 center_xy[1] + radius * math.sin(a),
#             )

#     spread(groups.get("Company", []), (-1.15,  0.15), 0.35,  2.6,  3.7)
#     spread(groups.get("Location", []), ( 0.00, -1.25), 0.48, -2.8, -0.3)
#     spread(groups.get("ExperienceBucket", []), ( 1.15,  0.85), 0.32,  0.2,  1.1)
#     spread(groups.get("SalaryBucket", []),     ( 1.15, -0.60), 0.32, -1.2, -0.2)
#     spread(groups.get("JobRoleCanonical", []), ( 0.95,  0.10), 0.25,  0.0,  0.0)
#     spread(groups.get("JobRoleRaw", []),       ( 0.95, -0.15), 0.25,  0.0,  0.0)
#     spread(groups.get("Skill", []),            ( 0.00,  0.00), 1.45,  0.0,  2 * math.pi)

#     missing = [n for n in H.nodes if n not in pos]
#     if missing:
#         sp = nx.spring_layout(H.subgraph(missing), seed=42, k=1.6)
#         for n in missing:
#             pos[n] = sp[n]

#     return pos
