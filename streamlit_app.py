# streamlit_app.py
import re, time, json, traceback, inspect
import streamlit as st
from streamlit_ace import st_ace

from polyworkbench.backends import BACKENDS

# ---------- Session state init (must be BEFORE UI renders) ----------
st.session_state.setdefault("ace_annotations", [])

# ---------- Tab indices ----------
TAB_TOKENS = 0
TAB_AST    = 1
TAB_IR     = 2
TAB_CFG    = 3
TAB_RUN    = 4
TAB_DEBUG  = 5

# ---------- Helpers ----------
def timeit(fn):
    t0 = time.perf_counter()
    out = fn()
    return out, (time.perf_counter() - t0) * 1000.0  # ms


TRACE_LINE_RE = re.compile(
    r'File\s+"(?:<string>|<stdin>|.+?)",\s+line\s+(\d+)'  # Python traceback lines
)
LINECOL_RE = re.compile(
    r'at\s+(\d+):(\d+)|line\s+(\d+)\s*col\s*(\d+)|line\s+(\d+)'  # generic fallbacks
)

def extract_line_col(msg: str):
    s = str(msg) or ""
    m = TRACE_LINE_RE.search(s)
    if m:
        return int(m.group(1)), 1
    
    m = LINECOL_RE.search(s)
    if not m:
        return None, None
    groups = [g for g in m.groups() if g]
    if len(groups) == 1:
        return int(groups[0]), 1
    return int(groups[0]), int(groups[1])


perf = {}  # collected timings

def perf_badge(*pairs):
    if not pairs:
        return
    cols = st.columns(len(pairs))
    for c, (label, ms) in zip(cols, pairs):
        with c:
            st.metric(label, f"{ms:.1f} ms")

# ---------- Page ----------
st.set_page_config(page_title="Polyglot Compiler Workbench", layout="wide")
st.title("🧪 Polyglot Compiler Workbench")
st.caption("Tokens → AST/IR (when available) → CFG → Run → Debug  •  MiniLang, Python, JavaScript, C")

# ---------- Sidebar (Ace editor) ----------
with st.sidebar:
    st.header("Controls")
    lang = st.selectbox("Language", list(BACKENDS.keys()), index=0)

    lang_map = {"MiniLang": "text", "Python": "python", "JavaScript": "javascript", "C": "c_cpp"}
    DEFAULTS = {
        "MiniLang": "fn main() -> int {\n  println(1+2);\n  return 0;\n}\n",
        "Python": "print(1+2)\n",
        "JavaScript": "console.log(1+2);\n",
        "C": '#include <stdio.h>\nint main(){ printf("%d\\n", 1+2); return 0; }\n',
    }

    code = st_ace(
        value=DEFAULTS[lang],
        language=lang_map.get(lang, "text"),
        theme="tomorrow_night_eighties",
        min_lines=16,
        max_lines=32,
        annotations=st.session_state["ace_annotations"], 
        auto_update=True,  
        key=f"ace_{lang}",
    )

    autorun = st.checkbox("Auto-run", value=True)
    run_btn = st.button("Compile / Run")
    
if st.session_state["ace_annotations"]:
    last_err = st.session_state["ace_annotations"][-1]["text"]
    st.error(f"Last error: {last_err}")
do = autorun or run_btn
b = BACKENDS[lang]
tabs = st.tabs(["Tokens", "AST", "IR/Bytecode", "CFG", "Run", "Debug"])

# ---------- TOKENS ----------
with tabs[TAB_TOKENS]:
    st.subheader("Tokens")
    st.session_state["ace_annotations"] = []  # clear previous errors
    try:
        toks, t_tok = timeit(lambda: b.tokens(code))
        perf["tokens_ms"] = t_tok
        st.dataframe(toks, hide_index=True, use_container_width=True)
        st.success("Tokenization OK.")
    except Exception as e:
        st.error(f"Tokenization error: {e}")
        st.code(traceback.format_exc())
        ln, col = extract_line_col(e)
        st.session_state["ace_annotations"] = [{
            "row": (ln - 1) if ln else 0,
            "column": max(0, (col or 1) - 1),
            "text": str(e),
            "type": "error",
        }]
    perf_badge(("Tokens", perf.get("tokens_ms", 0.0)))

