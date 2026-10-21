import pytest
import shutil
from compiler.pipeline import compile_source
from compiler.validator import validate_program, run_representative_suite, generate_diff


def has_gxx() -> bool:
    return shutil.which("g++") is not None


@pytest.mark.skipif(not has_gxx(), reason="g++ compiler required for validation tests")
def test_validation_representative_suite():
    """Validates that all representative archetype programs pass behavioral equivalence."""
    results = run_representative_suite()
    assert len(results) == 5
    for res in results:
        assert res.status == "PASS", f"Test '{res.name}' failed:\nExpected: {res.expected_output}\nActual: {res.actual_output}\nDiff: {res.mismatch_details}\nNotes: {res.notes}"
        assert res.expected_output == res.actual_output
        assert res.compile_time > 0.0
        assert res.run_time >= 0.0


@pytest.mark.skipif(not has_gxx(), reason="g++ compiler required for validation tests")
def test_validation_arithmetic_equivalence():
    code = (
        "a = 20 // 3\n"
        "b = 20 % 3\n"
        "c = 20 / 4\n"
        "print(a, b, c)\n"
    )
    res = validate_program(code, name="Arithmetic Validation")
    assert res.status == "PASS"
    assert res.actual_output == "6 2 5.0"
    assert res.expected_output == "6 2 5.0"


@pytest.mark.skipif(not has_gxx(), reason="g++ compiler required for validation tests")
def test_validation_conditional_equivalence():
    code = (
        "x = 42\n"
        "if x > 50:\n"
        "    msg = \"high\"\n"
        "elif x > 20:\n"
        "    msg = \"medium\"\n"
        "else:\n"
        "    msg = \"low\"\n"
        "print(\"Result:\", msg)\n"
    )
    res = validate_program(code, name="Conditional Validation")
    assert res.status == "PASS"
    assert res.actual_output == "Result: medium"


@pytest.mark.skipif(not has_gxx(), reason="g++ compiler required for validation tests")
def test_validation_while_loop_equivalence():
    code = (
        "count = 1\n"
        "sum = 0\n"
        "while count <= 4:\n"
        "    sum = sum + count\n"
        "    count = count + 1\n"
        "print(\"Sum 1..4:\", sum)\n"
    )
    res = validate_program(code, name="While Loop Validation")
    assert res.status == "PASS"
    assert res.actual_output == "Sum 1..4: 10"


def test_validation_compilation_error_reporting():
    """Ensures syntax and semantic errors are reported honestly as COMPILATION_ERROR."""
    syntax_err_code = "if x > 0\n    print(1)\n"
    res_syntax = validate_program(syntax_err_code, name="Syntax Error Test")
    assert res_syntax.status == "COMPILATION_ERROR"
    assert "Parser" in res_syntax.notes or "Syntax" in res_syntax.notes

    semantic_err_code = "x = 10\nx = \"incompatible\"\n"
    res_semantic = validate_program(semantic_err_code, name="Semantic Error Test")
    assert res_semantic.status == "COMPILATION_ERROR"
    assert "Semantic" in res_semantic.notes


def test_validation_diff_generator():
    diff = generate_diff("Line 1\nLine 2", "Line 1\nLine 2 modified")
    assert "-Line 2" in diff
    assert "+Line 2 modified" in diff


def test_explainable_optimization_records():
    """Verifies that optimization records capture rule, original, replacement, and explanation."""
    code = (
        "a = 10 + 20\n"
        "if 10 > 5:\n"
        "    b = 1\n"
        "else:\n"
        "    b = 2\n"
    )
    comp_res = compile_source(code)
    assert comp_res.success is True
    assert len(comp_res.optimization_log) > 0

    for rec in comp_res.optimization_log:
        assert rec.pass_name in ("Constant Folding", "Branch Simplification", "Dead Code Elimination")
        assert rec.rule != ""
        assert rec.original is not None
        assert rec.replacement is not None
        assert rec.explanation != ""
