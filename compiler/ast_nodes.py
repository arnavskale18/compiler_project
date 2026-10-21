"""Explicit Abstract Syntax Tree (AST) definitions for CodeX.

Provides clean node hierarchies with source position metadata and
pretty-printing utilities for tree inspection.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Tuple, Dict


@dataclass
class ASTNode:
    line: int = 0
    column: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Converts AST node to a dictionary for JSON/tree inspection."""
        raise NotImplementedError


# ==============================================================================
# Expressions
# ==============================================================================

@dataclass
class Expression(ASTNode):
    inferred_type: Optional[str] = None  # populated during semantic analysis


@dataclass
class Literal(Expression):
    value: Any = None
    lit_type: str = "unknown"  # "int", "float", "bool", "string"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "Literal",
            "type": self.lit_type,
            "value": self.value,
            "line": self.line,
            "column": self.column,
        }

    def __repr__(self) -> str:
        return f"Literal({self.value!r}:{self.lit_type})"


@dataclass
class Identifier(Expression):
    name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "Identifier",
            "name": self.name,
            "line": self.line,
            "column": self.column,
        }

    def __repr__(self) -> str:
        return f"Id({self.name})"


@dataclass
class UnaryOp(Expression):
    op: str = ""
    operand: Expression = field(default_factory=lambda: Literal())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "UnaryOp",
            "op": self.op,
            "operand": self.operand.to_dict(),
            "line": self.line,
            "column": self.column,
        }

    def __repr__(self) -> str:
        return f"UnaryOp({self.op} {self.operand!r})"


@dataclass
class BinaryOp(Expression):
    left: Expression = field(default_factory=lambda: Literal())
    op: str = ""
    right: Expression = field(default_factory=lambda: Literal())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "BinaryOp",
            "op": self.op,
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
            "line": self.line,
            "column": self.column,
        }

    def __repr__(self) -> str:
        return f"BinaryOp({self.left!r} {self.op} {self.right!r})"


# ==============================================================================
# Statements
# ==============================================================================

@dataclass
class Statement(ASTNode):
    pass


@dataclass
class AssignStmt(Statement):
    target: Identifier = field(default_factory=Identifier)
    value: Expression = field(default_factory=lambda: Literal())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "AssignStmt",
            "target": self.target.name,
            "value": self.value.to_dict(),
            "line": self.line,
            "column": self.column,
        }

    def __repr__(self) -> str:
        return f"Assign({self.target.name} = {self.value!r})"


@dataclass
class PrintStmt(Statement):
    expressions: List[Expression] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "PrintStmt",
            "expressions": [expr.to_dict() for expr in self.expressions],
            "line": self.line,
            "column": self.column,
        }

    def __repr__(self) -> str:
        return f"Print({', '.join(repr(e) for e in self.expressions)})"


@dataclass
class PassStmt(Statement):
    def to_dict(self) -> Dict[str, Any]:
        return {"node": "PassStmt", "line": self.line, "column": self.column}

    def __repr__(self) -> str:
        return "Pass"


@dataclass
class ElifBranch(ASTNode):
    condition: Expression = field(default_factory=lambda: Literal())
    body: List[Statement] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "ElifBranch",
            "condition": self.condition.to_dict(),
            "body": [stmt.to_dict() for stmt in self.body],
            "line": self.line,
            "column": self.column,
        }


@dataclass
class IfStmt(Statement):
    condition: Expression = field(default_factory=lambda: Literal())
    then_body: List[Statement] = field(default_factory=list)
    elif_branches: List[ElifBranch] = field(default_factory=list)
    else_body: Optional[List[Statement]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "IfStmt",
            "condition": self.condition.to_dict(),
            "then_body": [stmt.to_dict() for stmt in self.then_body],
            "elif_branches": [b.to_dict() for b in self.elif_branches],
            "else_body": [stmt.to_dict() for stmt in self.else_body] if self.else_body else None,
            "line": self.line,
            "column": self.column,
        }

    def __repr__(self) -> str:
        return f"If({self.condition!r}, then={len(self.then_body)} stmts, elifs={len(self.elif_branches)}, has_else={self.else_body is not None})"


@dataclass
class WhileStmt(Statement):
    condition: Expression = field(default_factory=lambda: Literal())
    body: List[Statement] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "WhileStmt",
            "condition": self.condition.to_dict(),
            "body": [stmt.to_dict() for stmt in self.body],
            "line": self.line,
            "column": self.column,
        }

    def __repr__(self) -> str:
        return f"While({self.condition!r}, body={len(self.body)} stmts)"


@dataclass
class Program(ASTNode):
    statements: List[Statement] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "Program",
            "statements": [stmt.to_dict() for stmt in self.statements],
        }


