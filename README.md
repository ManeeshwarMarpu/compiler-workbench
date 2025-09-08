# 🧪 Polyglot Compiler Workbench

An interactive **step-by-step compiler workbench** built with [Streamlit](https://streamlit.io).  
It supports **MiniLang (custom language)**, **Python**, **JavaScript**, and **C**, with visualization of each compilation stage:

- **Lexing / Tokens**
- **Parsing / AST (ASCII, JSON, Graphviz)**
- **Semantic Analysis (MiniLang)**
- **Intermediate Representation (IR / TAC / Bytecode)**
- **Control-Flow Graph (CFG)**
- **Execution**
- **Debugger UX** (stepping through MiniLang, Python, JavaScript, and C)

---

## ✨ Features

- Inline **error annotations** in the code editor (using `streamlit-ace`).
- Stage-by-stage **timings** (performance panel).
- **CFG visualization** for all supported languages.
- **Debugging modes**:
  - MiniLang: interpreter step mode with events.
  - Python: real line-by-line stepping (via `bdb`).
  - JavaScript: structural AST stepping.
  - C: structural CFG stepping.
- Works in your browser — no need for local GUI.

---

## 📂 Project Structure

compiler-workbench/
├── compliter/ # MiniLang compiler (parser, lexer, IR, interpreter, etc.)
├── polyworkbench/ # Polyglot backends (Python, JS, C integration)
├── examples/ # Example MiniLang programs
├── streamlit_app.py # Main Streamlit UI
├── pyproject.toml # Project metadata & dependencies
└── README.md

2. Install dependencies

It’s best to use Python 3.10+ and a virtual environment.

python -m venv .venv
.venv\Scripts\activate     # on Windows
source .venv/bin/activate  # on Linux/Mac

pip install -r requirements.txt


If you don’t have requirements.txt yet, install manually:
pip install streamlit streamlit-ace esprima pycparser graphviz


3. Run the workbench
streamlit run streamlit_app.py
