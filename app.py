"""CodeX — Source-to-Source Compiler Workbench (Streamlit Application).

An academic-grade, modern compiler engineering workbench demonstrating
all six classic phases of source-to-source compilation:
1. Lexical Analysis (Tokens & Coordinate Tracking)
2. Syntax Analysis (Recursive Descent & Typed AST)
3. Semantic Analysis (Scoped Symbol Table & Type Invariants)
4. Original Three-Address Code (TAC Linearization)
5. Optimized Three-Address Code (Explainable -O0 to -O3 Optimization)
6. Generated C++17 Target Code
7. Behavior Validation (Differential Execution vs Python Interpreter)
8. Source-Level Execution Profiler (High-Resolution Wall-Clock Telemetry)
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
from compiler.validator import validate_program, run_representative_suite, ValidationResult, profile_cpp_code


EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "examples")

EXAMPLE_DESCRIPTIONS = {
    "01_arithmetic.py": "Arithmetic precedence, float division (/), floor division (//), modulo (%), and string concatenation",
    "02_conditionals.py": "Branching control flow with if, elif, else, and compound boolean expressions",
    "03_loops.py": "While loops, iteration counters, and accumulators (Factorial & Summation)",
    "04_nested_blocks.py": "Nested while loops and conditionals with deeply scoped variables",
    "05_optimization.py": "Constant folding benchmark, branch simplification, and dead-code elimination (DCE)",
    "06_syntax_error.py": "Intentional syntax error demo (missing colon after if statement)",
    "07_semantic_error.py": "Intentional semantic error demo (incompatible type reassignment)",
}

OPT_LEVEL_OPTIONS = [
    "-O0 (None — No optimization)",
    "-O1 (Basic — Constant Folding + Branch Simplification)",
    "-O2 (Standard — O1 + Unused Temp Elimination)  ← default",
    "-O3 (Aggressive — Multi-pass Fixed-Point, all passes)",
]

OPT_LEVEL_DESCRIPTIONS = {
    0: "**-O0 (None)** — All optimization passes disabled. Raw TAC is passed through unmodified.",
    1: "**-O1 (Basic)** — Single-pass Constant Folding & Branch Simplification.",
    2: "**-O2 (Standard)** — O1 passes plus Unused Temporary Elimination (single pass).",
    3: "**-O3 (Aggressive)** — Multi-pass fixed-point loop across all four passes (up to 10 iterations).",
}


def load_example(filename: str) -> str:
    path = os.path.join(EXAMPLES_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


# -----------------------------------------------------------------------------
# Streamlit Page Config & Premium Developer-Grade CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="CodeX — Compiler Studio",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

STUDIO_CSS = """
<style>
/* ── Google Fonts Import ─────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Outfit:wght@500;600;700;800;900&display=swap');

/* ── Base Canvas & Typography ────────────────────────────────────────── */
:root {
    --primary-indigo: #4f46e5;
    --primary-blue: #2563eb;
    --accent-cyan: #06b6d4;
    --accent-emerald: #10b981;
    --accent-rose: #f43f5e;
    --bg-page: #f8fafc;
    --surface-card: #ffffff;
    --surface-glass: rgba(255, 255, 255, 0.88);
    --border-subtle: #e2e8f0;
    --border-strong: #cbd5e1;
    --text-heading: #0f172a;
    --text-body: #334155;
    --text-muted: #64748b;
}

body, .stApp {
    background-color: var(--bg-page);
    color: var(--text-body);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    -webkit-font-smoothing: antialiased;
}

/* ── Sidebar Styling ─────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
    border-right: 1px solid var(--border-subtle);
    box-shadow: 2px 0 12px rgba(15, 23, 42, 0.02);
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
    font-family: 'Outfit', sans-serif !important;
    font-size: 1.35rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em !important;
    color: #0f172a !important;
}

/* ── Headings ────────────────────────────────────────────────────────── */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Outfit', 'Inter', sans-serif !important;
    color: var(--text-heading) !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
}

