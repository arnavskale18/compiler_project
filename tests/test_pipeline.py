import os
import pytest
from compiler.pipeline import compile_source


def test_pipeline_success():
    src = "x = 10\ny = x + 5\nprint(y)\n"
    res = compile_source(src)
    assert res.success is True
    assert res.phase_reached == "COMPLETED"
    assert len(res.tokens) > 0
    assert res.ast is not None
    assert len(res.symbols) == 2
    assert len(res.tac) > 0
    assert len(res.optimized_tac) > 0
    assert "#include <iostream>" in res.cpp_code


def test_pipeline_stop_at_lexer():
    src = "x = 10 @ 2\n"
    res = compile_source(src)
    assert res.success is False
    assert res.phase_reached == "LEXICAL"
    assert res.ast is None
    assert len(res.tac) == 0
    assert len(res.diagnostics) == 1
    assert res.diagnostics[0].phase == "Lexer"


def test_pipeline_stop_at_parser():
    src = "if x > 0\n    print(1)\n"
    res = compile_source(src)
    assert res.success is False
    assert res.phase_reached == "PARSER"
    assert res.ast is None
    assert len(res.tac) == 0
    assert len(res.diagnostics) == 1
    assert res.diagnostics[0].phase == "Parser"


def test_pipeline_stop_at_semantic():
    src = "x = 10\nx = \"incompatible\"\n"
    res = compile_source(src)
    assert res.success is False
    assert res.phase_reached == "SEMANTIC"
    assert res.ast is not None
    assert len(res.tac) == 0
    assert len(res.diagnostics) == 1
    assert res.diagnostics[0].phase == "Semantic"


def test_pipeline_all_examples():
    examples_dir = os.path.join(os.path.dirname(__file__), "..", "examples")
    for fname in sorted(os.listdir(examples_dir)):
        if not fname.endswith(".py"):
            continue
        path = os.path.join(examples_dir, fname)
        with open(path, "r", encoding="utf-8") as f:
            code = f.read()

        res = compile_source(code)
        if "syntax_error" in fname:
            assert res.success is False
            assert res.phase_reached == "PARSER"
        elif "semantic_error" in fname:
            assert res.success is False
            assert res.phase_reached == "SEMANTIC"
        else:
            assert res.success is True, f"Failed compiling example {fname}: {res.error_message}"
            assert res.phase_reached == "COMPLETED"