def format_ast_tree(node: ASTNode, prefix: str = "", is_last: bool = True) -> str:
    """Formats an AST node into an ASCII tree diagram."""
    connector = "`-- " if is_last else "|-- "
    new_prefix = prefix + ("    " if is_last else "|   ")
    lines = []

    if isinstance(node, Program):
        lines.append("Program")
        count = len(node.statements)
        for i, stmt in enumerate(node.statements):
            lines.append(format_ast_tree(stmt, prefix, i == count - 1))
        return "\n".join(lines)

    if isinstance(node, AssignStmt):
        lines.append(f"{prefix}{connector}AssignStmt (=) [line {node.line}]")
        lines.append(f"{new_prefix}|-- Target: {node.target.name}")
        lines.append(f"{new_prefix}`-- Value:")
        lines.append(format_ast_tree(node.value, new_prefix + "    ", True))
        return "\n".join(lines)

    if isinstance(node, PrintStmt):
        lines.append(f"{prefix}{connector}PrintStmt [line {node.line}]")
        count = len(node.expressions)
        for i, expr in enumerate(node.expressions):
            lines.append(format_ast_tree(expr, new_prefix, i == count - 1))
        return "\n".join(lines)

    if isinstance(node, PassStmt):
        lines.append(f"{prefix}{connector}PassStmt [line {node.line}]")
        return "\n".join(lines)

    if isinstance(node, IfStmt):
        lines.append(f"{prefix}{connector}IfStmt [line {node.line}]")
        lines.append(f"{new_prefix}|-- Condition:")
        lines.append(format_ast_tree(node.condition, new_prefix + "|   ", True))
        lines.append(f"{new_prefix}|-- Then Block ({len(node.then_body)} stmts):")
        for i, stmt in enumerate(node.then_body):
            is_l = (i == len(node.then_body) - 1) and not node.elif_branches and not node.else_body
            lines.append(format_ast_tree(stmt, new_prefix + "|   ", is_l))
        for elif_idx, elif_b in enumerate(node.elif_branches):
            lines.append(f"{new_prefix}|-- Elif Branch [line {elif_b.line}]:")
            lines.append(f"{new_prefix}|   |-- Condition:")
            lines.append(format_ast_tree(elif_b.condition, new_prefix + "|   |   ", True))
            lines.append(f"{new_prefix}|   `-- Body:")
            for j, s in enumerate(elif_b.body):
                lines.append(format_ast_tree(s, new_prefix + "|       ", j == len(elif_b.body) - 1))
        if node.else_body:
            lines.append(f"{new_prefix}`-- Else Block ({len(node.else_body)} stmts):")
            for i, stmt in enumerate(node.else_body):
                lines.append(format_ast_tree(stmt, new_prefix + "    ", i == len(node.else_body) - 1))
        return "\n".join(lines)

    if isinstance(node, WhileStmt):
        lines.append(f"{prefix}{connector}WhileStmt [line {node.line}]")
        lines.append(f"{new_prefix}|-- Condition:")
        lines.append(format_ast_tree(node.condition, new_prefix + "|   ", True))
        lines.append(f"{new_prefix}`-- Body ({len(node.body)} stmts):")
        for i, stmt in enumerate(node.body):
            lines.append(format_ast_tree(stmt, new_prefix + "    ", i == len(node.body) - 1))
        return "\n".join(lines)

    if isinstance(node, BinaryOp):
        type_annot = f" : {node.inferred_type}" if node.inferred_type else ""
        lines.append(f"{prefix}{connector}BinaryOp ('{node.op}'){type_annot} [line {node.line}]")
        lines.append(format_ast_tree(node.left, new_prefix, False))
        lines.append(format_ast_tree(node.right, new_prefix, True))
        return "\n".join(lines)

    if isinstance(node, UnaryOp):
        type_annot = f" : {node.inferred_type}" if node.inferred_type else ""
        lines.append(f"{prefix}{connector}UnaryOp ('{node.op}'){type_annot} [line {node.line}]")
        lines.append(format_ast_tree(node.operand, new_prefix, True))
        return "\n".join(lines)

    if isinstance(node, Identifier):
        type_annot = f" : {node.inferred_type}" if node.inferred_type else ""
        lines.append(f"{prefix}{connector}Id('{node.name}'){type_annot} [line {node.line}]")
        return "\n".join(lines)

    if isinstance(node, Literal):
        type_annot = f" : {node.inferred_type}" if node.inferred_type else ""
        lines.append(f"{prefix}{connector}Literal({node.value!r}, type={node.lit_type}){type_annot} [line {node.line}]")
        return "\n".join(lines)

    return f"{prefix}{connector}{type(node).__name__}"
