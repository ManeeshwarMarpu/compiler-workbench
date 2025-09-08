# compliter/cfg.py
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from .ir import TACInstr

@dataclass
class BasicBlock:
    name: str
    instrs: List[TACInstr] = field(default_factory=list)
    succs: List[str] = field(default_factory=list)

def build_cfg(ir: List[TACInstr]) -> Dict[str, BasicBlock]:
    blocks: Dict[str, BasicBlock] = {}
    current = None

    def ensure(name):
        if name not in blocks:
            blocks[name] = BasicBlock(name)
        return blocks[name]

    # split into blocks
    for ins in ir:
        if ins.label:
            current = ensure(ins.label)
            continue
        if current is None:
            current = ensure("entry")
        current.instrs.append(ins)
        # track control-transfer
        if ins.op == "br":
            # unconditional: br L
            if ins.args:
                current.succs.append(ins.args[0])
            current = None
        elif ins.op == "cbr":
            # conditional: cbr t Ltrue Lfalse
            if len(ins.args) >= 3:
                current.succs.extend([ins.args[1], ins.args[2]])
            current = None
        elif ins.op == "ret":
            current = None

    # link fallthroughs: if a block doesn't end with a jump/ret, assume fallthrough to next label
    labels = [ins.label for ins in ir if ins.label]
    label_to_index = {lab:i for i, lab in enumerate(labels)}
    for i, lab in enumerate(labels):
        b = blocks.get(lab)
        if not b: continue
        if not b.instrs: continue
        last = b.instrs[-1].op
        if last not in ("br","cbr","ret"):
            # fallthrough to next label if any
            if i+1 < len(labels):
                b.succs.append(labels[i+1])
    return blocks
