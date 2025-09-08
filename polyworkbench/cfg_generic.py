
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

@dataclass
class BasicBlock:
    name: str
    lines: List[str] = field(default_factory=list)   # text rows to show inside the box
    succs: List[str] = field(default_factory=list)

Blocks = Dict[str, BasicBlock]

# ---------- MiniLang (via your TAC CFG) ----------
def cfg_from_minilang(func_ir) -> Blocks:
    # func_ir is List[TACInstr]
    from compliter.cfg import build_cfg   # you already created this earlier
    blocks_ml = build_cfg(func_ir)       # returns name->BasicBlock(TAC)
    # adapt to generic BasicBlock
    out: Blocks = {}
    for name, b in blocks_ml.items():
        rows = []
        for i in b.instrs:
            rows.append(
                (f"{i.op} " + " ".join(i.args)) if i.dst is None else (f"{i.dst} = {i.op} " + " ".join(i.args))
            )
        out[name] = BasicBlock(name=name, lines=rows, succs=list(b.succs))
    return out

# ---------- Python (bytecode) ----------
def cfg_from_python(code: str) -> Blocks:
    import dis
    instrs = list(dis.get_instructions(code))
    # leaders: first instr, any jump target, next after a jump
    leaders = {instrs[0].offset}
    targets = set(i.argval for i in instrs if i.opname.startswith("JUMP") or "JUMP" in i.opname or i.is_jump_target)
    leaders |= {i.offset for i in instrs if i.is_jump_target}
    for i, ins in enumerate(instrs):
        if "JUMP" in ins.opname or ins.opname in ("RETURN_VALUE",):
            if i + 1 < len(instrs):
                leaders.add(instrs[i+1].offset)
    leaders |= set(t for t in targets if isinstance(t, int))
    leaders = sorted(leaders)

    # map offset -> block name
    name_of = {off: f"B{n}" for n, off in enumerate(leaders)}
    blocks: Blocks = {name: BasicBlock(name) for name in name_of.values()}

    # fill blocks
    cur = None
    for i, ins in enumerate(instrs):
        if ins.offset in name_of:
            cur = blocks[name_of[ins.offset]]
        cur.lines.append(f"{ins.offset:>3}: {ins.opname} {'' if ins.arg is None else ins.argrepr}")
        # edges
        if "JUMP" in ins.opname:
            tgt = ins.argval if isinstance(ins.argval, int) else None
            if tgt in name_of:
                cur.succs.append(name_of[tgt])
            # conditional jumps also fallthrough
            if ins.opname.startswith("POP_JUMP_IF") or ins.opname.startswith("JUMP_IF"):
                if i + 1 < len(instrs):
                    fall = name_of.get(instrs[i+1].offset)
                    if fall: cur.succs.append(fall)
        elif ins.opname == "RETURN_VALUE":
            pass
        else:
            # fallthrough to next leader
            if i + 1 < len(instrs) and instrs[i+1].offset in name_of:
                cur.succs.append(name_of[instrs[i+1].offset])
    # dedupe succs
    for b in blocks.values():
        b.succs = sorted(list(dict.fromkeys(b.succs)))
    return blocks

# ---------- JavaScript (Esprima AST) ----------
def cfg_from_js(code: str) -> Blocks:
    import json, esprima
    ast_obj = esprima.parseScript(code, loc=True)
    root = json.loads(json.dumps(ast_obj, default=lambda o: o.__dict__))

    blocks: Blocks = {}
    counter = 0
    def newb(label=None):
        nonlocal counter
        counter += 1
        name = label or f"B{counter}"
        blocks[name] = BasicBlock(name)
        return name

    def linearize(stmt, cur) -> str:
        """Return the last block name after placing stmt(s) starting in block cur."""
        kind = stmt.get("type")
        if kind == "BlockStatement":
            for s in stmt.get("body", []):
                cur = linearize(s, cur)
            return cur
        if kind == "ExpressionStatement":
            blocks[cur].lines.append(render_expr(stmt.get("expression")))
            return cur
        if kind == "VariableDeclaration":
            for d in stmt.get("declarations", []):
                nm = render_id(d.get("id"))
                init = render_expr(d.get("init")) if d.get("init") else ""
                blocks[cur].lines.append(f"var {nm}" + (f" = {init}" if init else ""))
            return cur
        if kind == "IfStatement":
            cond = render_expr(stmt.get("test"))
            thenB = newb("then")
            elseB = newb("else")
            endB  = newb("endif")
            blocks[cur].lines.append(f"if ({cond}) ?")
            blocks[cur].succs += [thenB, elseB]
            t_end = linearize(stmt.get("consequent"), thenB)
            blocks[t_end].succs.append(endB)
            alt = stmt.get("alternate")
            if alt:
                e_end = linearize(alt, elseB)
                blocks[e_end].succs.append(endB)
            else:
                blocks[elseB].succs.append(endB)
            return endB
        if kind in ("WhileStatement","ForStatement"):
            condB = newb("loop_cond")
            bodyB = newb("loop_body")
            endB  = newb("loop_end")
            blocks[cur].succs.append(condB)
            if kind == "WhileStatement":
                c = render_expr(stmt.get("test"))
            else:
                # ForStatement: init; test; update
                init = render_expr(stmt.get("init")) if stmt.get("init") else ""
                if init: blocks[cur].lines.append(init)
                c = render_expr(stmt.get("test")) if stmt.get("test") else "true"
            blocks[condB].lines.append(f"cond {c}")
            blocks[condB].succs += [bodyB, endB]
            b_end = linearize(stmt.get("body"), bodyB)
            blocks[b_end].succs.append(condB)
            return endB
        if kind == "ReturnStatement":
            val = render_expr(stmt.get("argument")) if stmt.get("argument") else ""
            blocks[cur].lines.append(f"return {val}")
            return cur
        # fallback: dump the type
        blocks[cur].lines.append(kind or "Stmt")
        return cur

    def render_id(node):
        return node.get("name") if node else "?"
    def render_expr(node):
        if not node: return ""
        t = node.get("type")
        if t == "Identifier": return node.get("name")
        if t == "Literal": return repr(node.get("value"))
        if t == "BinaryExpression": return f"{render_expr(node['left'])} {node.get('operator')} {render_expr(node['right'])}"
        if t == "UpdateExpression": return f"{node.get('operator')}{render_expr(node['argument'])}" if node.get("prefix") else f"{render_expr(node['argument'])}{node.get('operator')}"
        if t == "AssignmentExpression": return f"{render_expr(node['left'])} {node.get('operator')} {render_expr(node['right'])}"
        if t == "CallExpression":
            callee = render_expr(node["callee"])
            args = ", ".join(render_expr(a) for a in node.get("arguments", []))
            return f"{callee}({args})"
        return t

    entry = newb("entry")
    prog = root.get("body", [])
    cur = entry
    for s in prog:
        cur = linearize(s, cur)
    return blocks

