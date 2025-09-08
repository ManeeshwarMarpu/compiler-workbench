from .astnodes import *

class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value

class Env:
    def __init__(self, parent=None):
        self.parent = parent
        self.vars = {}
    def set(self, name, val):
        if name in self.vars:
            self.vars[name]=val
            return
        if self.parent:
            try:
                self.parent.set(name,val)
                return
            except KeyError:
                pass
        self.vars[name]=val
    def get(self, name):
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.get(name)
        raise KeyError(name)

class Interpreter:
    def __init__(self, prog:Program):
        self.prog = prog
        self.funcs = { d.name:d for d in prog.decls if isinstance(d, FuncDecl) }

    def call(self, name, args):
        if name == 'print':
            print(*args, end='')
            return 0
        if name == 'println':
            print(*args)
            return 0
        f = self.funcs[name]
        env = Env()
        for (pname,_), aval in zip(f.params, args):
            env.set(pname, aval)
        try:
            self.exec_block(f.body, env)
        except ReturnSignal as rs:
            return rs.value
        return 0

    def exec_block(self, b:Block, env:Env):
        local = Env(env)
        for st in b.statements:
            self.exec_stmt(st, local)

    def exec_stmt(self, st:Node, env:Env):
        if isinstance(st, VarDecl):
            val = None
            if st.init is not None:
                val = self.eval(st.init, env)
            env.set(st.name, val)
        elif isinstance(st, Assign):
            val = self.eval(st.value, env)
            env.set(st.name, val)
        elif isinstance(st, IfStmt):
            c = self.eval(st.cond, env)
            if c:
                self.exec_block(st.then_block, env)
            elif st.else_block:
                self.exec_block(st.else_block, env)
        elif isinstance(st, WhileStmt):
            while self.eval(st.cond, env):
                self.exec_block(st.body, env)
        elif isinstance(st, ReturnStmt):
            v = self.eval(st.value, env) if st.value else 0
            raise ReturnSignal(v)
        elif isinstance(st, Expr):
            self.eval(st, env)

    def eval(self, e:Expr, env:Env):
        if isinstance(e, Literal):
            return e.value
        if isinstance(e, Var):
            return env.get(e.name)
        if isinstance(e, UnOp):
            v = self.eval(e.operand, env)
            if e.op=='-': return -v
            if e.op=='!': return not bool(v)
        if isinstance(e, BinOp):
            if e.op in ['+','-','*','/','<','>','<=','>=','==','!=','&&','||']:
                l = self.eval(e.left, env)
                if e.op=='&&':
                    return bool(l) and bool(self.eval(e.right, env))
                if e.op=='||':
                    return bool(l) or bool(self.eval(e.right, env))
                r = self.eval(e.right, env)
                ops = {
                    '+': lambda a,b: a+b,
                    '-': lambda a,b: a-b,
                    '*': lambda a,b: a*b,
                    '/': lambda a,b: a//b,
                    '<': lambda a,b: a<b,
                    '>': lambda a,b: a>b,
                    '<=': lambda a,b: a<=b,
                    '>=': lambda a,b: a>=b,
                    '==': lambda a,b: a==b,
                    '!=': lambda a,b: a!=b,
                }
                return ops[e.op](l,r)
        if isinstance(e, Call):
            args = [self.eval(a, env) for a in e.args]
            return self.call(e.name, args)
        raise RuntimeError("Unknown expression")

    def run(self):
        return self.call('main', [])
