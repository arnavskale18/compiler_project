import subprocess
import shutil
import pytest
from compiler.pipeline import compile_source
from tests.test_codegen import compile_and_run_cpp, has_gxx


def test_division_and_modulo():
    src = (
        "f = 7 / 2\n"
        "i = 7 // 2\n"
        "m = 7 % 2\n"
        "print(\"f:\", f, \"i:\", i, \"m:\", m)\n"
    )
    res = compile_source(src)
    assert res.success is True
    if has_gxx():
        out = compile_and_run_cpp(res.cpp_code)
        assert out == "f: 3.5 i: 3 m: 1"


def test_nested_loops_and_conditionals():
    src = (
        "sum = 0\n"
        "i = 1\n"
        "while i <= 3:\n"
        "    j = 1\n"
        "    while j <= 3:\n"
        "        if (i * j) % 2 == 0:\n"
        "            sum = sum + (i * j)\n"
        "        j = j + 1\n"
        "    i = i + 1\n"
        "print(\"Sum:\", sum)\n"
    )
    res = compile_source(src)
    assert res.success is True
    if has_gxx():
        out = compile_and_run_cpp(res.cpp_code)
        # Pairs:
        # i=1: j=1 (1), j=2 (2*), j=3 (3) -> 2
        # i=2: j=1 (2*), j=2 (4*), j=3 (6*) -> 12
        # i=3: j=1 (3), j=2 (6*), j=3 (9) -> 6
        # Total = 2 + 12 + 6 = 20
        assert out == "Sum: 20"


def test_unary_negative_and_not():
    src = (
        "x = -15\n"
        "y = -x\n"
        "flag = not (y > 10)\n"
        "print(\"x:\", x, \"y:\", y, \"flag:\", flag)\n"
    )
    res = compile_source(src)
    assert res.success is True
    if has_gxx():
        out = compile_and_run_cpp(res.cpp_code)
        assert out == "x: -15 y: 15 flag: False"


def test_complex_constant_folding():
    src = (
        "c = 100 + (25 * 4) - (50 // 2)\n"
        "print(\"Result:\", c)\n"
    )
    res = compile_source(src)
    assert res.success is True
    # 100 + 100 - 25 = 175
    assign_c = [i for i in res.optimized_tac if i.dest == "c"]
    assert len(assign_c) == 1
    assert assign_c[0].arg1 == "175"
