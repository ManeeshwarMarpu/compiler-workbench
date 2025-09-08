from typing import List
from .lexer import Lexer, Token
from .astnodes import *

class ParseError(Exception):
    pass

class Parser:
        def __init__(self, text:str):
            self.tokens = list(Lexer(text).tokens())
            self.pos = 0

        def peek(self) -> Token:
            return self.tokens[self.pos]

        def match(self, *kinds):
            if self.peek().kind in kinds:
                t = self.peek()
                self.pos += 1
                return t
            return None

        def expect(self, kind:str):
            t = self.peek()
            if t.kind != kind:
                raise ParseError(f"Expected {kind}, got {t.kind} at {t.line}:{t.col}")
            self.pos += 1
            return t

        def parse(self) -> Program:
            decls: List[Node] = []
            start = self.peek()
            while self.peek().kind != 'EOF':
                decls.append(self.fn_decl())
            return Program(line=start.line, col=start.col, decls=decls)

        # fn name '(' params? ')' '->' type block
        def fn_decl(self) -> FuncDecl:
            kw = self.expect('FN')
            name = self.expect('ID').lexeme
            self.expect('LPAREN')
            params = []
            if self.peek().kind != 'RPAREN':
                params.append(self.param())
                while self.match('COMMA'):
                    params.append(self.param())
            self.expect('RPAREN')
            self.expect('ARROW')
            ret_type = self.type_name()
            body = self.block()
            return FuncDecl(kw.line, kw.col, name=name, params=params, ret_type=ret_type, body=body)

        def param(self):
            name = self.expect('ID').lexeme
            self.expect('COLON')
            tname = self.type_name()
            return (name, tname)

        def type_name(self):
            t = self.peek()
            if t.kind in ('INT','BOOL','STRING'):
                self.pos += 1
                return t.lexeme
            if t.kind == 'ID':
                self.pos += 1
                return t.lexeme
            raise ParseError(f"Expected type at {t.line}:{t.col}")

        def block(self) -> Block:
            lb = self.expect('LBRACE')
            stmts = []
            while self.peek().kind not in ('RBRACE','EOF'):
                stmts.append(self.statement())
            self.expect('RBRACE')
            return Block(lb.line, lb.col, statements=stmts)

        def statement(self) -> Node:
            t = self.peek()
            if t.kind == 'LET':
                return self.var_decl()
            if t.kind == 'IF':
                return self.if_stmt()
            if t.kind == 'WHILE':
                return self.while_stmt()
            if t.kind == 'RETURN':
                return self.return_stmt()
            # assignment or expression statement
            if t.kind == 'ID' and self.tokens[self.pos+1].kind in ('EQ',):
                return self.assign_stmt()
            expr = self.expr()
            self.expect('SEMICOL')
            return expr

        def var_decl(self) -> VarDecl:
            kw = self.expect('LET')
            name = self.expect('ID').lexeme
            self.expect('COLON')
            tname = self.type_name()
            init = None
            if self.match('EQ'):
                init = self.expr()
            self.expect('SEMICOL')
            return VarDecl(kw.line, kw.col, name=name, type_name=tname, init=init)

        def if_stmt(self) -> IfStmt:
            kw = self.expect('IF')
            self.expect('LPAREN')
            cond = self.expr()
            self.expect('RPAREN')
            thenb = self.block()
            elseb = None
            if self.match('ELSE'):
                elseb = self.block()
            return IfStmt(kw.line, kw.col, cond=cond, then_block=thenb, else_block=elseb)

        def while_stmt(self) -> WhileStmt:
            kw = self.expect('WHILE')
            self.expect('LPAREN')
            cond = self.expr()
            self.expect('RPAREN')
            body = self.block()
            return WhileStmt(kw.line, kw.col, cond=cond, body=body)

        def return_stmt(self) -> ReturnStmt:
            kw = self.expect('RETURN')
            val = None
            if self.peek().kind != 'SEMICOL':
                val = self.expr()
            self.expect('SEMICOL')
            return ReturnStmt(kw.line, kw.col, value=val)

        def assign_stmt(self) -> Assign:
            t = self.expect('ID')
            self.expect('EQ')
            val = self.expr()
            self.expect('SEMICOL')
            return Assign(t.line, t.col, name=t.lexeme, value=val)

        # Pratt parser for expressions with precedence
        def expr(self) -> Expr:
            return self._parse_binop(0)

        PRECEDENCE = {
            '||':1,
            '&&':2,
            '==':3,'!=':3,
            '<':4,'>':4,'<=':4,'>=':4,
            '+':5,'-':5,
            '*':6,'/':6,
        }

        def _parse_primary(self) -> Expr:
            t = self.peek()
            if t.kind == 'NUMBER':
                self.pos += 1
                return Literal(t.line,t.col,int(t.lexeme))
            if t.kind == 'STRING':
                self.pos += 1
                return Literal(t.line,t.col,t.lexeme)
            if t.kind == 'TRUE':
                self.pos += 1
                return Literal(t.line,t.col,True)
            if t.kind == 'FALSE':
                self.pos += 1
                return Literal(t.line,t.col,False)
            if t.kind == 'ID':
                # call or variable
                if self.tokens[self.pos+1].kind == 'LPAREN':
                    name = t.lexeme
                    self.pos += 2  # consume ID, LPAREN
                    args: List[Expr] = []
                    if self.peek().kind != 'RPAREN':
                        args.append(self.expr())
                        while self.match('COMMA'):
                            args.append(self.expr())
                    self.expect('RPAREN')
                    return Call(t.line,t.col,name=name,args=args)
                else:
                    self.pos += 1
                    return Var(t.line,t.col,name=t.lexeme)
            if t.kind == 'LPAREN':
                self.pos += 1
                e = self.expr()
                self.expect('RPAREN')
                return e
            # unary operators
            if t.kind == 'OP' and t.lexeme in ('-','!'):
                self.pos += 1
                operand = self._parse_primary()
                return UnOp(t.line,t.col,op=t.lexeme, operand=operand)
            raise ParseError(f"Unexpected token {t.kind} at {t.line}:{t.col}")

        def _lbp(self, tok:Token):
            if tok.kind == 'OP':
                return self.PRECEDENCE.get(tok.lexeme, -1)
            if tok.lexeme in self.PRECEDENCE:
                return self.PRECEDENCE[tok.lexeme]
            return -1

        def _parse_binop(self, min_bp:int) -> Expr:
            left = self._parse_primary()
            while True:
                tok = self.peek()
                op = None
                if tok.kind == 'OP':
                    op = tok.lexeme
                else:
                    break
                lbp = self._lbp(tok)
                if lbp < min_bp:
                    break
                self.pos += 1
                right = self._parse_binop(lbp + 1)
                left = BinOp(tok.line,tok.col,op=op,left=left,right=right)
            return left
