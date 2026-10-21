"""Semantic Analyzer and Type Checker for CodeX.

Performs static type checking, undeclared identifier detection,
scope resolution, and type inference across the AST.
"""

from typing import Optional, List
from .ast_nodes import (
    Program,
    Statement,
    AssignStmt,
    PrintStmt,
    PassStmt,
    IfStmt,
    WhileStmt,
    Expression,
    BinaryOp,
    UnaryOp,
    Literal,
    Identifier,
)
from .symbol_table import SymbolTable, Symbol


class SemanticError(Exception):
    def __init__(self, message: str, line: int, column: int):
        super().__init__(f"SemanticError at line {line}, col {column}: {message}")
        self.message = message
        self.line = line
        self.column = column


class SemanticAnalyzer:
    def __init__(self):
        self.symbol_table = SymbolTable()

    def analyze(self, program: Program) -> SymbolTable:
        for stmt in program.statements:
            self.visit_statement(stmt)
        return self.symbol_table

    def visit_statement(self, stmt: Statement) -> None:
        if isinstance(stmt, AssignStmt):
            self.visit_assign_stmt(stmt)
        elif isinstance(stmt, PrintStmt):
            self.visit_print_stmt(stmt)
        elif isinstance(stmt, IfStmt):
            self.visit_if_stmt(stmt)
        elif isinstance(stmt, WhileStmt):
            self.visit_while_stmt(stmt)
        elif isinstance(stmt, PassStmt):
            pass
        else:
            raise SemanticError(f"Unknown statement type {type(stmt).__name__}", stmt.line, stmt.column)

    def visit_assign_stmt(self, stmt: AssignStmt) -> None:
        val_type = self.visit_expr(stmt.value)
        target_name = stmt.target.name
        existing = self.symbol_table.lookup(target_name)

        if existing is None:
            # Declare variable with inferred type
            self.symbol_table.define(
                name=target_name,
                type_name=val_type,
                line=stmt.line,
                column=stmt.column,
            )
            stmt.target.inferred_type = val_type
        else:
            # Reassignment: verify type compatibility
            if existing.type_name == val_type:
                stmt.target.inferred_type = val_type
            elif existing.type_name == "float" and val_type == "int":
                # Safe numeric promotion: int value can be stored in float
                stmt.target.inferred_type = "float"
            else:
                raise SemanticError(
                    f"Cannot assign expression of type '{val_type}' to variable '{target_name}' previously declared as '{existing.type_name}'",
                    stmt.line,
                    stmt.column,
                )

    def visit_print_stmt(self, stmt: PrintStmt) -> None:
        for expr in stmt.expressions:
            self.visit_expr(expr)

    def visit_if_stmt(self, stmt: IfStmt) -> None:
        cond_type = self.visit_expr(stmt.condition)
        if cond_type != "bool":
            raise SemanticError(
                f"Condition in 'if' statement must be of type 'bool', but got '{cond_type}'",
                stmt.condition.line,
                stmt.condition.column,
            )
        for s in stmt.then_body:
            self.visit_statement(s)

        for elif_branch in stmt.elif_branches:
            elif_cond_type = self.visit_expr(elif_branch.condition)
            if elif_cond_type != "bool":
                raise SemanticError(
                    f"Condition in 'elif' statement must be of type 'bool', but got '{elif_cond_type}'",
                    elif_branch.condition.line,
                    elif_branch.condition.column,
                )
            for s in elif_branch.body:
                self.visit_statement(s)

        if stmt.else_body:
            for s in stmt.else_body:
                self.visit_statement(s)

    def visit_while_stmt(self, stmt: WhileStmt) -> None:
        cond_type = self.visit_expr(stmt.condition)
        if cond_type != "bool":
            raise SemanticError(
                f"Condition in 'while' loop must be of type 'bool', but got '{cond_type}'",
                stmt.condition.line,
                stmt.condition.column,
            )
        for s in stmt.body:
            self.visit_statement(s)

    def visit_expr(self, expr: Expression) -> str:
        if isinstance(expr, Literal):
            expr.inferred_type = expr.lit_type
            return expr.lit_type

        if isinstance(expr, Identifier):
            sym = self.symbol_table.lookup(expr.name)
            if sym is None:
                raise SemanticError(f"Undeclared variable '{expr.name}'", expr.line, expr.column)
            expr.inferred_type = sym.type_name
            return sym.type_name

        if isinstance(expr, UnaryOp):
            operand_type = self.visit_expr(expr.operand)
            if expr.op in ("+", "-"):
                if operand_type not in ("int", "float"):
                    raise SemanticError(
                        f"Unary operator '{expr.op}' cannot be applied to type '{operand_type}'",
                        expr.line,
                        expr.column,
                    )
                expr.inferred_type = operand_type
                return operand_type
            elif expr.op == "not":
                if operand_type != "bool":
                    raise SemanticError(
                        f"Logical 'not' operator requires 'bool' operand, got '{operand_type}'",
                        expr.line,
                        expr.column,
                    )
                expr.inferred_type = "bool"
                return "bool"
            else:
                raise SemanticError(f"Unsupported unary operator '{expr.op}'", expr.line, expr.column)

        if isinstance(expr, BinaryOp):
            left_type = self.visit_expr(expr.left)
            right_type = self.visit_expr(expr.right)
            op = expr.op

            # Arithmetic
            if op in ("+", "-", "*"):
                if left_type == "int" and right_type == "int":
                    res_type = "int"
                elif (left_type, right_type) in [("int", "float"), ("float", "int"), ("float", "float")]:
                    res_type = "float"
                elif op == "+" and left_type == "string" and right_type == "string":
                    res_type = "string"
                else:
                    raise SemanticError(
                        f"Invalid operand types for '{op}': '{left_type}' and '{right_type}'",
                        expr.line,
                        expr.column,
                    )
                expr.inferred_type = res_type
                return res_type

            if op == "/":
                # Python float division
                if left_type in ("int", "float") and right_type in ("int", "float"):
                    res_type = "float"
                else:
                    raise SemanticError(
                        f"Division '/' requires numeric operands, got '{left_type}' and '{right_type}'",
                        expr.line,
                        expr.column,
                    )
                expr.inferred_type = res_type
                return res_type

            if op in ("//", "%"):
                # Integer division and modulo
                if left_type == "int" and right_type == "int":
                    res_type = "int"
                else:
                    raise SemanticError(
                        f"Operator '{op}' requires integer operands, got '{left_type}' and '{right_type}'",
                        expr.line,
                        expr.column,
                    )
                expr.inferred_type = res_type
                return res_type

            # Comparison
            if op in ("<", "<=", ">", ">="):
                if (left_type in ("int", "float") and right_type in ("int", "float")) or (
                    left_type == "string" and right_type == "string"
                ):
                    res_type = "bool"
                else:
                    raise SemanticError(
                        f"Operator '{op}' cannot compare '{left_type}' with '{right_type}'",
                        expr.line,
                        expr.column,
                    )
                expr.inferred_type = res_type
                return res_type

            if op in ("==", "!="):
                if (left_type in ("int", "float") and right_type in ("int", "float")) or (left_type == right_type):
                    res_type = "bool"
                else:
                    raise SemanticError(
                        f"Equality operator '{op}' cannot compare incompatible types '{left_type}' and '{right_type}'",
                        expr.line,
                        expr.column,
                    )
                expr.inferred_type = res_type
                return res_type

            # Logical
            if op in ("and", "or"):
                if left_type == "bool" and right_type == "bool":
                    res_type = "bool"
                else:
                    raise SemanticError(
                        f"Logical operator '{op}' requires 'bool' operands, got '{left_type}' and '{right_type}'",
                        expr.line,
                        expr.column,
                    )
                expr.inferred_type = res_type
                return res_type

            raise SemanticError(f"Unsupported binary operator '{op}'", expr.line, expr.column)

        raise SemanticError(f"Unknown expression type {type(expr).__name__}", expr.line, expr.column)
