from .astnodes import *

class SemaError(Exception): pass

class TypeEnv:
    def __init__(self):
        self.scopes = [ {} ]  # name -> type
    def push(self):
        self.scopes.append({})
    def pop(self):
        self.scopes.pop()
    def declare(self, name:str, typ:str):
        if name in self.scopes[-1]:
            raise SemaError(f"Redeclaration of {name}")
        self.scopes[-1][name] = typ
    def lookup(self, name:str):
        for s in reversed(self.scopes):
            if name in s:
                return s[name]
        raise SemaError(f"Undefined identifier {name}")

class Sema:
    def __init__(self, prog:Program):
        self.prog = prog
        self.funcs = {}

    def analyze(self):
        # collect signatures
        for d in self.prog.decls:
            if isinstance(d, FuncDecl):
                self.funcs[d.name] = ([t for _,t in d.params], d.ret_type)
        if 'main' not in self.funcs:
            raise SemaError("No entry point: fn main() -> int {...}")
        tenv = TypeEnv()
        for d in self.prog.decls:
            if isinstance(d, FuncDecl):
                self._check_func(d, tenv)
        return True

    def _check_func(self, f:FuncDecl, tenv:TypeEnv):
        tenv.push()
        for name, t in f.params:
            tenv.declare(name, t)
        self._check_block(f.body, tenv)
        tenv.pop()

    def _check_block(self, b:Block, tenv:TypeEnv):
        tenv.push()
        for s in b.statements:
            self._check_stmt(s, tenv)
        tenv.pop()

    def _check_stmt(self, s:Node, tenv:TypeEnv):
        if isinstance(s, VarDecl):
            if s.init:
                t = self._check_expr(s.init, tenv)
                if t != s.type_name:
                    raise SemaError(f"Type mismatch for {s.name}: {s.type_name} != {t}")
            tenv.declare(s.name, s.type_name)
        elif isinstance(s, Assign):
            tvar = tenv.lookup(s.name)
            tval = self._check_expr(s.value, tenv)
            if tvar != tval:
                raise SemaError(f"Type mismatch in assignment to {s.name}: {tvar} != {tval}")
        elif isinstance(s, IfStmt):
            t = self._check_expr(s.cond, tenv)
            if t != 'bool':
                raise SemaError("if condition must be bool")
            self._check_block(s.then_block, tenv)
            if s.else_block:
                self._check_block(s.else_block, tenv)
        elif isinstance(s, WhileStmt):
            t = self._check_expr(s.cond, tenv)
            if t != 'bool':
                raise SemaError("while condition must be bool")
            self._check_block(s.body, tenv)
        elif isinstance(s, ReturnStmt):
            if s.value:
                self._check_expr(s.value, tenv)
        elif isinstance(s, Expr):
            self._check_expr(s, tenv)
        else:
            pass

    def _check_expr(self, e:Expr, tenv:TypeEnv) -> str:
        if isinstance(e, Literal):
            if isinstance(e.value, bool):   return 'bool'
            if isinstance(e.value, int):    return 'int'
            if isinstance(e.value, str):    return 'string'
        if isinstance(e, Var):
            return tenv.lookup(e.name)
        if isinstance(e, UnOp):
            t = self._check_expr(e.operand, tenv)
            if e.op == '!':
                if t!='bool': raise SemaError('! expects bool')
                return 'bool'
            if e.op == '-':
                if t!='int': raise SemaError('unary - expects int')
                return 'int'
        if isinstance(e, BinOp):
            lt = self._check_expr(e.left, tenv)
            rt = self._check_expr(e.right, tenv)
            if e.op in ['+','-','*','/']:
                if lt==rt=='int': return 'int'
                raise SemaError('arithmetic expects int')
            if e.op in ['<','>','<=','>=','==','!=']:
                if lt!=rt: raise SemaError('compare type mismatch')
                return 'bool'
            if e.op in ['&&','||']:
                if lt==rt=='bool': return 'bool'
                raise SemaError('logical expects bool')
        if isinstance(e, Call):
            # builtins
            if e.name in ('print','println'):
                for a in e.args:
                    self._check_expr(a, tenv)
                return 'void'
            # user functions: assume int for MVP
            return 'int'
        raise SemaError('Unknown expression')
