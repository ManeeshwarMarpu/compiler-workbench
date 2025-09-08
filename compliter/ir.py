from dataclasses import dataclass
from typing import List, Optional

@dataclass
class TACInstr:
    op: str                 # e.g., 'const', 'add', 'sub', 'br', 'cbr', 'phi', 'call', 'ret', 'mov'
    dst: Optional[str]      # result temp (e.g., t1)
    args: List[str]         # operands (temps or immediates)
    label: Optional[str] = None  # for blocks

def pretty_tac(func_name: str, code: List[TACInstr]) -> str:
    lines = [f"func {func_name}()"]
    for ins in code:
        if ins.label:
            lines.append(f"{ins.label}:")
        lhs = (ins.dst + " = ") if ins.dst else ""
        argstr = ", ".join(ins.args)
        lines.append(f"  {lhs}{ins.op} {argstr}".rstrip())
    return "\n".join(lines)