# ---------- AST ----------
with tabs[TAB_AST]:
    st.subheader("Parser / AST")
    try:
        if lang == "MiniLang":
            from compliter.parser import Parser, ParseError
            from compliter.inspectors import ast_ascii_tree, ast_to_dict, ast_graphviz
            prog, t_parse = timeit(lambda: Parser(code).parse())
            perf["parse_ms"] = t_parse
            st.success("Parsed successfully.")

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**AST — ASCII**")
                st.code(ast_ascii_tree(prog), language="text")
            with c2:
                st.markdown("**AST — JSON**")
                st.json(ast_to_dict(prog))

            st.markdown("**AST — Graphviz**")
            st.graphviz_chart(ast_graphviz(prog).source)

        elif lang == "Python":
            import ast
            from polyworkbench.viz import py_ast_graphviz
            tree, t_parse = timeit(lambda: ast.parse(code, mode="exec"))
            perf["parse_ms"] = t_parse
            st.markdown("**AST — Graphviz**")
            st.graphviz_chart(py_ast_graphviz(tree).source)
            with st.expander("AST (text)"):
                st.code(ast.dump(tree, indent=2), language="text")

        elif lang == "JavaScript":
            import esprima
            from polyworkbench.viz import js_ast_graphviz
            ast_obj, t_parse = timeit(lambda: esprima.parseScript(code, loc=True))
            perf["parse_ms"] = t_parse
            import json as _json
            ast_dict = _json.loads(_json.dumps(ast_obj, default=lambda o: o.__dict__))
            st.markdown("**AST — Graphviz**")
            st.graphviz_chart(js_ast_graphviz(ast_dict).source)
            with st.expander("AST (JSON)"):
                st.json(ast_dict)

        elif lang == "C":
            from pycparser import c_parser
            from polyworkbench.viz import c_ast_graphviz
            tree, t_parse = timeit(lambda: c_parser.CParser().parse(code))
            perf["parse_ms"] = t_parse
            st.markdown("**AST — Graphviz**")
            st.graphviz_chart(c_ast_graphviz(tree).source)
            with st.expander("AST (repr)"):
                st.code(str(tree), language="text")

    except Exception as e:
        st.error(f"AST error: {e}")
        st.code(traceback.format_exc())
        ln, col = extract_line_col(e)
        st.session_state["ace_annotations"] = [{
            "row": (ln - 1) if ln else 0,
            "column": max(0, (col or 1) - 1),
            "text": str(e),
            "type": "error",
        }]
    perf_badge(("Parse", perf.get("parse_ms", 0.0)))

# ---------- IR / Bytecode ----------
with tabs[TAB_IR]:
    st.subheader("IR / Bytecode")
    try:
        ir, t_ir = timeit(lambda: b.ir(code))
        perf["ir_ms"] = t_ir
        if not ir:
            st.info("No IR for this language.")
        else:
            st.code(ir, language="llvm" if lang == "C" else "text")
        st.success("IR stage OK.")
    except Exception as e:
        st.error(f"IR error: {e}")
        st.code(traceback.format_exc())
        ln, col = extract_line_col(e)
        if ln:
            st.session_state["ace_annotations"] = [{
                "row": ln - 1, "column": max(0, (col or 1) - 1),
                "text": str(e), "type": "error"
            }]
    perf_badge(("IR", perf.get("ir_ms", 0.0)))

# ---------- CFG ----------
with tabs[TAB_CFG]:
    st.subheader("Control-Flow Graph")
    try:
        from polyworkbench.viz_cfg import cfg_graphviz
        from polyworkbench.cfg_generic import cfg_from_minilang, cfg_from_python, cfg_from_js, cfg_from_c

        if lang == "MiniLang":
            from compliter.parser import Parser
            from compliter.sema import Sema
            from compliter.codegen_tac import TACBuilder
            prog, t_parse = timeit(lambda: Parser(code).parse())
            _, t_sema = timeit(lambda: Sema(prog).analyze())
            tb = TACBuilder()
            funcs, t_ir = timeit(lambda: tb.lower_prog(prog))
            perf.update(parse_ms=t_parse, sema_ms=t_sema, ir_ms=t_ir)
            for fname, ir in funcs:
                blocks, t_cfg = timeit(lambda: cfg_from_minilang(ir))
                perf["cfg_ms"] = t_cfg
                st.markdown(f"**Function** `{fname}`")
                st.graphviz_chart(cfg_graphviz(blocks).source)
            st.success("CFG generated.")
        elif lang == "Python":
            blocks, t_cfg = timeit(lambda: cfg_from_python(code))
            perf["cfg_ms"] = t_cfg
            st.graphviz_chart(cfg_graphviz(blocks).source)
            st.success("CFG from Python bytecode.")
        elif lang == "JavaScript":
            blocks, t_cfg = timeit(lambda: cfg_from_js(code))
            perf["cfg_ms"] = t_cfg
            st.graphviz_chart(cfg_graphviz(blocks).source)
            st.success("CFG from JS AST.")
        elif lang == "C":
            blocks, t_cfg = timeit(lambda: cfg_from_c(code))
            perf["cfg_ms"] = t_cfg
            st.graphviz_chart(cfg_graphviz(blocks).source)
            st.success("CFG from C AST.")
    except Exception as e:
        st.error(f"CFG error: {e}")
        st.code(traceback.format_exc())

    perf_badge(
        ("Parse", perf.get("parse_ms", 0.0)),
        ("Sema",  perf.get("sema_ms", 0.0)),
        ("IR",    perf.get("ir_ms", 0.0)),
        ("CFG",   perf.get("cfg_ms", 0.0)),
    )

