from __future__ import annotations
from typing import Any, Dict, List, Tuple
from .lexer import Lexer
from .astnodes import *
from graphviz import Digraph
# --------- LEXER ----------
def tokenize(text: str) -> List[Dict[str, Any]]:
    return [ { "kind": t.kind, "lexeme": t.lexeme, "line": t.line, "col": t.col }
             for t in Lexer(text).tokens() ]

# --------- AST helpers ----------
def ast_to_dict(node: Node) -> Dict[str, Any]:
    # turn dataclass AST into a plain dict for JSON display
    if isinstance(node, list):
        return [ast_to_dict(n) for n in node]
    if not hasattr(node, "__dataclass_fields__"):
        return node
    d = {"_type": node.__class__.__name__, "line": node.line, "col": node.col}
    for f in node.__dataclass_fields__.keys():
        if f in ("line","col"): continue
        v = getattr(node, f)
        if isinstance(v, Node):
            d[f] = ast_to_dict(v)
        elif isinstance(v, list):
            d[f] = [ast_to_dict(x) if isinstance(x, Node) else x for x in v]
        else:
            d[f] = v
    return d

def _tree_lines(node: Node, prefix: str = "", is_last: bool = True) -> List[str]:
    name = node.__class__.__name__
    head = f"{prefix}{'└─' if is_last else '├─'}{name}"
    lines = [head]
    new_prefix = f"{prefix}{'  ' if is_last else '│ '}"
    children: List[Tuple[str, Any]] = []
    for f in getattr(node, "__dataclass_fields__", {}):
        if f in ("line","col"): continue
        v = getattr(node, f)
        if isinstance(v, Node):
            children.append((f, v))
        elif isinstance(v, list) and any(isinstance(x, Node) for x in v):
            for i, x in enumerate(v):
                if isinstance(x, Node):
                    children.append((f if i==0 else f, x))
    for i, (fname, child) in enumerate(children):
        label = f" ({fname})"
        # insert label on child line
        sub = _tree_lines(child, new_prefix, i == len(children) - 1)
        sub[0] = sub[0] + label
        lines.extend(sub)
    return lines

def ast_ascii_tree(root: Node) -> str:
    return "\n".join(_tree_lines(root, "", True))



def ast_graphviz(root: Node) -> Digraph:
    g = Digraph("AST", node_attr={"shape": "box", "fontname": "Inter"})
    counter = 0
    def add(n):
        nonlocal counter
        counter += 1
        nid = f"n{counter}"
        label = n.__class__.__name__
        g.node(nid, label)
        # children
        for f in getattr(n, "__dataclass_fields__", {}):
            if f in ("line","col"): continue
            v = getattr(n, f)
            def link(child):
                cid = add(child)
                g.edge(nid, cid, label=f)
            if isinstance(v, Node):
                link(v)
            elif isinstance(v, list):
                for i,x in enumerate(v):
                    if isinstance(x, Node):
                        cid = add(x)
                        g.edge(nid, cid, label=f"{f}[{i}]")
        return nid
    add(root)
    return g