# ---------- C (pycparser AST) ----------
def cfg_from_c(code: str) -> Blocks:
    from pycparser import c_parser, c_ast
    ast = c_parser.CParser().parse(code)

    blocks: Blocks = {}
    counter = 0
    def newb(label=None):
        nonlocal counter
        counter += 1
        name = label or f"B{counter}"
        blocks[name] = BasicBlock(name)
        return name

    def render(n):
        return n.show(buf=None) if hasattr(n, "show") else type(n).__name__

    def lin_stmt(n, cur):
        if isinstance(n, c_ast.Compound):
            for s in n.block_items or []:
                cur = lin_stmt(s, cur)
            return cur
        if isinstance(n, c_ast.Return):
            blocks[cur].lines.append(f"return {to_src(n.expr)}")
            return cur
        if isinstance(n, c_ast.Assignment):
            blocks[cur].lines.append(f"{to_src(n.lvalue)} {n.op} {to_src(n.rvalue)}")
            return cur
        if isinstance(n, c_ast.If):
            thenB, elseB, endB = newb("then"), newb("else"), newb("endif")
            blocks[cur].lines.append(f"if ({to_src(n.cond)}) ?")
            blocks[cur].succs += [thenB, elseB]
            t_end = lin_stmt(n.iftrue, thenB) if n.iftrue else thenB
            blocks[t_end].succs.append(endB)
            e_end = lin_stmt(n.iffalse, elseB) if n.iffalse else elseB
            blocks[e_end].succs.append(endB)
            return endB
        if isinstance(n, c_ast.While):
            condB, bodyB, endB = newb("loop_cond"), newb("loop_body"), newb("loop_end")
            blocks[cur].succs.append(condB)
            blocks[condB].lines.append(f"cond ({to_src(n.cond)})")
            blocks[condB].succs += [bodyB, endB]
            b_end = lin_stmt(n.stmt, bodyB)
            blocks[b_end].succs.append(condB)
            return endB
        # default: one-liner
        blocks[cur].lines.append(type(n).__name__)
        return cur

    def to_src(node):
        if node is None: return ""
        # very small pretty-printer
        if isinstance(node, c_ast.ID): return node.name
        if isinstance(node, c_ast.Constant): return node.value
        if isinstance(node, c_ast.BinaryOp): return f"{to_src(node.left)} {node.op} {to_src(node.right)}"
        if isinstance(node, c_ast.UnaryOp): return f"{node.op}{to_src(node.expr)}"
        if isinstance(node, c_ast.FuncCall):
            a = ", ".join(to_src(x) for x in (node.args.exprs if node.args else []))
            return f"{to_src(node.name)}({a})"
        return type(node).__name__

    entry = newb("entry")
    # walk top-level: run main() body if present; otherwise flatten all
    def find_main(node):
        for ext in node.ext:
            if isinstance(ext, c_ast.FuncDef) and getattr(ext.decl, "name", "") == "main":
                return ext
        return None

    main = find_main(ast)
    if main:
        cur = lin_stmt(main.body, entry)
    else:
        cur = entry
        for ext in ast.ext:
            cur = lin_stmt(ext, cur)
    return blocks