/* ── Hero Banner Header ─────────────────────────────────────────────── */
.hero-header {
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 60%, #eef2ff 100%);
    border: 1px solid rgba(226, 232, 240, 0.9);
    border-radius: 14px;
    padding: 24px 28px;
    margin-bottom: 22px;
    box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.05), 0 2px 6px -1px rgba(15, 23, 42, 0.02);
    position: relative;
    overflow: hidden;
}
.hero-header::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, #3b82f6, #6366f1, #8b5cf6, #06b6d4);
}
.hero-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
}
.hero-title-group {
    display: flex;
    align-items: center;
    gap: 12px;
}
.hero-title {
    font-family: 'Outfit', sans-serif;
    font-size: 2.1rem;
    font-weight: 900;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #4338ca 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
    line-height: 1.1;
}
.hero-tag {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 10px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    background: #eef2ff;
    color: #4338ca;
    border: 1px solid #c7d2fe;
}
.hero-subtitle {
    color: #475569;
    font-size: 0.96rem;
    margin-top: 8px;
    margin-bottom: 0;
    line-height: 1.5;
}

/* ── Code Editor Container (Window Frame) ────────────────────────────── */
.editor-frame {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 4px 16px -2px rgba(15, 23, 42, 0.06);
    margin-bottom: 14px;
}
.editor-bar {
    background: #f1f5f9;
    border-bottom: 1px solid #e2e8f0;
    padding: 8px 14px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.window-dots {
    display: flex;
    gap: 6px;
    align-items: center;
}
.dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
}
.dot-red { background-color: #ef4444; }
.dot-yellow { background-color: #f59e0b; }
.dot-green { background-color: #10b981; }
.editor-bar-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    font-weight: 600;
    color: #475569;
}
.editor-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: #64748b;
    background: #ffffff;
    padding: 2px 8px;
    border-radius: 4px;
    border: 1px solid #e2e8f0;
}

/* Custom Text Area styling */
textarea {
    font-family: "JetBrains Mono", Consolas, monospace !important;
    font-size: 0.92rem !important;
    line-height: 1.55 !important;
    border-radius: 0 0 10px 10px !important;
    border: none !important;
    background-color: #ffffff !important;
    color: #0f172a !important;
    padding: 14px 16px !important;
}
textarea:focus {
    outline: none !important;
    box-shadow: inset 0 0 0 2px #4f46e5 !important;
}

/* ── Dynamic Pulsing Status Pills ───────────────────────────────────── */
.status-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 7px 14px;
    border-radius: 8px;
    font-size: 0.84rem;
    font-weight: 700;
    letter-spacing: 0.02em;
}
.status-pill-success {
    background-color: #ecfdf5;
    color: #065f46;
    border: 1px solid #a7f3d0;
}
.status-pill-success::before {
    content: '';
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #10b981;
    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.25);
}
.status-pill-error {
    background-color: #fff1f2;
    color: #9f1239;
    border: 1px solid #fecdd3;
}
.status-pill-error::before {
    content: '';
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #f43f5e;
    box-shadow: 0 0 0 3px rgba(244, 63, 94, 0.25);
}

