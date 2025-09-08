from dataclasses import dataclass
from typing import List, Optional, Any

@dataclass
class Node:
    line: int
    col: int

@dataclass
class Program(Node):
    decls: List[Node]

@dataclass
class FuncDecl(Node):
    name: str
    params: List[tuple]  # (name, type)
    ret_type: str
    body: 'Block'

@dataclass
class Block(Node):
    statements: List[Node]

@dataclass
class VarDecl(Node):
    name: str
    type_name: str
    init: Optional['Expr']

@dataclass
class IfStmt(Node):
    cond: 'Expr'
    then_block: Block
    else_block: Optional[Block]

@dataclass
class WhileStmt(Node):
    cond: 'Expr'
    body: Block

@dataclass
class ReturnStmt(Node):
    value: Optional['Expr']

@dataclass
class Assign(Node):
    name: str
    value: 'Expr'

# Expressions
@dataclass
class Expr(Node):
    pass

@dataclass
class Literal(Expr):
    value: Any

@dataclass
class Var(Expr):
    name: str

@dataclass
class BinOp(Expr):
    op: str
    left: Expr
    right: Expr

@dataclass
class UnOp(Expr):
    op: str
    operand: Expr

@dataclass
class Call(Expr):
    name: str
    args: List[Expr]
