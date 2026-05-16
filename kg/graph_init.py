from rdflib import Graph as RDFGraph, Namespace, RDF, RDFS, OWL, Literal
from rdflib.namespace import XSD
from config import RDF_CLASSES, RDF_OBJ_PROPS
import networkx as nx

def init_rdf_graph():
    """Initialize RDF graph"""
    rdf = RDFGraph()
    EX = Namespace("http://example.org/jobKG#")
    rdf.bind("ex", EX)

    for c in RDF_CLASSES:
        rdf.add((EX[c], RDF.type, OWL.Class))

    for p in RDF_OBJ_PROPS:
        rdf.add((EX[p], RDF.type, OWL.ObjectProperty))
    
    rdf.add((EX.SIMILAR_TO, RDF.type, OWL.SymmetricProperty))
    rdf.add((EX.score, RDF.type, OWL.DatatypeProperty))
    rdf.add((EX.score, RDFS.range, XSD.float))
    rdf.add((EX.prob, RDF.type, OWL.DatatypeProperty))
    rdf.add((EX.prob, RDFS.range, XSD.float))
    rdf.add((EX.confidence, RDF.type, OWL.DatatypeProperty))
    rdf.add((EX.confidence, RDFS.range, XSD.float))

    return rdf, EX

def _iri(ex_ns: Namespace, raw_id: str):
    """Sanitize graph identifiers for RDF URIs."""
    return ex_ns[str(raw_id).replace('::', '_').replace('-', '_')]

def add_node(G: nx.DiGraph, nx_id: str, ntype: str, label, rdf=None, ex_ns=None, **props):
    """Add a node to a NetworkX graph and optionally mirror it to RDF."""
    if not G.has_node(nx_id):
        G.add_node(nx_id, ntype=ntype, label=str(label), **props)

        if rdf is not None and ex_ns is not None:
            rdf.add((_iri(ex_ns, nx_id), RDF.type, ex_ns[ntype]))

def add_edge(G: nx.DiGraph, u: str, v: str, rel: str, rdf=None, ex_ns=None, **props):
    """Add an edge to a NetworkX graph and optionally mirror it to RDF."""
    G.add_edge(u, v, rel=rel, **props)

    if rdf is not None and ex_ns is not None:
        if rel in RDF_OBJ_PROPS:
            rdf.add((_iri(ex_ns, u), ex_ns[rel], _iri(ex_ns, v)))

        if 'prob' in props:
            rdf.add((_iri(ex_ns, u), ex_ns.prob, Literal(props['prob'], datatype=XSD.float)))
        if 'score' in props:
            rdf.add((_iri(ex_ns, u), ex_ns.score, Literal(props['score'], datatype=XSD.float)))