/* ── Optimization Level Badges ──────────────────────────────────────── */
.opt-badge {
    display: inline-flex;
    align-items: center;
    padding: 4px 10px;
    border-radius: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.opt-badge-O0 { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }
.opt-badge-O1 { background: #fefce8; color: #854d0e; border: 1px solid #fef08a; }
.opt-badge-O2 { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; box-shadow: 0 0 8px rgba(37, 99, 235, 0.15); }
.opt-badge-O3 { background: #fdf4ff; color: #7e22ce; border: 1px solid #e9d5ff; box-shadow: 0 0 8px rgba(168, 85, 247, 0.2); }

/* ── Modern Card Panels ─────────────────────────────────────────────── */
.modern-card {
    background: #ffffff;
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 18px 22px;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.03);
    margin-bottom: 16px;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.modern-card:hover {
    box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
}
.card-header-title {
    font-family: 'Outfit', sans-serif;
    font-size: 0.92rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #475569;
    margin-bottom: 10px;
}

/* ── Profiler Hero Card ─────────────────────────────────────────────── */
.profiler-telemetry-card {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    color: #f8fafc;
    border-radius: 14px;
    padding: 22px 26px;
    margin-bottom: 18px;
    box-shadow: 0 8px 30px rgba(15, 23, 42, 0.2);
    position: relative;
    border: 1px solid #334155;
    overflow: hidden;
}
.profiler-telemetry-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, #06b6d4, #3b82f6, #a855f7);
}
.profiler-title {
    font-family: 'Outfit', sans-serif;
    font-size: 1.1rem;
    font-weight: 800;
    color: #38bdf8;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.profiler-config-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
    margin-top: 14px;
}
.profiler-config-item {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 10px 14px;
}
.profiler-config-label {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #94a3b8;
    font-weight: 600;
}
.profiler-config-val {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    color: #f1f5f9;
    font-weight: 700;
    margin-top: 2px;
}

/* ── Streamlit Tabs Overrides ───────────────────────────────────────── */
button[data-baseweb="tab"] {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.92rem !important;
    color: #64748b !important;
    padding: 10px 18px !important;
    border-radius: 8px 8px 0 0 !important;
    transition: all 0.15s ease-in-out !important;
}
button[data-baseweb="tab"]:hover {
    color: #1e293b !important;
    background-color: rgba(241, 245, 249, 0.6) !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #3b82f6 !important;
    border-bottom: 3px solid #3b82f6 !important;
    background-color: #ffffff !important;
    font-weight: 700 !important;
}

/* ── Metric Cards Overrides ─────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 12px 16px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03);
    transition: transform 0.15s ease;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06);
}
[data-testid="stMetricValue"] {
    font-family: 'Outfit', sans-serif !important;
    color: #0f172a !important;
    font-weight: 800 !important;
    font-size: 1.65rem !important;
}
[data-testid="stMetricLabel"] {
    font-family: 'Inter', sans-serif !important;
    color: #64748b !important;
    font-weight: 600 !important;
    font-size: 0.8rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.03em !important;
}

/* ── Button Aesthetics ──────────────────────────────────────────────── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important;
    color: #ffffff !important;
    border: none !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    border-radius: 8px !important;
    padding: 10px 20px !important;
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3) !important;
    transition: all 0.15s ease !important;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 18px rgba(37, 99, 235, 0.4) !important;
}
.stButton > button[kind="secondary"] {
    background: #ffffff !important;
    color: #1e293b !important;
    border: 1px solid #cbd5e1 !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    border-radius: 8px !important;
    padding: 8px 16px !important;
    transition: all 0.15s ease !important;
}
.stButton > button[kind="secondary"]:hover {
    background: #f8fafc !important;
    border-color: #94a3b8 !important;
    transform: translateY(-1px) !important;
}

/* Custom code blocks */
code, pre {
    font-family: 'JetBrains Mono', Consolas, monospace !important;
}

/* Dataframe table rounded container */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border-subtle);
    border-radius: 10px;
    overflow: hidden;
}
</style>
"""
st.markdown(STUDIO_CSS, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Robust Sample Program Selection & State Synchronization
# -----------------------------------------------------------------------------
examples_list = [
    ("01_arithmetic.py", "1. Arithmetic & Precedence"),
    ("02_conditionals.py", "2. Conditionals (if / elif / else)"),
    ("03_loops.py", "3. While Loops & Accumulators"),
    ("04_nested_blocks.py", "4. Nested Blocks & Scopes"),
    ("05_optimization.py", "5. Optimization (Folding & DCE)"),
    ("06_syntax_error.py", "6. Syntax Error Diagnostic Demo"),
    ("07_semantic_error.py", "7. Semantic Error Diagnostic Demo"),
]

# Ensure initial state is populated
if "current_sample_file" not in st.session_state:
    st.session_state["current_sample_file"] = examples_list[0][0]

if "source_editor_input" not in st.session_state:
    st.session_state["source_editor_input"] = load_example(examples_list[0][0])


def on_sample_change():
    """Callback triggered whenever the user changes the Sample Program dropdown.

    Directly synchronizes the editor content in session state before rendering.
    """
    chosen = st.session_state.get("sample_selector")
    if chosen:
        st.session_state["source_editor_input"] = load_example(chosen)
        st.session_state["current_sample_file"] = chosen


# -----------------------------------------------------------------------------
# Sidebar Configuration & Controls
# -----------------------------------------------------------------------------
st.sidebar.markdown("### ⚡ CodeX Studio")
st.sidebar.caption("High-Performance Python ➔ C++17 Academic Compiler")

st.sidebar.markdown("---")
st.sidebar.markdown("#### 📂 Sample Program")

# Find index of current sample to keep selectbox synchronized
current_idx = 0
for idx, (fname, _) in enumerate(examples_list):
    if fname == st.session_state.get("current_sample_file"):
        current_idx = idx
        break

selected_sample_file = st.sidebar.selectbox(
    "Choose Archetype Example:",
    options=[e[0] for e in examples_list],
    index=current_idx,
    format_func=lambda x: dict(examples_list).get(x, x),
    key="sample_selector",
    on_change=on_sample_change,
)

# Safety synchronization guard (in case state was changed externally)
if st.session_state["current_sample_file"] != selected_sample_file:
    st.session_state["source_editor_input"] = load_example(selected_sample_file)
    st.session_state["current_sample_file"] = selected_sample_file

# Sample description info card
sample_desc = EXAMPLE_DESCRIPTIONS.get(selected_sample_file, "")
if sample_desc:
    st.sidebar.info(f"💡 **Archetype Focus:**\n{sample_desc}")

# Reset Button to revert edits to the sample's pristine file
if st.sidebar.button("🔄 Reset Editor to Sample Default", use_container_width=True):
    st.session_state["source_editor_input"] = load_example(selected_sample_file)
    st.rerun()

st.sidebar.markdown("---")

# ── Optimization Level Selector ───────────────────────────────────────────────
st.sidebar.markdown("#### ⚙️ Compiler Optimization")

selected_opt_label = st.sidebar.selectbox(
    "Optimization Level (-O):",
    options=OPT_LEVEL_OPTIONS,
    index=2,  # default: -O2
    key="opt_level_selector",
    help=(
        "-O0: No optimization (raw TAC)\n"
        "-O1: Constant Folding + Branch Simplification\n"
        "-O2: O1 + Unused Temporary Elimination (default)\n"
        "-O3: Aggressive multi-pass fixed-point iteration (up to 10 iterations)"
    ),
)

opt_level: int = OPT_LEVEL_OPTIONS.index(selected_opt_label)
_opt_badge_class = f"opt-badge-O{opt_level}"

st.sidebar.markdown(
    f'<div style="margin-top: 6px; margin-bottom: 10px;">'
    f'<span class="opt-badge {_opt_badge_class}">-O{opt_level} Active</span>'
    f'</div>'
    f'<div style="font-size: 0.82rem; color: #475569; line-height: 1.4;">'
    f'{OPT_LEVEL_DESCRIPTIONS[opt_level]}'
    f'</div>',
    unsafe_allow_html=True,
)

st.sidebar.markdown("---")
st.sidebar.markdown("#### 🏛️ 6-Phase Pipeline")
st.sidebar.markdown(
    """
    1. **Lexical Analysis**: Tokens, Indent/Dedent, Line/Col
    2. **Syntax Analysis**: Recursive Descent, Explicit AST
    3. **Semantic Analysis**: Scoped Symbol Table, Type Invariants
    4. **Original TAC**: Linearized Three-Address Instructions
    5. **Optimized TAC**: Configurable Constant Folding & DCE
    6. **Generated C++**: Idiomatic C++17 with Runtime Helpers
    """
)

st.sidebar.markdown("---")
st.sidebar.caption("CodeX Studio v1.2 • Google DeepMind Enhanced")


# -----------------------------------------------------------------------------
# Main Header Card (Hero)
# -----------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="hero-header">
        <div class="hero-row">
            <div class="hero-title-group">
                <h1 class="hero-title">CodeX</h1>
                <span class="hero-tag">Compiler Studio v1.2</span>
                <span class="opt-badge opt-badge-O{opt_level}">-O{opt_level} Configured</span>
            </div>
            <div>
                <span style="font-size:0.82rem; color:#64748b; font-family:'JetBrains Mono', monospace;">
                    Target: C++17 (ISO/IEC 14882:2017)
                </span>
            </div>
        </div>
        <p class="hero-subtitle">
            An academic-grade, modular source-to-source compiler translating a typed Python subset into standard C++17.
            Explore lexical scanning, AST synthesis, semantic type checking, 3-address code optimization (-O0 to -O3), and live execution profiling.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Source Code Input & Compilation Controls
# -----------------------------------------------------------------------------
col_editor, col_controls = st.columns([7, 3])

with col_editor:
    # macOS window style header bar
    line_count = len(st.session_state.get("source_editor_input", "").splitlines())
    char_count = len(st.session_state.get("source_editor_input", ""))
    sample_name = dict(examples_list).get(selected_sample_file, selected_sample_file)

    st.markdown(
        f"""
        <div class="editor-frame">
            <div class="editor-bar">
                <div class="window-dots">
                    <span class="dot dot-red"></span>
                    <span class="dot dot-yellow"></span>
                    <span class="dot dot-green"></span>
                    <span class="editor-bar-title" style="margin-left: 8px;">🐍 {sample_name}</span>
                </div>
                <div style="display: flex; gap: 8px;">
                    <span class="editor-badge">{line_count} lines</span>
                    <span class="editor-badge">{char_count} chars</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    source_code = st.text_area(
        "Source Code Editor",
        key="source_editor_input",
        height=280,
        label_visibility="collapsed",
        help="Edit Python source code here. Picking a sample from the sidebar automatically loads its content.",
    )

