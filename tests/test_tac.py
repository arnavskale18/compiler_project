import pytest
from compiler.parser import parse_source
from compiler.semantic import SemanticAnalyzer
from compiler.tac import TacGenerator, TacOp


def test_tac_arithmetic_linearization():
    src = "x = (a + b) * (c - d)\n"
    ast = parse_source(src)
    # Define symbols so analyzer passes
    analyzer = SemanticAnalyzer()
    analyzer.symbol_table.define("a", "int", 1, 1)
    analyzer.symbol_table.define("b", "int", 1, 1)
    analyzer.symbol_table.define("c", "int", 1, 1)
    analyzer.symbol_table.define("d", "int", 1, 1)
    for s in ast.statements:
        analyzer.visit_statement(s)

    tac_gen = TacGenerator()
    instructions = tac_gen.generate(ast)

    ops = [i.op for i in instructions]
    assert TacOp.BINARY in ops
    assert TacOp.ASSIGN in ops
    # The last instruction should assign to 'x'
    assert instructions[-1].dest == "x"


def test_tac_if_else_control_flow():
    src = (
        "if x > 0:\n"
        "    y = 1\n"
        "else:\n"
        "    y = 2\n"
    )
    ast = parse_source(src)
    analyzer = SemanticAnalyzer()
    analyzer.symbol_table.define("x", "int", 1, 1)
    for s in ast.statements:
        analyzer.visit_statement(s)

    tac_gen = TacGenerator()
    instructions = tac_gen.generate(ast)

    has_jump_if_false = any(i.op == TacOp.JUMP_IF_FALSE for i in instructions)
    has_jump = any(i.op == TacOp.JUMP for i in instructions)
    has_label = any(i.op == TacOp.LABEL for i in instructions)

    assert has_jump_if_false
    assert has_jump
    assert has_label


def test_tac_while_loop_control_flow():
    src = (
        "while i < 10:\n"
        "    i = i + 1\n"
    )
    ast = parse_source(src)
    analyzer = SemanticAnalyzer()
    analyzer.symbol_table.define("i", "int", 1, 1)
    for s in ast.statements:
        analyzer.visit_statement(s)

    tac_gen = TacGenerator()
    instructions = tac_gen.generate(ast)

    # First instruction should be a LABEL (loop header)
    assert instructions[0].op == TacOp.LABEL
    # Should have a jump_if_false
    assert any(i.op == TacOp.JUMP_IF_FALSE for i in instructions)
    # Should end loop body with an unconditional jump back to start
    jump_backs = [i for i in instructions if i.op == TacOp.JUMP and i.arg1 == instructions[0].dest]
    assert len(jump_backs) >= 1
