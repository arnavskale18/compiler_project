"""Three-Address Code (TAC) Intermediate Representation and Code Generator for CodeX.

Produces linear, deterministic three-address instructions using explicit
temporaries, labels, conditional/unconditional jumps, and print operations.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Any
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


class TacOp(str, Enum):
    ASSIGN = "ASSIGN"
    BINARY = "BINARY"
    UNARY = "UNARY"
    LABEL = "LABEL"
    JUMP = "JUMP"
    JUMP_IF_FALSE = "JUMP_IF_FALSE"
    JUMP_IF_TRUE = "JUMP_IF_TRUE"
    PRINT = "PRINT"


@dataclass
class TacInstruction:
    op: TacOp
    dest: Optional[str] = None
    arg1: Optional[str] = None
    arg2: Optional[str] = None
    operator: Optional[str] = None
    args: List[str] = field(default_factory=list)
    comment: str = ""
    line: int = 0

    def to_code_str(self) -> str:
        """Returns standard, human-readable Three-Address Code string."""
        if self.op == TacOp.LABEL:
            return f"{self.dest}:"
        elif self.op == TacOp.JUMP:
            return f"    goto {self.arg1}"
        elif self.op == TacOp.JUMP_IF_FALSE:
            return f"    if_false {self.arg1} goto {self.arg2}"
        elif self.op == TacOp.JUMP_IF_TRUE:
            return f"    if_true {self.arg1} goto {self.arg2}"
        elif self.op == TacOp.ASSIGN:
            return f"    {self.dest} = {self.arg1}"
        elif self.op == TacOp.BINARY:
            return f"    {self.dest} = {self.arg1} {self.operator} {self.arg2}"
        elif self.op == TacOp.UNARY:
            return f"    {self.dest} = {self.operator} {self.arg1}"
        elif self.op == TacOp.PRINT:
            items = ", ".join(self.args)
            return f"    print {items}"
        return f"    {self.op.value} {self.dest}"

    def __repr__(self) -> str:
        return self.to_code_str()


class TacGenerator:
    def __init__(self):
        self.instructions: List[TacInstruction] = []
        self._temp_counter = 0
        self._label_counter = 0

    def new_temp(self) -> str:
        t = f"t{self._temp_counter}"
        self._temp_counter += 1
        return t

    def new_label(self, prefix: str = "L") -> str:
        l = f"{prefix}{self._label_counter}"
        self._label_counter += 1
        return l

    def emit(self, inst: TacInstruction) -> TacInstruction:
        self.instructions.append(inst)
        return inst

    def generate(self, program: Program) -> List[TacInstruction]:
        self.instructions = []
        self._temp_counter = 0
        self._label_counter = 0
        for stmt in program.statements:
            self.generate_statement(stmt)
        return self.instructions

    def generate_statement(self, stmt: Statement) -> None:
        if isinstance(stmt, AssignStmt):
            rhs_var = self.generate_expr(stmt.value)
            self.emit(
                TacInstruction(
                    op=TacOp.ASSIGN,
                    dest=stmt.target.name,
                    arg1=rhs_var,
                    line=stmt.line,
                )
            )
        elif isinstance(stmt, PrintStmt):
            arg_vars = [self.generate_expr(e) for e in stmt.expressions]
            self.emit(
                TacInstruction(
                    op=TacOp.PRINT,
                    args=arg_vars,
                    line=stmt.line,
                )
            )
        elif isinstance(stmt, PassStmt):
            pass
        elif isinstance(stmt, IfStmt):
            self.generate_if_stmt(stmt)
        elif isinstance(stmt, WhileStmt):
            self.generate_while_stmt(stmt)

    def generate_if_stmt(self, stmt: IfStmt) -> None:
        end_label = self.new_label("L_endif_")
        
        # Then condition
        cond_var = self.generate_expr(stmt.condition)
        next_label = self.new_label("L_else_") if (stmt.elif_branches or stmt.else_body) else end_label
        
        self.emit(
            TacInstruction(
                op=TacOp.JUMP_IF_FALSE,
                arg1=cond_var,
                arg2=next_label,
                line=stmt.condition.line,
            )
        )
        for s in stmt.then_body:
            self.generate_statement(s)
            
        if stmt.elif_branches or stmt.else_body:
            self.emit(TacInstruction(op=TacOp.JUMP, arg1=end_label, line=stmt.line))
            
        curr_label = next_label
        # Process elif branches
        for i, elif_b in enumerate(stmt.elif_branches):
            self.emit(TacInstruction(op=TacOp.LABEL, dest=curr_label, line=elif_b.line))
            elif_cond_var = self.generate_expr(elif_b.condition)
            is_last = (i == len(stmt.elif_branches) - 1) and not stmt.else_body
            next_b_label = end_label if is_last else self.new_label(f"L_elif_{i+1}_")
            
            self.emit(
                TacInstruction(
                    op=TacOp.JUMP_IF_FALSE,
                    arg1=elif_cond_var,
                    arg2=next_b_label,
                    line=elif_b.condition.line,
                )
            )
            for s in elif_b.body:
                self.generate_statement(s)
            self.emit(TacInstruction(op=TacOp.JUMP, arg1=end_label, line=elif_b.line))
            curr_label = next_b_label

        # Process else body if present
        if stmt.else_body:
            self.emit(TacInstruction(op=TacOp.LABEL, dest=curr_label, line=stmt.line))
            for s in stmt.else_body:
                self.generate_statement(s)

        self.emit(TacInstruction(op=TacOp.LABEL, dest=end_label, line=stmt.line))

    def generate_while_stmt(self, stmt: WhileStmt) -> None:
        start_label = self.new_label("L_while_start_")
        end_label = self.new_label("L_while_end_")

        self.emit(TacInstruction(op=TacOp.LABEL, dest=start_label, line=stmt.line))
        cond_var = self.generate_expr(stmt.condition)
        self.emit(
            TacInstruction(
                op=TacOp.JUMP_IF_FALSE,
                arg1=cond_var,
                arg2=end_label,
                line=stmt.condition.line,
            )
        )
        for s in stmt.body:
            self.generate_statement(s)
        self.emit(TacInstruction(op=TacOp.JUMP, arg1=start_label, line=stmt.line))
        self.emit(TacInstruction(op=TacOp.LABEL, dest=end_label, line=stmt.line))

    def generate_expr(self, expr: Expression) -> str:
        if isinstance(expr, Literal):
            if expr.lit_type == "string":
                return repr(expr.value)  # formatted with quotes e.g. "hello"
            elif expr.lit_type == "bool":
                return "True" if expr.value else "False"
            return str(expr.value)

        if isinstance(expr, Identifier):
            return expr.name

        if isinstance(expr, UnaryOp):
            operand_var = self.generate_expr(expr.operand)
            temp = self.new_temp()
            self.emit(
                TacInstruction(
                    op=TacOp.UNARY,
                    dest=temp,
                    operator=expr.op,
                    arg1=operand_var,
                    line=expr.line,
                )
            )
            return temp

        if isinstance(expr, BinaryOp):
            left_var = self.generate_expr(expr.left)
            right_var = self.generate_expr(expr.right)
            temp = self.new_temp()
            self.emit(
                TacInstruction(
                    op=TacOp.BINARY,
                    dest=temp,
                    operator=expr.op,
                    arg1=left_var,
                    arg2=right_var,
                    line=expr.line,
                )
            )
            return temp

        raise ValueError(f"Unknown expression type in TAC generation: {type(expr).__name__}")


def format_tac_instructions(instructions: List[TacInstruction]) -> str:
    """Returns formatted string of TAC instructions."""
    lines = []
    for i, inst in enumerate(instructions):
        line_num = f"{i:03d}: "
        lines.append(f"{line_num}{inst.to_code_str()}")
    return "\n".join(lines)
