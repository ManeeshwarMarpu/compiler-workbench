# polyworkbench/viz_cfg.py
from graphviz import Digraph
from typing import Dict
from .cfg_generic import BasicBlock

def cfg_graphviz(blocks: Dict[str, BasicBlock]) -> Digraph:
    g = Digraph("CFG", node_attr={"shape":"box","fontname":"Inter"})
    for name, blk in blocks.items():
        body = "\\n".join(blk.lines)
        g.node(name, f"{name}\\n-----\\n{body}" if body else name)
    for name, blk in blocks.items():
        for s in blk.succs:
            if s in blocks:
                g.edge(name, s)
    return g
