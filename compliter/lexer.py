import re
from dataclasses import dataclass

@dataclass
class Token:
    kind: str
    lexeme: str
    line: int
    col: int
KEYWORDS = {
    'fn','let','if','else','while','return','true','false','int','bool','string'
}


TOKEN_SPEC = [
    ("NUMBER",   r"\d+"),
    ("STRING",   r'"([^"\\]|\\.)*"'),
    ("ID",       r"[A-Za-z_][A-Za-z0-9_]*"),
    ("OP",       r"==|!=|<=|>=|&&|\|\||[+\-*/<>!]") ,
    ("LPAREN",   r"\("),
    ("RPAREN",   r"\)"),
    ("LBRACE",   r"\{"),
    ("RBRACE",   r"\}"),
    ("COMMA",    r","),
    ("COLON",    r":"),
    ("SEMICOL",  r";"),
    ("ARROW",    r"->"),
    ("EQ",       r"=")
]

MASTER = re.compile("|".join(f"(?P<{k}>{p})" for k,p in TOKEN_SPEC))
WS = re.compile(r"[\t \r\f]+")
NEWLINE = re.compile(r"\n")

class Lexer:
    def __init__(self, text:str):
        self.text = text
        self.i = 0
        self.line = 1
        self.col = 1

    def _advance(self, n):
        for _ in range(n):
            if self.text[self.i] == '\n':
                self.line += 1
                self.col = 1
            else:
                self.col += 1
            self.i += 1

    def tokens(self):
        text = self.text
        N = len(text)
        while self.i < N:
            # skip comments
            if text[self.i:self.i+2] == "//":
                while self.i < N and text[self.i] != '\n':
                    self._advance(1)
                continue
            m = WS.match(text, self.i)
            if m:
                self._advance(len(m.group(0)))
                continue
            if self.i < N and text[self.i] == '\n':
                self._advance(1)
                continue
            # ARROW
            if text[self.i:self.i+2] == '->':
                tok = Token('ARROW','->', self.line, self.col)
                self._advance(2)
                yield tok
                continue
            m = MASTER.match(text, self.i)
            if not m:
                ch = text[self.i]
                raise SyntaxError(f"Unknown character '{ch}' at {self.line}:{self.col}")
            kind = m.lastgroup
            lex = m.group(0)
            if kind == 'ID' and lex in KEYWORDS:
                tok = Token(lex.upper(), lex, self.line, self.col)
            elif kind == 'STRING':
                tok = Token('STRING', bytes(lex[1:-1], 'utf-8').decode('unicode_escape'), self.line, self.col)
            else:
                tok = Token(kind, lex, self.line, self.col)
            self._advance(len(lex))
            yield tok
        yield Token('EOF','', self.line, self.col)
