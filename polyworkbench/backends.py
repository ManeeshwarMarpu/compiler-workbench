# polyglot/backends.py
import subprocess, tempfile, os, sys, json, ast, textwrap
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from .lexers import pygments_tokens

# ---------- Base ----------
@dataclass
class Result:
    tokens: Optional[List[Dict[str,Any]]] = None
    ast_repr: Optional[Any] = None
    ir_text: Optional[str] = None
    stdout: str = ""
    stderr: str = ""
    ok: bool = True
    stage_error: Optional[str] = None

class Backend:
    name:str
    def tokens(self, code:str)->Optional[List[Dict[str,Any]]]: ...
    def ast(self, code:str)->Optional[Any]: ...
    def ir(self, code:str)->Optional[str]: ...
    def run(self, code:str)->Result: ...

# ---------- MiniLang (uses your pipeline) ----------
from compliter.parser import Parser, ParseError
from compliter.sema import Sema, SemaError
from compliter.interpreter import Interpreter
from compliter.inspectors import tokenize as ml_tokens, ast_to_dict as ml_ast_to_dict, ast_ascii_tree
from compliter.codegen_tac import TACBuilder
from compliter.ir import pretty_tac

class MiniLangBackend(Backend):
    name="MiniLang"
    def tokens(self, code:str):
        return ml_tokens(code)
    def ast(self, code:str):
        return ml_ast_to_dict(Parser(code).parse())
    def ir(self, code:str):
        prog = Parser(code).parse()
        Sema(prog).analyze()
        tb = TACBuilder()
        funcs = tb.lower_prog(prog)
        chunks = [pretty_tac(n,c) for n,c in funcs]
        return "\n\n".join(chunks)
    def run(self, code:str)->Result:
        r = Result()
        try:
            r.tokens = self.tokens(code)
            prog = Parser(code).parse()
            r.ast_repr = ml_ast_to_dict(prog)
            Sema(prog).analyze()
            tb = TACBuilder()
            funcs = tb.lower_prog(prog)
            r.ir_text = "\n\n".join(pretty_tac(n,c) for n,c in funcs)
            from io import StringIO
            import contextlib
            buf = StringIO()
            with contextlib.redirect_stdout(buf):
                rc = Interpreter(prog).run()
            r.stdout = buf.getvalue()
            r.ok = True
        except (ParseError, SemaError, Exception) as e:
            r.ok = False
            r.stage_error = f"{type(e).__name__}: {e}"
        return r

# ---------- Python ----------
class PythonBackend(Backend):
    name="Python"
    def tokens(self, code:str):
        return pygments_tokens(code, "python")
    def ast(self, code:str):
        tree = ast.parse(code, mode="exec")
        return ast.dump(tree, indent=2)
    def ir(self, code:str):
        # Python doesn't expose IR; show bytecode as a proxy
        import dis
        c = compile(code, "<stdin>", "exec")
        return dis.Bytecode(c).dis()
    def run(self, code:str)->Result:
        r = Result()
        try:
            r.tokens = self.tokens(code)
            r.ast_repr = self.ast(code)
            r.ir_text = self.ir(code)
            out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
            r.stdout, r.stderr = out.stdout, out.stderr
            r.ok = (out.returncode == 0)
            if not r.ok:
                r.stage_error = f"exit {out.returncode}"
        except Exception as e:
            r.ok = False
            r.stage_error = str(e)
        return r

# ---------- JavaScript (Node) ----------
class JSBackend(Backend):
    name="JavaScript"
    def tokens(self, code:str):
        return pygments_tokens(code, "javascript")
    def ast(self, code:str):
        import esprima
        return json.dumps(esprima.parseScript(code, loc=True), indent=2, default=lambda o:o.__dict__)
    def ir(self, code:str):
        # JS has no standard IR; skip
        return None
    def run(self, code:str)->Result:
        r = Result()
        try:
            r.tokens = self.tokens(code)
            r.ast_repr = self.ast(code)
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
                f.write(code); path = f.name
            out = subprocess.run(["node", path], capture_output=True, text=True)
            r.stdout, r.stderr = out.stdout, out.stderr
            r.ok = (out.returncode == 0)
            if not r.ok: r.stage_error = f"exit {out.returncode}"
        except Exception as e:
            r.ok = False; r.stage_error = str(e)
        finally:
            try: os.remove(path)
            except: pass
        return r

# ---------- C (clang) ----------
class CBackend(Backend):
    name="C"
    def tokens(self, code:str):
        return pygments_tokens(code, "c")
    def ast(self, code:str):
        # pycparser gives an AST for C (without system headers)
        from pycparser import c_parser
        return str(c_parser.CParser().parse(code))
    def ir(self, code:str):
        with tempfile.TemporaryFile() as _:
            with tempfile.NamedTemporaryFile("w", suffix=".c", delete=False) as f:
                f.write(code); cpath = f.name
            llpath = cpath + ".ll"
            cmd = ["clang", "-S", "-emit-llvm", cpath, "-o", llpath]
            out = subprocess.run(cmd, capture_output=True, text=True)
            if out.returncode != 0: return f"clang error:\n{out.stderr}"
            with open(llpath, "r", encoding="utf-8") as h: ir = h.read()
            os.remove(cpath); os.remove(llpath)
            return ir
    def run(self, code:str)->Result:
        r = Result()
        try:
            r.tokens = self.tokens(code)
            r.ast_repr = self.ast(code)
            r.ir_text = self.ir(code)
            with tempfile.NamedTemporaryFile("w", suffix=".c", delete=False) as f:
                f.write(code); cpath = f.name
            exe = cpath + ".exe" if os.name=="nt" else cpath + ".out"
            out = subprocess.run(["clang", cpath, "-O0", "-o", exe], capture_output=True, text=True)
            if out.returncode != 0:
                r.ok=False; r.stage_error = out.stderr; return r
            out = subprocess.run([exe], capture_output=True, text=True)
            r.stdout, r.stderr = out.stdout, out.stderr
            r.ok = (out.returncode == 0)
        except Exception as e:
            r.ok=False; r.stage_error = str(e)
        finally:
            try: os.remove(cpath); os.remove(exe)
            except: pass
        return r

# registry
BACKENDS = {
    "MiniLang": MiniLangBackend(),
    "Python":   PythonBackend(),
    "JavaScript": JSBackend(),
    "C": CBackend(),
}
