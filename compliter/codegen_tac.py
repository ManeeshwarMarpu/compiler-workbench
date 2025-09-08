from typing import List, Tuple
from .astnodes import *
from .ir import TACInstr

class TACBuilder:
    def __init__(self):
        self.temp_i = 0
        self.label_i = 0
        self.code: List[TACInstr] = []
        self.env_stack: List[dict] = [{}]

    def new_t(self) -> str:
        self.temp_i += 1
        return f"t{self.temp_i}"

    def new_l(self, base="L") -> str:
        self.label_i += 1
        return f"{base}{self.label_i}"

    def emit(self, op, dst=None, *args, label=None):
        self.code.append(TACInstr(op=op, dst=dst, args=list(args), label=label))
        return dst

    def lower_prog(self, prog: Program) -> List[Tuple[str, List[TACInstr]]]:
        out = []
        for d in prog.decls:
            if isinstance(d, FuncDecl):
                self.temp_i = 0
                self.label_i = 0
                self.code = []
                self.env_stack = [{}]
                self.emit("label", None, label="entry")
                self.lower_block(d.body)
                out.append((d.name, list(self.code)))
        return out

    def lower_block(self, b: Block):
        self.env_stack.append({})
        for s in b.statements:
            self.lower_stmt(s)
        self.env_stack.pop()

    def lower_stmt(self, s: Node):
        if isinstance(s, VarDecl):
            if s.init is not None:
                v = self.lower_expr(s.init)
                self.emit("mov", s.name, v)
            else:
                self.emit("mov", s.name, "0")
        elif isinstance(s, Assign):
            v = self.lower_expr(s.value)
            self.emit("mov", s.name, v)
        elif isinstance(s, IfStmt):
            cond = self.lower_expr(s.cond)
            l_then = self.new_l("then")
            l_else = self.new_l("else")
            l_end  = self.new_l("endif")
            self.emit("cbr", None, cond, l_then, l_else)
            self.emit("label", None, label=l_then)
            self.lower_block(s.then_block)
            self.emit("br", None, l_end)
            self.emit("label", None, label=l_else)
            if s.else_block:
                self.lower_block(s.else_block)
            self.emit("label", None, label=l_end)
        elif isinstance(s, WhileStmt):
            l_cond = self.new_l("while_cond")
            l_body = self.new_l("while_body")
            l_end  = self.new_l("while_end")
            self.emit("br", None, l_cond)
            self.emit("label", None, label=l_cond)
            c = self.lower_expr(s.cond)
            self.emit("cbr", None, c, l_body, l_end)
            self.emit("label", None, label=l_body)
            self.lower_block(s.body)
            self.emit("br", None, l_cond)
            self.emit("label", None, label=l_end)
        elif isinstance(s, ReturnStmt):
            if s.value:
                v = self.lower_expr(s.value)
                self.emit("ret", None, v)
            else:
                self.emit("ret", None, "0")
        elif isinstance(s, Expr):
            self.lower_expr(s)

    def lower_expr(self, e: Expr) -> str:
        if isinstance(e, Literal):
            t = self.new_t()
            self.emit("const", t, str(e.value))
            return t
        if isinstance(e, Var):
            t = self.new_t()
            self.emit("mov", t, e.name)
            return t
        if isinstance(e, UnOp):
            v = self.lower_expr(e.operand)
            t = self.new_t()
            op = "neg" if e.op == "-" else "lnot"
            self.emit(op, t, v)
            return t
        if isinstance(e, BinOp):
            l = self.lower_expr(e.left)
            r = self.lower_expr(e.right)
            t = self.new_t()
            opmap = {"+":"add","-":"sub","*":"mul","/":"div",
                     "<":"lt",">":"gt","<=":"le",">=":"ge","==":"eq","!=":"ne",
                     "&&":"land","||":"lor"}
            self.emit(opmap[e.op], t, l, r)
            return t
        if isinstance(e, Call):
            # Lower args then emit call
            args = [self.lower_expr(a) for a in e.args]
            t = self.new_t()
            self.emit("call", t, e.name, *args)
            return t
        raise RuntimeError("unknown expr")
