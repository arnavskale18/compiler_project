import pytest
from compiler.parser import parse_source, ParserError
from compiler.ast_nodes import (
    Program,
    AssignStmt,
    PrintStmt,
    IfStmt,
    WhileStmt,
    BinaryOp,
    UnaryOp,
    Literal,
    Identifier,
)


def test_parser_arithmetic_precedence():
    # 2 + 3 * 4 should parse as 2 + (3 * 4)
    ast = parse_source("x = 2 + 3 * 4\n")
    assert len(ast.statements) == 1
    stmt = ast.statements[0]
    assert isinstance(stmt, AssignStmt)
    assert isinstance(stmt.value, BinaryOp)
    assert stmt.value.op == "+"
    assert isinstance(stmt.value.left, Literal)
    assert stmt.value.left.value == 2
    assert isinstance(stmt.value.right, BinaryOp)
    assert stmt.value.right.op == "*"
    assert stmt.value.right.left.value == 3
    assert stmt.value.right.right.value == 4


def test_parser_logical_precedence():
    # not a and b or c -> ((not a) and b) or c
    ast = parse_source("res = not a and b or c\n")
    stmt = ast.statements[0]
    assert isinstance(stmt, AssignStmt)
    assert isinstance(stmt.value, BinaryOp)
    assert stmt.value.op == "or"
    assert isinstance(stmt.value.left, BinaryOp)
    assert stmt.value.left.op == "and"
    assert isinstance(stmt.value.left.left, UnaryOp)
    assert stmt.value.left.left.op == "not"


def test_parser_parentheses_override():
    # (2 + 3) * 4
    ast = parse_source("x = (2 + 3) * 4\n")
    stmt = ast.statements[0]
    assert stmt.value.op == "*"
    assert stmt.value.left.op == "+"


def test_parser_if_elif_else():
    src = (
        "if x > 0:\n"
        "    print(1)\n"
        "elif x == 0:\n"
        "    print(0)\n"
        "else:\n"
        "    print(-1)\n"
    )
    ast = parse_source(src)
    assert len(ast.statements) == 1
    if_stmt = ast.statements[0]
    assert isinstance(if_stmt, IfStmt)
    assert len(if_stmt.then_body) == 1
    assert len(if_stmt.elif_branches) == 1
    assert if_stmt.else_body is not None
    assert len(if_stmt.else_body) == 1


def test_parser_while_loop():
    src = (
        "while i < 10:\n"
        "    i = i + 1\n"
    )
    ast = parse_source(src)
    assert len(ast.statements) == 1
    w_stmt = ast.statements[0]
    assert isinstance(w_stmt, WhileStmt)
    assert len(w_stmt.body) == 1


def test_parser_syntax_error_missing_colon():
    src = "if x > 0\n    print(1)\n"
    with pytest.raises(ParserError) as exc_info:
        parse_source(src)
    assert "Expected ':'" in exc_info.value.message


def test_parser_syntax_error_unclosed_paren():
    src = "print(1 + 2\n"
    with pytest.raises(ParserError) as exc_info:
        parse_source(src)
    assert "Expected ')'" in exc_info.value.message
