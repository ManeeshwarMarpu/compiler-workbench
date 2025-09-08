# polyworkbench/viz.py
from graphviz import Digraph
import ast

# ---------- Python AST -> Graphviz ----------
def py_ast_graphviz(tree: ast.AST) -> Digraph:
    g = Digraph("pyAST", node_attr={"shape": "box", "fontname": "Inter"})
    counter = 0

    def add(n):
        nonlocal counter
        counter += 1
        nid = f"n{counter}"
        label = type(n).__name__
        g.node(nid, label)
        for child in ast.iter_child_nodes(n):
            cid = add(child)
            g.edge(nid, cid)
        return nid

    add(tree)
    return g

# ---------- JS (esprima) AST (dict-like) -> Graphviz ----------
def js_ast_graphviz(root_dict) -> Digraph:
    g = Digraph("jsAST", node_attr={"shape": "box", "fontname": "Inter"})
    counter = 0

    def add(node):
        nonlocal counter
        counter += 1
        nid = f"n{counter}"
        # node is a dict with a "type" key (esprima)
        label = str(node.get("type", "Node"))
        g.node(nid, label)

        for k, v in node.items():
            if k in ("range", "loc", "raw"):  # skip noisy meta
                continue
            if isinstance(v, dict):
                cid = add(v)
                g.edge(nid, cid, label=k)
            elif isinstance(v, list):
                for i, item in enumerate(v):
                    if isinstance(item, dict):
                        cid = add(item)
                        g.edge(nid, cid, label=f"{k}[{i}]")
        return nid

    add(root_dict)
    return g

# ---------- C (pycparser) AST -> Graphviz ----------
def c_ast_graphviz(root) -> Digraph:
    # root is a pycparser.c_ast.Node
    from pycparser.c_ast import Node
    g = Digraph("cAST", node_attr={"shape": "box", "fontname": "Inter"})
    counter = 0

    def add(n: Node):
        nonlocal counter
        counter += 1
        nid = f"n{counter}"
        label = type(n).__name__
        g.node(nid, label)
        for field_name, child in n.children():
            cid = add(child)
            g.edge(nid, cid, label=field_name)
        return nid

    add(root)
    return g