with col_controls:
    st.markdown('<div class="card-header-title">Compiler Engine</div>', unsafe_allow_html=True)
    compile_btn = st.button("🚀 Compile Source", type="primary", use_container_width=True)
    st.caption(f"Executes all 6 pipeline phases with **-O{opt_level}** optimization.")

    # Execute full pipeline compilation
    result: CompilationResult = compile_source(source_code, opt_level=opt_level)

    st.markdown('<div class="card-header-title" style="margin-top: 16px;">Pipeline Status</div>', unsafe_allow_html=True)
    if result.success:
        st.markdown(
            '<div class="status-pill status-pill-success">ALL 6 PHASES PASSED</div>',
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        st.caption(
            f"• Tokens: **{len(result.tokens)}**<br>"
            f"• Original TAC: **{len(result.tac)}** insts<br>"
            f"• Optimized TAC: **{len(result.optimized_tac)}** insts<br>"
            f"• Optimizations: **{len(result.optimization_log)}** transformations",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="status-pill status-pill-error">HALTED AT {result.phase_reached}</div>',
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        st.error(result.error_message or "Compilation error occurred.")

st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Eight Feature Demonstration Tabs
# -----------------------------------------------------------------------------
(
    tab_tokens,
    tab_ast,
    tab_semantic,
    tab_orig_tac,
    tab_opt_tac,
    tab_cpp,
    tab_validation,
    tab_profiler,
) = st.tabs(
    [
        "🔤 Tokens",
        "🌳 AST",
        "🔎 Semantic Analysis",
        "📋 Original TAC",
        "✨ Optimized TAC",
        "⚙️ Generated C++",
        "✅ Validation",
        "⚡ Performance Profiler",
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

        filter_col, _ = st.columns([5, 5])
        with filter_col:
            search_query = st.text_input("🔍 Filter tokens by type or lexeme:", "")

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
            st.markdown("##### AST Node Attributes (Structured JSON)")
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

    _opt_label = OPT_LEVEL_OPTIONS[result.opt_level] if 0 <= result.opt_level <= 3 else f"-O{result.opt_level}"
    st.caption(
        f"Optimization level active: **{_opt_label}** — "
        "Demonstrates explainable constant folding, dead-branch pruning, and dead-code elimination."
    )

    if result.optimized_tac or result.tac:
        orig_count = len(result.tac)
        opt_count = len(result.optimized_tac)
        reduction = orig_count - opt_count
        reduction_pct = (reduction / orig_count * 100) if orig_count > 0 else 0

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Original Instructions", orig_count)
        m2.metric("Optimized Instructions", opt_count)
        m3.metric("Instructions Reduced", reduction)
        m4.metric("Reduction %", f"{reduction_pct:.1f}%")
        m5.metric("Active Opt Level", f"-O{result.opt_level}")

        col_orig, col_opt = st.columns(2)
        with col_orig:
            st.markdown("##### Original TAC Instruction Stream")
            st.code(result.tac_str, language="text")

        with col_opt:
            st.markdown("##### Optimized TAC Instruction Stream")
            st.code(result.optimized_tac_str or result.tac_str, language="text")

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
            if result.opt_level == 0:
                st.info("-O0 is active: all optimization passes are disabled. No transformations applied.")
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
                    f'<div class="status-pill status-pill-success">PASS — EXACT OUTPUT PARITY CONFIRMED</div> '
                    f'<span style="font-size:0.85rem; color:#64748b; margin-left:8px;">Compile: {val_res.compile_time:.3f}s | Run: {val_res.run_time:.3f}s</span>',
                    unsafe_allow_html=True,
                )
            elif val_res.status == "FAIL":
                st.markdown(
                    '<div class="status-pill status-pill-error">FAIL — OUTPUT MISMATCH DETECTED</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="status-pill status-pill-error">{val_res.status}</div>',
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


# -----------------------------------------------------------------------------
# 8. PERFORMANCE PROFILER TAB
# -----------------------------------------------------------------------------
with tab_profiler:
    st.markdown("### ⚡ Performance Profiler & Execution Benchmark")
    st.caption(
        "Compiles the generated C++17 binary with `g++ -std=c++17 -O2`, executes it **3 warm runs**, and reports the "
        "**median wall-clock execution time** measured with nanosecond resolution (`time.perf_counter_ns()`)."
    )

    if not result.success or not result.cpp_code:
        st.warning(
            "⚠️ The compiler pipeline must complete successfully before profiling. "
            "Please resolve any compilation errors in the editor first."
        )
    else:
        # ── Profiler Telemetry Card ───────────────────────────────────────────
        st.markdown(
            f"""
            <div class="profiler-telemetry-card">
                <div class="profiler-title">
                    <span>⚡ Benchmark Telemetry Configuration</span>
                </div>
                <div class="profiler-config-grid">
                    <div class="profiler-config-item">
                        <div class="profiler-config-label">Compiler Target</div>
                        <div class="profiler-config-val">g++ -std=c++17 -O2</div>
                    </div>
                    <div class="profiler-config-item">
                        <div class="profiler-config-label">CodeX Opt Level</div>
                        <div class="profiler-config-val">-O{result.opt_level} ({selected_opt_label.split()[1]})</div>
                    </div>
                    <div class="profiler-config-item">
                        <div class="profiler-config-label">Sampling Strategy</div>
                        <div class="profiler-config-val">3 Runs → Median Filter</div>
                    </div>
                    <div class="profiler-config-item">
                        <div class="profiler-config-label">Timing Precision</div>
                        <div class="profiler-config-val">perf_counter_ns() [ns]</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Benchmark Trigger Button ──────────────────────────────────────────
        run_profiler_btn = st.button(
            "🏁 Run Benchmark & Profile",
            type="primary",
            use_container_width=False,
            key="profiler_run_btn",
        )

        if run_profiler_btn:
            with st.spinner(
                "Compiling with g++ -O2 and benchmarking 3 execution runs... please wait."
            ):
                profile = profile_cpp_code(result.cpp_code)

            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

            if not profile["success"]:
                # Error State
                st.markdown(
                    '<div class="status-pill status-pill-error">PROFILING FAILED</div>',
                    unsafe_allow_html=True,
                )
                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
                st.error(profile.get("error", "Unknown profiling error."))

                if profile.get("compile_time_ms", 0) > 0:
                    st.metric("g++ Compile Time", f"{profile['compile_time_ms']:.1f} ms")
            else:
                # Success State — High-Resolution Metrics Dashboard
                st.markdown(
                    '<div class="status-pill status-pill-success">PROFILING COMPLETE — HARDWARE BENCHMARKED</div>',
                    unsafe_allow_html=True,
                )
                st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

                col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)

                exec_ms = profile["execution_time_ms"]
                compile_ms = profile["compile_time_ms"]
                line_count = profile["instruction_count"]
                opt_lbl = f"-O{result.opt_level}"
                tac_reduction = (
                    len(result.tac) - len(result.optimized_tac)
                    if result.tac else 0
                )

                col_m1.metric(
                    label="⏱ Median Exec Time",
                    value=f"{exec_ms:.4f} ms",
                    help="Median wall-clock execution time across 3 warm executions measured with perf_counter_ns().",
                )
                col_m2.metric(
                    label="🔧 g++ Compile Time",
                    value=f"{compile_ms:.1f} ms",
                    help="Duration for g++ -std=c++17 -O2 to compile the generated target source file.",
                )
                col_m3.metric(
                    label="📄 C++ Source Lines",
                    value=line_count,
                    help="Non-blank, non-comment lines of generated C++ code.",
                )
                col_m4.metric(
                    label="⚙️ Optimization Flag",
                    value=opt_lbl,
                    help=OPT_LEVEL_DESCRIPTIONS.get(result.opt_level, ""),
                )
                col_m5.metric(
                    label="📉 TAC Insts Eliminated",
                    value=tac_reduction,
                    help=f"Instructions removed by -O{result.opt_level} optimizer pass.",
                )

                # Throughput calculation
                if exec_ms > 0:
                    runs_per_sec = 1_000.0 / exec_ms
                    st.caption(
                        f"🚀 **Peak Throughput Estimate:** `{runs_per_sec:,.0f}` iterations/second "
                        f"| Compilation completed in `{compile_ms:.1f} ms`"
                    )

                # Clean Program Output Display
                st.markdown("---")
                st.markdown("##### 📤 Compiled Executable Standard Output (`stdout`)")
                stdout_text = profile.get("stdout", "")
                if stdout_text:
                    st.code(stdout_text, language="text")
                else:
                    st.info("The compiled program executed cleanly but generated no standard output.")

                # Comparative Optimization Impact Table
                st.markdown("---")
                st.markdown("##### 📊 End-to-End Optimization Impact Matrix")

                orig_n = len(result.tac)
                opt_n = len(result.optimized_tac)
                pct = ((orig_n - opt_n) / orig_n * 100) if orig_n > 0 else 0.0

                impact_col1, impact_col2 = st.columns(2)
                with impact_col1:
                    st.markdown(
                        f"""
                        | Frontend Metric | Measurement |
                        |---|---|
                        | CodeX Optimization Level | **-O{result.opt_level}** |
                        | Raw Linearized TAC Instructions | **{orig_n}** |
                        | Optimized TAC Instructions | **{opt_n}** |
                        | Code Reduction Efficiency | **{orig_n - opt_n}** ({pct:.1f}%) |
                        | Discrete Passes Recorded | **{len(result.optimization_log)}** |
                        """
                    )
                with impact_col2:
                    st.markdown(
                        f"""
                        | Target Backend Metric | Measurement |
                        |---|---|
                        | Native GCC C++ Compiler | **g++ 15.2 (C++17)** |
                        | Backend Optimization Flag | **-O2** |
                        | Target Binary Compilation Time | **{compile_ms:.1f} ms** |
                        | Median Binary Execution Time | **{exec_ms:.4f} ms** |
                        | Executable Timing Resolution | **Nanosecond** |
                        """
                    )

                if result.optimization_log:
                    st.markdown("##### 🔍 Recorded Optimization Transformations")
                    log_rows = [
                        {
                            "Rule": getattr(rec, "rule", rec.pass_name),
                            "Pass Category": rec.pass_name,
                            "Original TAC": rec.original or "-",
                            "Optimized TAC": rec.replacement or "-",
                            "Explanation": getattr(rec, "explanation", rec.description),
                        }
                        for rec in result.optimization_log
                    ]
                    st.dataframe(pd.DataFrame(log_rows), use_container_width=True, height=200)
