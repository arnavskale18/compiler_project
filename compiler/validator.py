"""Validation and Behavioral Equivalence Engine for CodeX.

Compares observable execution behavior between the Python reference interpreter
and the compiled C++17 target executable across representative programs.
Reports exact PASS/FAIL status, execution times, and line-by-line mismatch diagnostics.
"""

from dataclasses import dataclass
import difflib
import os
import subprocess
import tempfile
import time
from typing import Optional, List, Dict, Any

from .pipeline import compile_source, CompilationResult


@dataclass
class ValidationResult:
    name: str
    category: str
    status: str  # "PASS", "FAIL", "COMPILATION_ERROR", "EXECUTION_ERROR", "TIMEOUT"
    expected_output: str = ""
    actual_output: str = ""
    mismatch_details: Optional[str] = None
    compile_time: float = 0.0
    run_time: float = 0.0
    notes: str = ""
    source_code: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "Test Name": self.name,
            "Category": self.category,
            "Status": self.status,
            "Expected (Python)": self.expected_output,
            "Actual (C++17)": self.actual_output,
            "Compile Time (s)": round(self.compile_time, 3),
            "Run Time (s)": round(self.run_time, 3),
            "Notes": self.notes,
        }


def run_cpp_code(cpp_code: str) -> Dict[str, Any]:
    """Compiles C++ code with g++ -std=c++17 -O2 and executes it safely with a 5s threshold."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = os.path.join(tmpdir, "main.cpp")
        exe_path = os.path.join(tmpdir, "main.exe" if os.name == "nt" else "main")

        with open(src_path, "w", encoding="utf-8") as f:
            f.write(cpp_code)

        start_compile = time.time()
        try:
            compile_proc = subprocess.run(
                ["g++", "-std=c++17", "-O2", src_path, "-o", exe_path],
                capture_output=True,
                text=True,
                timeout=15,
            )
        except Exception as e:
            return {
                "success": False,
                "stage": "Compilation",
                "error": str(e),
                "compile_time": 0.0,
                "run_time": 0.0,
            }

        compile_time = time.time() - start_compile

        if compile_proc.returncode != 0:
            return {
                "success": False,
                "stage": "Compilation",
                "error": compile_proc.stderr or compile_proc.stdout,
                "compile_time": compile_time,
                "run_time": 0.0,
            }

        start_run = time.time()
        try:
            run_proc = subprocess.run(
                [exe_path],
                capture_output=True,
                text=True,
                timeout=5,
            )
            run_time = time.time() - start_run
            return {
                "success": run_proc.returncode == 0,
                "stage": "Execution",
                "stdout": run_proc.stdout.strip(),
                "stderr": run_proc.stderr.strip(),
                "exit_code": run_proc.returncode,
                "compile_time": compile_time,
                "run_time": run_time,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stage": "Execution",
                "error": "Execution timed out (5s threshold).",
                "compile_time": compile_time,
                "run_time": 5.0,
            }
        except Exception as e:
            return {
                "success": False,
                "stage": "Execution",
                "error": str(e),
                "compile_time": compile_time,
                "run_time": 0.0,
            }


def run_python_code(py_code: str) -> Dict[str, Any]:
    """Runs source Python script to obtain ground-truth reference output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        py_file = os.path.join(tmpdir, "ref.py")
        with open(py_file, "w", encoding="utf-8") as f:
            f.write(py_code)
        try:
            res = subprocess.run(
                ["python", py_file],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return {
                "success": res.returncode == 0,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip(),
            }
        except Exception as e:
            return {"success": False, "stdout": "", "stderr": str(e)}


def generate_diff(expected: str, actual: str) -> str:
    """Generates a human-readable unified diff between expected and actual output."""
    exp_lines = expected.splitlines(keepends=True)
    act_lines = actual.splitlines(keepends=True)
    diff = difflib.unified_diff(
        exp_lines,
        act_lines,
        fromfile="Expected (Python Reference)",
        tofile="Actual (C++17 Output)",
        lineterm="",
    )
    return "".join(diff)


def validate_program(
    source_code: str,
    name: str = "Active Program",
    category: str = "General",
) -> ValidationResult:
    """Performs end-to-end compilation, reference execution, and output comparison."""
    # Step 1: Compile source with CodeX pipeline
    comp_res: CompilationResult = compile_source(source_code)
    if not comp_res.success:
        return ValidationResult(
            name=name,
            category=category,
            status="COMPILATION_ERROR",
            notes=f"CodeX compilation stopped at {comp_res.phase_reached} phase: {comp_res.error_message}",
            source_code=source_code,
        )

    # Step 2: Run Python reference
    py_res = run_python_code(source_code)
    if not py_res["success"]:
        return ValidationResult(
            name=name,
            category=category,
            status="EXECUTION_ERROR",
            notes=f"Python reference execution failed: {py_res['stderr']}",
            source_code=source_code,
        )

    # Step 3: Compile and run generated C++ code
    cpp_res = run_cpp_code(comp_res.cpp_code)
    if not cpp_res["success"]:
        return ValidationResult(
            name=name,
            category=category,
            status="EXECUTION_ERROR" if cpp_res.get("stage") == "Execution" else "COMPILATION_ERROR",
            compile_time=cpp_res.get("compile_time", 0.0),
            run_time=cpp_res.get("run_time", 0.0),
            notes=f"g++ {cpp_res.get('stage')} failed: {cpp_res.get('error')}",
            source_code=source_code,
        )

    expected = py_res["stdout"]
    actual = cpp_res["stdout"]

    if expected == actual:
        return ValidationResult(
            name=name,
            category=category,
            status="PASS",
            expected_output=expected,
            actual_output=actual,
            compile_time=cpp_res["compile_time"],
            run_time=cpp_res["run_time"],
            notes="Exact stdout match between Python reference and compiled C++17.",
            source_code=source_code,
        )
    else:
        diff_str = generate_diff(expected, actual)
        return ValidationResult(
            name=name,
            category=category,
            status="FAIL",
            expected_output=expected,
            actual_output=actual,
            mismatch_details=diff_str,
            compile_time=cpp_res["compile_time"],
            run_time=cpp_res["run_time"],
            notes="Output mismatch detected between Python reference and generated C++.",
            source_code=source_code,
        )


REPRESENTATIVE_PROGRAMS = [
    (
        "Arithmetic & Operator Precedence",
        "Arithmetic",
        (
            "x = 10 + 5 * 2\n"
            "y = (10 + 5) * 2\n"
            "z = 15 // 4\n"
            "rem = 15 % 4\n"
            "div = 10 / 4\n"
            "greeting = \"Hello \" + \"World\"\n"
            "print(\"x:\", x)\n"
            "print(\"y:\", y)\n"
            "print(\"z:\", z)\n"
            "print(\"rem:\", rem)\n"
            "print(\"div:\", div)\n"
            "print(\"greeting:\", greeting)\n"
        ),
    ),
    (
        "Branching Conditionals (if / elif / else)",
        "Conditionals",
        (
            "score = 85\n"
            "if score >= 90:\n"
            "    grade = \"A\"\n"
            "elif score >= 80:\n"
            "    grade = \"B\"\n"
            "else:\n"
            "    grade = \"C\"\n"
            "is_valid = score >= 50 and not (score > 100)\n"
            "print(\"Grade:\", grade)\n"
            "print(\"Valid:\", is_valid)\n"
        ),
    ),
    (
        "While Loop Accumulator & Factorial",
        "Loops",
        (
            "n = 5\n"
            "fact = 1\n"
            "curr = 1\n"
            "while curr <= n:\n"
            "    fact = fact * curr\n"
            "    curr = curr + 1\n"
            "print(\"Factorial 5:\", fact)\n"
        ),
    ),
    (
        "Nested Loops & Conditions",
        "Nested Blocks",
        (
            "r = 1\n"
            "evens = 0\n"
            "while r <= 3:\n"
            "    c = 1\n"
            "    while c <= 3:\n"
            "        if (r * c) % 2 == 0:\n"
            "            evens = evens + 1\n"
            "        c = c + 1\n"
            "    r = r + 1\n"
            "print(\"Evens in 3x3:\", evens)\n"
        ),
    ),
    (
        "Constant Folding Behavior Preservation",
        "Optimization",
        (
            "folded = 100 + (25 * 4) - (50 // 2)\n"
            "if 10 > 5:\n"
            "    res = folded + 10\n"
            "else:\n"
            "    res = 0\n"
            "print(\"Result:\", res)\n"
        ),
    ),
]


def run_representative_suite() -> List[ValidationResult]:
    """Runs behavioral validation across all representative archetype programs."""
    results: List[ValidationResult] = []
    for name, cat, code in REPRESENTATIVE_PROGRAMS:
        res = validate_program(code, name=name, category=cat)
        results.append(res)
    return results
