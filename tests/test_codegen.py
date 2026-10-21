import subprocess
import tempfile
import os
import shutil
import pytest
from compiler.pipeline import compile_source


def has_gxx() -> bool:
    return shutil.which("g++") is not None


def compile_and_run_cpp(cpp_source: str) -> str:
    """Compiles C++ source with g++ and executes it, returning stdout."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_file = os.path.join(tmpdir, "out.cpp")
        exe_file = os.path.join(tmpdir, "out.exe" if os.name == "nt" else "out")

        with open(src_file, "w", encoding="utf-8") as f:
            f.write(cpp_source)

        # Compile
        compile_res = subprocess.run(
            ["g++", "-std=c++17", "-O2", src_file, "-o", exe_file],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if compile_res.returncode != 0:
            raise RuntimeError(f"C++ Compilation failed:\n{compile_res.stderr}")

        # Execute
        run_res = subprocess.run(
            [exe_file],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if run_res.returncode != 0:
            raise RuntimeError(f"Execution failed with return code {run_res.returncode}:\n{run_res.stderr}")

        return run_res.stdout.strip()


def test_codegen_syntax_structure():
    src = "x = 42\nprint(x)\n"
    res = compile_source(src)
    assert res.success is True
    assert "#include <iostream>" in res.cpp_code
    assert "int64_t x" in res.cpp_code
    assert "x = 42;" in res.cpp_code
    assert "int main()" in res.cpp_code


@pytest.mark.skipif(not has_gxx(), reason="g++ is not available on PATH")
def test_codegen_e2e_arithmetic():
    src = (
        "a = 10 + 5 * 2\n"
        "b = (20 - 4) // 2\n"
        "print(\"Result:\", a, b)\n"
    )
    res = compile_source(src)
    assert res.success is True
    output = compile_and_run_cpp(res.cpp_code)
    assert output == "Result: 20 8"


@pytest.mark.skipif(not has_gxx(), reason="g++ is not available on PATH")
def test_codegen_e2e_conditionals():
    src = (
        "x = 15\n"
        "if x > 20:\n"
        "    print(\"high\")\n"
        "elif x > 10:\n"
        "    print(\"medium\")\n"
        "else:\n"
        "    print(\"low\")\n"
    )
    res = compile_source(src)
    assert res.success is True
    output = compile_and_run_cpp(res.cpp_code)
    assert output == "medium"


@pytest.mark.skipif(not has_gxx(), reason="g++ is not available on PATH")
def test_codegen_e2e_while_loop():
    src = (
        "fact = 1\n"
        "i = 1\n"
        "while i <= 5:\n"
        "    fact = fact * i\n"
        "    i = i + 1\n"
        "print(\"Factorial 5:\", fact)\n"
    )
    res = compile_source(src)
    assert res.success is True
    output = compile_and_run_cpp(res.cpp_code)
    assert output == "Factorial 5: 120"
