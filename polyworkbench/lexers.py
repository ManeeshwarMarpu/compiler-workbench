from pygments import lex
from pygments.lexers import PythonLexer, JavascriptLexer, CLexer
from pygments.token import Token

def pygments_tokens(code:str, lang:str):
    if lang == "python": lx = PythonLexer()
    elif lang == "javascript": lx = JavascriptLexer()
    elif lang == "c": lx = CLexer()
    else: raise ValueError("Unsupported for pygments: " + lang)
    rows = []
    for ttype, value in lex(code, lx):
        kind = str(ttype)
        rows.append({"kind": kind, "lexeme": value})
    return rows
