"""CodeX — Source-to-Source Compiler Workbench (Streamlit Application).

A clean, light-mode compiler engineering workbench for university demonstrations.
Demonstrates all six phases of source-to-source compilation:
1. Lexical Analysis (Tokens)
2. Syntax Analysis (AST)
3. Semantic Analysis (Symbol Table & Type Checker)
4. Original Three-Address Code (TAC)
5. Optimized Three-Address Code (Explainable TAC Optimization)
6. Generated C++17 Target Code
7. Behavior Validation & Semantic Parity Verification
"""

import os
import subprocess
import tempfile
import time
from typing import Optional, Dict, Any, List

import streamlit as st
import pandas as pd

from compiler.pipeline import compile_source, CompilationResult
from compiler.lexer import TokenType
from compiler.validator import validate_program, run_representative_suite, ValidationResult


EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "examples")

EXAMPLE_DESCRIPTIONS = {
    "01_arithmetic.py": "Arithmetic, precedence, float division, modulo, and string concatenation",
    "02_conditionals.py": "Branching control flow with if, elif, else, and boolean expressions",
    "03_loops.py": "While loops, iteration counters, and accumulators (Factorial & Sum)",
    "04_nested_blocks.py": "Nested while loops and conditionals with scoped variables",
    "05_optimization.py": "Constant folding benchmark, branch simplification, and DCE",
    "06_syntax_error.py": "Intentional syntax error demo (missing colon after if statement)",
    "07_semantic_error.py": "Intentional semantic error demo (incompatible type reassignment)",
}