# ---------- RUN ----------
with tabs[TAB_RUN]:
    st.subheader("Run")
    if do:
        try:
            r, t_run = timeit(lambda: b.run(code))
            perf["run_ms"] = t_run
            if not r.ok and r.stage_error:
                st.error(f"Run failed: {r.stage_error}")
                if r.stderr:
                    st.code(r.stderr, language="text")
                ln, col = extract_line_col(r.stderr or r.stage_error)
                if ln:
                    st.session_state["ace_annotations"] = [{
                        "row": ln - 1, "column": max(0, (col or 1) - 1),
                        "text": str(r.stage_error), "type": "error"
                    }]
            if r.stdout.strip():
                st.code(r.stdout, language="text")
            else:
                st.info("(no output)")
        except Exception as e:
            st.error(f"Run error: {e}")
            st.code(traceback.format_exc())
            ln, col = extract_line_col(e)
            if ln:
                st.session_state["ace_annotations"] = [{
                    "row": ln - 1, "column": max(0, (col or 1) - 1),
                    "text": str(e), "type": "error"
                }]
    perf_badge(("Run", perf.get("run_ms", 0.0)))

# ---------- DEBUG ----------
with tabs[TAB_DEBUG]:
    st.subheader("Debugger")
    if lang == "MiniLang":
        try:
            from compliter.parser import Parser
            from compliter.sema import Sema
            from compliter.interpreter import Interpreter
            prog = Parser(code).parse()
            Sema(prog).analyze()
            if "ml_dbg_gen" not in st.session_state:
                st.session_state.ml_dbg_gen = Interpreter(prog).run_debug()
                st.session_state.ml_events = []
            cols = st.columns(3)
            if cols[0].button("Step (MiniLang)"):
                try:
                    ev = next(st.session_state.ml_dbg_gen)
                    st.session_state.ml_events.append(ev)
                except StopIteration:
                    st.success("Program finished.")
            if cols[1].button("Reset"):
                st.session_state.ml_dbg_gen = Interpreter(prog).run_debug()
                st.session_state.ml_events = []
            st.markdown("**Events**")
            st.write(st.session_state.ml_events)
        except Exception as e:
            st.error(f"MiniLang debug error: {e}")
            st.code(traceback.format_exc())
    elif lang == "Python":
        try:
            from polyworkbench.py_debugger import LineStepper
            cols = st.columns(2)
            if cols[0].button("Run & Step Lines"):
                stepper = LineStepper()
                st.session_state.py_events = stepper.run_script(code)
            if cols[1].button("Clear"):
                st.session_state.py_events = []
            st.markdown("**Events (line-by-line)**")
            st.write(st.session_state.get("py_events", []))
        except Exception as e:
            st.error(f"Python debug error: {e}")
            st.code(traceback.format_exc())
    elif lang == "JavaScript":
        try:
            import esprima, json as _json
            ast_obj = esprima.parseScript(code, loc=True)
            ast_dict = _json.loads(_json.dumps(ast_obj, default=lambda o: o.__dict__))
            body = ast_dict.get("body", [])
            steps = []
            for s in body:
                loc = s.get("loc", {}).get("start", {})
                steps.append({"event": "stmt", "line": loc.get("line", 1), "kind": s.get("type")})
            cols = st.columns(2)
            if cols[0].button("Generate Steps"):
                st.session_state.js_steps = steps
            if cols[1].button("Clear"):
                st.session_state.js_steps = []
            st.markdown("**Structural Steps**")
            st.write(st.session_state.get("js_steps", []))
            st.info("JS debugger is structural (AST order). We can upgrade to runtime stepping by instrumenting code.")
        except Exception as e:
            st.error(f"JS debug error: {e}")
            st.code(traceback.format_exc())
    elif lang == "C":
        try:
            from polyworkbench.cfg_generic import cfg_from_c
            from polyworkbench.viz_cfg import cfg_graphviz
            blocks = cfg_from_c(code)
            order = list(blocks.keys())
            cols = st.columns(3)
            if "c_step_i" not in st.session_state:
                st.session_state.c_step_i = 0
            if cols[0].button("Next Block"):
                st.session_state.c_step_i = min(len(order) - 1, st.session_state.c_step_i + 1)
            if cols[1].button("Reset"):
                st.session_state.c_step_i = 0
            idx = st.session_state.c_step_i
            st.markdown(f"**Current Block:** `{order[idx]}`")
            st.code("\n".join(blocks[order[idx]].lines) or "(empty)")
            st.graphviz_chart(cfg_graphviz(blocks).source)
            st.info("C debugger is structural (CFG blocks). We can add real stepping via lldb/gdb if you want.")
        except Exception as e:
            st.error(f"C debug error: {e}")
            st.code(traceback.format_exc())