def load_example(filename: str) -> str:
    path = os.path.join(EXAMPLES_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


# -----------------------------------------------------------------------------
# Streamlit Page Config & Professional Light-Mode CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="CodeX — Compiler Workbench",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

LIGHT_MODE_CSS = """
<style>
/* Main Page Background and Text Typography */
body, .stApp {
    background-color: #ffffff;
    color: #0f172a;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background-color: #f8fafc;
    border-right: 1px solid #e2e8f0;
}

/* Headers */
h1, h2, h3, h4, h5, h6 {
    color: #0f172a !important;
    font-weight: 700 !important;
}

/* Clean Header Card */
.header-container {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 20px 24px;
    margin-bottom: 20px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
}
.header-title-row {
    display: flex;
    align-items: center;
    gap: 12px;
}
.header-title {
    font-size: 1.85rem;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: -0.02em;
    margin: 0;
}
.header-badge {
    display: inline-block;
    padding: 3px 9px;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    background-color: #eff6ff;
    color: #1d4ed8;
    border: 1px solid #dbeafe;
}
.header-subtitle {
    color: #475569;
    font-size: 0.95rem;
    margin-top: 6px;
    margin-bottom: 0;
}

/* Professional Status Pills */
.status-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 0.82rem;
    font-weight: 600;
}
.status-pill-success {
    background-color: #f0fdf4;
    color: #166534;
    border: 1px solid #bbf7d0;
}
.status-pill-error {
    background-color: #fff1f2;
    color: #9f1239;
    border: 1px solid #fecdd3;
}

/* Card panels */
.panel-card {
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 16px 18px;
    margin-bottom: 16px;
}
.panel-card-title {
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #475569;
    margin-bottom: 8px;
}

/* Tab labels styling */
button[data-baseweb="tab"] {
    font-weight: 600;
    font-size: 0.9rem;
    color: #475569 !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #1d4ed8 !important;
    border-bottom-color: #2563eb !important;
}

/* Metric styling */
[data-testid="stMetricValue"] {
    color: #0f172a !important;
    font-weight: 700 !important;
}
[data-testid="stMetricLabel"] {
    color: #64748b !important;
    font-weight: 600 !important;
}

/* Buttons */
.stButton > button[kind="primary"] {
    background-color: #2563eb;
    color: #ffffff;
    border: none;
    font-weight: 600;
    border-radius: 6px;
    box-shadow: 0 1px 2px rgba(37, 99, 235, 0.2);
    transition: background-color 0.15s ease-in-out;
}
.stButton > button[kind="primary"]:hover {
    background-color: #1d4ed8;
    color: #ffffff;
}
.stButton > button[kind="secondary"] {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    font-weight: 600;
    border-radius: 6px;
}
.stButton > button[kind="secondary"]:hover {
    background-color: #f8fafc;
    border-color: #94a3b8;
}

/* Code area custom border */
textarea {
    font-family: "JetBrains Mono", "SF Mono", "Fira Code", Consolas, monospace !important;
    font-size: 0.9rem !important;
    border-radius: 6px !important;
    border: 1px solid #cbd5e1 !important;
    background-color: #ffffff !important;
    color: #0f172a !important;
}
</style>
"""
st.markdown(LIGHT_MODE_CSS, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Sidebar Configuration & Sample Program Selector
# -----------------------------------------------------------------------------
st.sidebar.markdown("### ⚡ CodeX Workbench")
st.sidebar.caption("Pedagogical Source-to-Source Compiler: Python ➔ C++17")

examples_list = [
    ("01_arithmetic.py", "1. Arithmetic & Precedence"),
    ("02_conditionals.py", "2. Conditionals (if / elif / else)"),
    ("03_loops.py", "3. While Loops & Accumulators"),
    ("04_nested_blocks.py", "4. Nested Blocks & Scopes"),
    ("05_optimization.py", "5. Optimization (Folding & DCE)"),
    ("06_syntax_error.py", "6. Syntax Error Diagnostic Demo"),
    ("07_semantic_error.py", "7. Semantic Error Diagnostic Demo"),
]

selected_sample_file = st.sidebar.selectbox(
    "Select Sample Program",
    options=[e[0] for e in examples_list],
    format_func=lambda x: dict(examples_list).get(x, x),
    key="sample_selector",
)

sample_desc = EXAMPLE_DESCRIPTIONS.get(selected_sample_file, "")
if sample_desc:
    st.sidebar.info(f"**Description:** {sample_desc}")

if "last_loaded_sample" not in st.session_state:
    st.session_state["last_loaded_sample"] = selected_sample_file
    st.session_state["source_text"] = load_example(selected_sample_file)

if st.session_state["last_loaded_sample"] != selected_sample_file:
    st.session_state["last_loaded_sample"] = selected_sample_file
    st.session_state["source_text"] = load_example(selected_sample_file)

if st.sidebar.button("🔄 Reset Editor to Sample Default", use_container_width=True):
    st.session_state["source_text"] = load_example(selected_sample_file)

st.sidebar.markdown("---")
st.sidebar.markdown("#### 🏛️ Six-Phase Pipeline")
st.sidebar.markdown(
    """
    1. **Lexical Analysis**: Tokens, Indent/Dedent, Line/Col
    2. **Syntax Analysis**: Recursive Descent, Explicit AST
    3. **Semantic Analysis**: Scoped Symbol Table, Type Inference
    4. **Original TAC**: Linearized Three-Address Instructions
    5. **Optimized TAC**: Explainable Constant Folding & DCE
    6. **Generated C++**: Idiomatic C++17 with Runtime Helpers
    """
)

st.sidebar.markdown("---")
st.sidebar.caption("CodeX Compiler v1.0 • Academic Demonstration")


# -----------------------------------------------------------------------------
# Main Header Card
# -----------------------------------------------------------------------------
st.markdown(
    """
    <div class="header-container">
        <div class="header-title-row">
            <h1 class="header-title">CodeX</h1>
            <span class="header-badge">v1.0 • Academic Workbench</span>
        </div>
        <p class="header-subtitle">
            Source-to-Source Compiler translating a typed Python subset into optimized C++17 across all six classic compiler phases.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Source Code Input & Control Bar
# -----------------------------------------------------------------------------
col_editor, col_controls = st.columns([7, 3])

with col_editor:
    source_code = st.text_area(
        "Source Code (Python-like subset):",
        value=st.session_state.get("source_text", ""),
        height=260,
        key="source_editor_input",
        help="Edit code directly or pick a pre-built example from the sidebar.",
    )

with col_controls:
    st.markdown('<div class="panel-card-title">Compilation Controls</div>', unsafe_allow_html=True)
    compile_btn = st.button("🚀 Compile Source", type="primary", use_container_width=True)
    st.caption("Executes all six compiler phases on the input source code.")

    # Execute actual compilation
    result: CompilationResult = compile_source(source_code)

    st.markdown('<div class="panel-card-title" style="margin-top: 14px;">Pipeline Status</div>', unsafe_allow_html=True)
    if result.success:
        st.markdown(
            '<div class="status-pill status-pill-success">✓ ALL 6 PHASES PASSED</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            f"• Tokens: **{len(result.tokens)}**<br>"
            f"• Original TAC: **{len(result.tac)}** instructions<br>"
            f"• Optimized TAC: **{len(result.optimized_tac)}** instructions",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="status-pill status-pill-error">✗ STOPPED AT {result.phase_reached}</div>',
            unsafe_allow_html=True,
        )
        st.error(result.error_message or "Compilation error occurred.")

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Seven Demonstration Tabs
# -----------------------------------------------------------------------------
tab_tokens, tab_ast, tab_semantic, tab_orig_tac, tab_opt_tac, tab_cpp, tab_validation = st.tabs(
    [
        "Tokens",
        "AST",
        "Semantic Analysis",
        "Original TAC",
        "Optimized TAC",
        "Generated C++",
        "Validation",
    ]
)


# -----------------------------------------------------------------------------
# 1. TOKENS TAB
# -----------------------------------------------------------------------------
with tab_tokens:
    st.markdown("### Phase 1: Lexical Analysis")
    st.caption("Scans raw source characters into typed tokens, tracking line/column coordinates and layout indentation.")

    if result.tokens:
        tok_data = [
            {
                "Index": i,
                "Token Type": tok.type.value,
                "Lexeme / Value": repr(tok.value),
                "Line": tok.line,
                "Column": tok.column,
            }
            for i, tok in enumerate(result.tokens)
        ]
        df_tokens = pd.DataFrame(tok_data)

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Tokens Emitted", len(result.tokens))
        m2.metric("Distinct Token Kinds", df_tokens["Token Type"].nunique())
        m3.metric("Source Lines Scanned", df_tokens["Line"].max() if not df_tokens.empty else 0)

        filter_col, _ = st.columns([4, 6])
        with filter_col:
            search_query = st.text_input("🔍 Filter tokens by name or value:", "")

        if search_query:
            filtered_df = df_tokens[
                df_tokens["Token Type"].str.contains(search_query, case=False)
                | df_tokens["Lexeme / Value"].str.contains(search_query, case=False)
            ]
        else:
            filtered_df = df_tokens

        st.dataframe(filtered_df, use_container_width=True, height=360)
    else:
        st.warning("No tokens produced. Review lexical diagnostics.")


# -----------------------------------------------------------------------------
# 2. AST TAB
# -----------------------------------------------------------------------------
with tab_ast:
    st.markdown("### Phase 2: Syntax Analysis & AST Construction")
    st.caption("Custom grammar-based recursive descent parser constructing an explicit, typed Abstract Syntax Tree.")

    if result.ast:
        col_tree, col_inspect = st.columns([6, 4])
        with col_tree:
            st.markdown("##### Visual AST Hierarchy (ASCII Tree)")
            st.code(result.ast_tree_str, language="text")

        with col_inspect:
            st.markdown("##### AST Node Attributes (Structured)")
            st.json(result.ast.to_dict(), expanded=False)
    else:
        st.info("AST not available: Compilation stopped prior to or during syntax analysis.")


# -----------------------------------------------------------------------------
# 3. SEMANTIC ANALYSIS TAB
# -----------------------------------------------------------------------------
with tab_semantic:
    st.markdown("### Phase 3: Semantic Analysis & Symbol Table")
    st.caption("Performs static type checking, undeclared identifier detection, scope resolution, and type promotion.")

    if result.symbols:
        df_sym = pd.DataFrame(result.symbols)
        df_sym.rename(
            columns={
                "name": "Identifier Name",
                "type": "Inferred Static Type",
                "scope_level": "Scope Depth",
                "line_declared": "Line Declared",
                "column_declared": "Col Declared",
                "is_initialized": "Initialized",
            },
            inplace=True,
        )

        st.markdown("##### Scoped Symbol Table")
        st.dataframe(df_sym, use_container_width=True)

        st.markdown("##### Type System Invariants Enforced")
        st.markdown(
            """
            - **Declaration by Assignment**: Variables receive a static type upon their initial assignment.
            - **Type Compatibility**: Reassignment requires matching types, or safe numeric promotion (`int` ➔ `float`).
            - **Division Semantics**: True division `/` yields `float`; floor division `//` and modulo `%` yield `int`.
            - **Condition Invariants**: All `if`, `elif`, and `while` conditions must strictly evaluate to `bool`.
            - **Undeclared Identifier Guard**: Any reference to a variable before assignment immediately halts compilation.
            """
        )
    elif result.diagnostics and result.phase_reached == "SEMANTIC":
        st.markdown("##### Semantic Diagnostics")
        for diag in result.diagnostics:
            st.error(f"Semantic Error [Line {diag.line}, Col {diag.column}]: {diag.message}")
    else:
        st.info("Semantic analysis not reached. Resolve earlier syntax or lexical errors.")


# -----------------------------------------------------------------------------
# 4. ORIGINAL TAC TAB
# -----------------------------------------------------------------------------
with tab_orig_tac:
    st.markdown("### Phase 4: Original Three-Address Code (TAC)")
    st.caption("Linear intermediate representation with deterministic temporaries, labels, and explicit control-flow jumps.")

    if result.tac:
        c1, c2, c3 = st.columns(3)
        c1.metric("Instruction Count", len(result.tac))
        temps = {i.dest for i in result.tac if i.dest and i.dest.startswith("t") and i.dest[1:].isdigit()}
        c2.metric("Temporaries Allocated", len(temps))
        labels = {i.dest for i in result.tac if i.op.value == "LABEL" and i.dest}
        c3.metric("Control Flow Labels", len(labels))

        st.markdown("##### Linearized TAC Instruction Stream")
        st.code(result.tac_str, language="text")
    else:
        st.info("Original TAC generation not reached.")


# -----------------------------------------------------------------------------
# 5. OPTIMIZED TAC TAB (Explainable Optimization)
# -----------------------------------------------------------------------------
with tab_opt_tac:
    st.markdown("### Phase 5: Optimized Three-Address Code (TAC)")
    st.caption("Demonstrates explainable constant folding, dead-branch pruning, and dead-code elimination with explicit rules.")

    if result.optimized_tac:
        orig_count = len(result.tac)
        opt_count = len(result.optimized_tac)
        reduction = orig_count - opt_count
        reduction_pct = (reduction / orig_count * 100) if orig_count > 0 else 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Original Instructions", orig_count)
        m2.metric("Optimized Instructions", opt_count)
        m3.metric("Instructions Reduced", reduction)
        m4.metric("Instruction Reduction", f"{reduction_pct:.1f}%")

        col_orig, col_opt = st.columns(2)
        with col_orig:
            st.markdown("##### Original TAC Instruction Stream")
            st.code(result.tac_str, language="text")

        with col_opt:
            st.markdown("##### Optimized TAC Instruction Stream")
            st.code(result.optimized_tac_str, language="text")

        st.markdown("##### Explainable Optimization Log (Applied Rules & Rationale)")
        if result.optimization_log:
            log_entries = [
                {
                    "Rule Applied": getattr(rec, "rule", rec.pass_name),
                    "Pass Category": rec.pass_name,
                    "Original Instruction": rec.original or "-",
                    "Optimized Result": rec.replacement or "-",
                    "Concise Explanation": getattr(rec, "explanation", rec.description),
                }
                for rec in result.optimization_log
            ]
            st.dataframe(pd.DataFrame(log_entries), use_container_width=True)
        else:
            st.info("No transformation opportunities detected. The intermediate code is already in minimal form.")
    else:
        st.info("Optimized TAC not reached. Resolve earlier compilation errors.")


# -----------------------------------------------------------------------------
# 6. GENERATED C++ TAB
# -----------------------------------------------------------------------------
with tab_cpp:
    st.markdown("### Phase 6: Generated C++17 Target Code")
    st.caption("Emits standard, idiomatic C++17 with explicit types, runtime helpers, and main() entry point.")

    if result.cpp_code:
        st.download_button(
            label="💾 Download Generated C++ Source (.cpp)",
            data=result.cpp_code,
            file_name="codex_output.cpp",
            mime="text/x-c++src",
            use_container_width=False,
        )
        st.code(result.cpp_code, language="cpp")
    else:
        st.info("C++ target code generation not reached.")


# -----------------------------------------------------------------------------
# 7. VALIDATION TAB (Behavioral Equivalence & Verification)
# -----------------------------------------------------------------------------
with tab_validation:
    st.markdown("### Phase 7: Behavior Validation & Parity Verification")
    st.caption(
        "Validates observable runtime behavior by comparing the Python reference interpreter against the compiled C++17 binary."
    )

    # Sub-section A: Active Program Validation
    st.markdown("#### 1. Active Program Validation")
    st.markdown("Compiles the code currently in the editor and compares its stdout output against native Python execution.")

    if result.success and result.cpp_code:
        run_validation_btn = st.button("▶ Run Validation on Active Program", type="primary")

        if run_validation_btn:
            with st.spinner("Validating active program (compiling with g++ and comparing outputs)..."):
                val_res = validate_program(source_code, name="Active Program")

            if val_res.status == "PASS":
                st.markdown(
                    f'<div class="status-pill status-pill-success">✓ PASS — EXACT OUTPUT PARITY CONFIRMED</div> '
                    f'<span style="font-size:0.85rem; color:#64748b; margin-left:8px;">Compile: {val_res.compile_time:.3f}s | Run: {val_res.run_time:.3f}s</span>',
                    unsafe_allow_html=True,
                )
            elif val_res.status == "FAIL":
                st.markdown(
                    '<div class="status-pill status-pill-error">✗ FAIL — OUTPUT MISMATCH DETECTED</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="status-pill status-pill-error">✗ {val_res.status}</div>',
                    unsafe_allow_html=True,
                )

            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            col_cpp_out, col_py_out = st.columns(2)
            with col_cpp_out:
                st.markdown("##### Compiled C++17 Output (`stdout`):")
                st.code(val_res.actual_output or "(no output printed)", language="text")

            with col_py_out:
                st.markdown("##### Expected Python Reference Output (`stdout`):")
                st.code(val_res.expected_output or "(no output printed)", language="text")

            if val_res.status == "FAIL" and val_res.mismatch_details:
                st.markdown("##### Output Discrepancy Diff:")
                st.code(val_res.mismatch_details, language="diff")

            if val_res.notes:
                st.caption(f"**Verification Notes:** {val_res.notes}")
    else:
        st.warning("Resolve compiler diagnostics before running behavior validation.")

    st.markdown("---")

    # Sub-section B: Representative Archetype Suite
    st.markdown("#### 2. Representative Archetype Test Suite")
    st.markdown(
        "Execute automated behavioral verification across five representative benchmark programs covering arithmetic, conditionals, loops, nested blocks, and constant optimization."
    )

    run_suite_btn = st.button("🧪 Run Representative Suite (5 Core Archetypes)")

    if run_suite_btn:
        with st.spinner("Executing representative validation test suite with g++..."):
            suite_results = run_representative_suite()

        passed_count = sum(1 for r in suite_results if r.status == "PASS")
        total_count = len(suite_results)

        m1, m2, m3 = st.columns(3)
        m1.metric("Archetype Tests Run", total_count)
        m2.metric("Tests Passed", passed_count)
        m3.metric("Pass Rate", f"{(passed_count / total_count * 100):.1f}%")

        suite_rows = [r.to_dict() for r in suite_results]
        st.dataframe(pd.DataFrame(suite_rows), use_container_width=True)

        for r in suite_results:
            if r.status != "PASS":
                st.error(f"Failure in '{r.name}': {r.notes}")
                if r.mismatch_details:
                    st.code(r.mismatch_details, language="diff")

    st.markdown("---")

    # Sub-section C: Academic Language Semantics Disclosure
    st.markdown("#### 3. Language Scope & Semantics Disclosure")
    st.markdown(
        """
        - **Documented Semantics**: Verification evaluates stdout equivalence against the defined language subset: 64-bit signed integers (`int64_t`), floating-point doubles (`double`), booleans (`bool`), string literals, Python-style floor division (`//`), modulo (`%`), and structured control flow.
        - **Scope of Equivalence**: Equivalence is demonstrated for supported constructs and observable program behavior; it does not claim formal semantics or compatibility with unrestricted Python features (e.g. arbitrary-precision bigints, classes, or dynamic duck typing).
        """
    )
