# CodeX — Source-to-Source Compiler (Python Subset to C++17)

**CodeX** is an academic-grade, modular source-to-source compiler that translates a documented subset of Python-like syntax into equivalent, idiomatic C++17. It demonstrates all six classic compiler phases in clean, well-tested Python modules accompanied by an interactive Streamlit compiler workbench.

---

## 🏛️ Compiler Architecture

```
                       Source Code (Python-like subset)
                                     │
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │ Phase 1: Lexical Analyzer (compiler/lexer.py)                          │
 │  - Tokenizes keywords, literals, operators, delimiters                │
 │  - Tracks source locations (1-indexed line and column)                │
 │  - Manages indentation stack emitting synthetic INDENT / DEDENT tokens │
 └───────────────────────────────────┬────────────────────────────────────┘
                                     │ Tokens
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │ Phase 2: Syntax Analyzer & AST (compiler/parser.py, ast_nodes.py)       │
 │  - Custom Recursive Descent Parser without third-party AST libraries   │
 │  - Enforces operator precedence and left/right associativity           │
 │  - Constructs an explicit typed AST with line/col diagnostics          │
 └───────────────────────────────────┬────────────────────────────────────┘
                                     │ AST
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │ Phase 3: Semantic Analyzer (compiler/semantic.py, symbol_table.py)     │
 │  - Multi-level scoped symbol table with variable declarations          │
 │  - Type inference and strict static type checking                      │
 │  - Undeclared identifier detection and incompatible type rejection     │
 └───────────────────────────────────┬────────────────────────────────────┘
                                     │ Validated AST + Symbol Table
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │ Phase 4: Intermediate Code Generation (compiler/tac.py)                │
 │  - Generates linear Three-Address Code (TAC) instructions              │
 │  - Deterministic temporaries (`t0, t1, ...`) and labels (`L0, L1, ...`)│
 │  - Conditionals, loops, and control flow linearization                 │
 └───────────────────────────────────┬────────────────────────────────────┘
                                     │ Original TAC
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │ Phase 5: TAC Optimizer (compiler/optimizer.py)                         │
 │  - Constant folding for arithmetic, comparison, and boolean logic      │
 │  - Branch simplification on constant conditions                        │
 │  - Conservative dead-code elimination (unreachable code & dead temps)  │
 │  - Generates an auditable transformation explanation log               │
 └───────────────────────────────────┬────────────────────────────────────┘
                                     │ Optimized TAC
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │ Phase 6: C++17 Code Generator (compiler/codegen_cpp.py)                 │
 │  - Generates readable, standard-compliant C++17                        │
 │  - Standard runtime helpers for Python-like floor div, modulo, print   │
 │  - Compiles natively with `g++ -std=c++17`                             │
 └────────────────────────────────────────────────────────────────────────┘
```

---

## 📜 Formal Language Grammar (EBNF)

```ebnf
program        ::= ( NEWLINE | statement )* EOF ;

statement      ::= simple_stmt | compound_stmt ;
simple_stmt    ::= ( assign_stmt | print_stmt | pass_stmt ) NEWLINE ;
compound_stmt  ::= if_stmt | while_stmt ;

assign_stmt    ::= IDENTIFIER '=' expr ;
print_stmt     ::= 'print' '(' [ expr ( ',' expr )* ] ')' ;
pass_stmt      ::= 'pass' ;

block          ::= NEWLINE INDENT statement+ DEDENT ;

if_stmt        ::= 'if' expr ':' block
                   ( 'elif' expr ':' block )*
                   [ 'else' ':' block ] ;

while_stmt     ::= 'while' expr ':' block ;

expr           ::= or_test ;
or_test        ::= and_test ( 'or' and_test )* ;
and_test       ::= not_test ( 'and' not_test )* ;
not_test       ::= 'not' not_test | comparison ;
comparison     ::= term ( ( '==' | '!=' | '<' | '<=' | '>' | '>=' ) term )* ;
term           ::= factor ( ( '+' | '-' ) factor )* ;
factor         ::= unary ( ( '*' | '/' | '//' | '%' ) unary )* ;
unary          ::= ( '+' | '-' ) unary | primary ;
primary        ::= INT_LITERAL
                 | FLOAT_LITERAL
                 | STRING_LITERAL
                 | BOOL_LITERAL
                 | IDENTIFIER
                 | '(' expr ')' ;
```

---

## 🔍 Language Scope & Semantics

### Supported Types
- **`int`**: 64-bit signed integer (`int64_t` in C++).
- **`float`**: Double precision floating point (`double` in C++).
- **`bool`**: Boolean value (`bool` in C++, literals `True`, `False`).
- **`string`**: Text strings (`std::string` in C++, supporting quotes and escape sequences).

### Type Inference & Promotion Rules
1. Variables are declared implicitly on first assignment with their inferred type.
2. Reassignment to a previously declared variable requires identical type, with one safe numeric exception: an integer expression can be assigned to a variable previously typed as `float`.
3. Arithmetic operators (`+`, `-`, `*`) between two `int`s produce `int`. Any combination with `float` promotes to `float`.
4. String concatenation (`+`) is supported exclusively between two strings.
5. True division (`/`) between numeric types always yields `float` (conforming to Python 3 semantics).
6. Integer floor division (`//`) and modulo (`%`) require integer operands and yield integer results.
7. Conditions for `if`, `elif`, and `while` must evaluate to `bool`. Non-boolean conditions are rejected at the semantic phase.

---

## ⚙️ Optimization Passes

The TAC Optimizer implements sound, conservative transformations:
1. **Constant Folding**:
   - Statically computes arithmetic (`+`, `-`, `*`, `/`, `//`, `%`), comparisons (`<`, `<=`, `>`, `>=`, `==`, `!=`), and logical operations (`and`, `or`, `not`) on literal constants.
2. **Branch Simplification**:
   - `if_false True goto L`: Eliminated entirely as dead code.
   - `if_false False goto L`: Converted into an unconditional `goto L`.
3. **Dead Code Elimination (DCE)**:
   - Instructions positioned between an unconditional `goto` and the next `LABEL:` are eliminated as unreachable.
   - Pure temporary assignments (`tX = ...`) whose values are never referenced in downstream instructions are pruned iteratively.

Every transformation is recorded with its pass name, before/after instruction text, and rationale in `CompilationResult.optimization_log`.

---

## 🚫 Documented Limitations & Unsupported Features

CodeX intentionally implements a well-defined, statically verifiable subset of Python. The following features are outside the language specification:
- User-defined functions (`def`) and classes (`class`).
- Dynamic duck typing or runtime type mutations.
- Collections (lists, dictionaries, sets, tuples).
- `for ... in ...` loops and iterators.
- Exception handling (`try / except / finally`).
- Bitwise operators (`&`, `|`, `^`, `<<`, `>>`).
- Imports and standard library modules outside `print()`.

---

## 📂 Project Directory Structure

```
compiler project/
├── app.py                      # Interactive Streamlit compiler workbench
├── requirements.txt            # Minimal dependencies (streamlit, pandas, pytest)
├── README.md                   # Complete architectural and grammatical documentation
├── compiler/
│   ├── __init__.py             # Exposes compile_source and CompilationResult
│   ├── lexer.py                # Lexer with INDENT/DEDENT and location tracking
│   ├── ast_nodes.py            # Explicit AST dataclasses & ASCII tree formatter
│   ├── parser.py               # Custom Recursive Descent Parser
│   ├── symbol_table.py         # Scoped Symbol Table & Symbol dataclass
│   ├── semantic.py             # Semantic analyzer & static type checker
│   ├── tac.py                  # Three-Address Code intermediate representation
│   ├── optimizer.py            # Explainable Constant Folder & Dead-Code Eliminator
│   ├── codegen_cpp.py          # Valid C++17 target code generator
│   ├── validator.py            # Behavioral Equivalence Engine & Representative Test Suite
│   └── pipeline.py             # Single compile_source entry point with diagnostics
├── tests/
│   ├── __init__.py
│   ├── test_lexer.py           # Tokens, literals, indentation, invalid chars
│   ├── test_parser.py          # AST building, precedence, syntax errors
│   ├── test_semantic.py        # Symbol table, type check, semantic errors
│   ├── test_tac.py             # Linearization, labels, and jumps
│   ├── test_optimizer.py       # Constant folding, branch simplification, DCE
│   ├── test_codegen.py         # C++ generation, g++ compilation & run
│   ├── test_pipeline.py        # Staged pipeline and error stopping
│   ├── test_advanced_cases.py  # Modulo, nested loops, unary negations
│   └── test_validation.py      # Behavioral equivalence, diffing, and explainability
└── examples/
    ├── 01_arithmetic.py        # Arithmetic, precedence, float & floor div
    ├── 02_conditionals.py      # if-elif-else branching
    ├── 03_loops.py             # while loop & factorial
    ├── 04_nested_blocks.py     # nested while and if blocks
    ├── 05_optimization.py      # constant folding benchmark
    ├── 06_syntax_error.py      # missing colon syntax error demo
    └── 07_semantic_error.py    # incompatible type reassignment demo
```

---

## 🚀 Installation & Launch Instructions

### Prerequisites
- Python 3.10+
- `g++` with C++17 support (e.g. MSYS2 / MinGW-w64 on Windows, or GCC on Linux/macOS)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch Streamlit Workbench UI
```bash
streamlit run app.py
# Or if streamlit is not in your system PATH:
python -m streamlit run app.py
```
Open `http://localhost:8501` in your browser.

In the workbench:
- **Sample Program Selector**: Instantly loads 7 archetype examples (arithmetic, conditionals, while loops, nested scopes, optimization, and syntax/semantic error demos).
- **Optimization Selector**: Use the sidebar to switch between `-O0 (None)`, `-O1 (Basic)`, `-O2 (Standard)`, and `-O3 (Aggressive)`.
- **⚡ Performance Profiler**: Switch to the Profiler tab and click **Run Benchmark & Profile** to compile with `g++ -std=c++17 -O2`, capture high-resolution execution metrics, and inspect standard output.

### 3. Run the Complete Test Suite
```bash
pytest -v
# Or:
py -m pytest tests/ -v
```

---

## 🧪 Verified Test Results

All **51 unit, integration, validation, optimizer-level, and profiler tests** pass with 100% success:

```
tests/test_advanced_cases.py::test_division_and_modulo PASSED            [  1%]
tests/test_advanced_cases.py::test_nested_loops_and_conditionals PASSED  [  3%]
tests/test_advanced_cases.py::test_unary_negative_and_not PASSED         [  5%]
tests/test_advanced_cases.py::test_complex_constant_folding PASSED       [  7%]
tests/test_codegen.py::test_codegen_syntax_structure PASSED              [  9%]
tests/test_codegen.py::test_codegen_e2e_arithmetic PASSED                [ 11%]
tests/test_codegen.py::test_codegen_e2e_conditionals PASSED              [ 13%]
tests/test_codegen.py::test_codegen_e2e_while_loop PASSED                [ 15%]
tests/test_lexer.py::test_lexer_literals PASSED                          [ 17%]
tests/test_lexer.py::test_lexer_operators_and_keywords PASSED            [ 19%]
tests/test_lexer.py::test_lexer_indentation PASSED                       [ 21%]
tests/test_lexer.py::test_lexer_comments_and_blanks PASSED               [ 23%]
tests/test_lexer.py::test_lexer_invalid_character PASSED                 [ 25%]
tests/test_lexer.py::test_lexer_unclosed_string PASSED                   [ 27%]
tests/test_lexer.py::test_lexer_bad_indentation PASSED                   [ 29%]
tests/test_optimizer.py::test_optimizer_constant_folding_arithmetic PASSED [ 31%]
tests/test_optimizer.py::test_optimizer_branch_simplification PASSED     [ 33%]
tests/test_optimizer.py::test_optimizer_dead_code_elimination_unused_temps PASSED [ 35%]
tests/test_optimizer.py::test_optimizer_levels_o0_to_o3 PASSED           [ 37%]
tests/test_optimizer.py::test_pipeline_configurable_opt_levels PASSED    [ 39%]
tests/test_parser.py::test_parser_arithmetic_precedence PASSED           [ 41%]
tests/test_parser.py::test_parser_logical_precedence PASSED              [ 43%]
tests/test_parser.py::test_parser_parentheses_override PASSED            [ 45%]
tests/test_parser.py::test_parser_if_elif_else PASSED                    [ 47%]
tests/test_parser.py::test_parser_while_loop PASSED                      [ 49%]
tests/test_parser.py::test_parser_syntax_error_missing_colon PASSED      [ 50%]
tests/test_parser.py::test_parser_syntax_error_unclosed_paren PASSED     [ 52%]
tests/test_pipeline.py::test_pipeline_success PASSED                     [ 54%]
tests/test_pipeline.py::test_pipeline_stop_at_lexer PASSED               [ 56%]
tests/test_pipeline.py::test_pipeline_stop_at_parser PASSED              [ 58%]
tests/test_pipeline.py::test_pipeline_stop_at_semantic PASSED            [ 60%]
tests/test_pipeline.py::test_pipeline_all_examples PASSED                [ 62%]
tests/test_semantic.py::test_semantic_valid_variable_declaration PASSED  [ 64%]
tests/test_semantic.py::test_semantic_undeclared_variable PASSED         [ 66%]
tests/test_semantic.py::test_semantic_type_mismatch_assignment PASSED    [ 68%]
tests/test_semantic.py::test_semantic_invalid_binary_operands PASSED     [ 70%]
tests/test_semantic.py::test_semantic_condition_must_be_bool PASSED      [ 72%]
tests/test_semantic.py::test_semantic_string_concatenation PASSED        [ 74%]
tests/test_semantic.py::test_semantic_float_promotion PASSED             [ 76%]
tests/test_tac.py::test_tac_arithmetic_linearization PASSED              [ 78%]
tests/test_tac.py::test_tac_if_else_control_flow PASSED                  [ 80%]
tests/test_tac.py::test_tac_while_loop_control_flow PASSED               [ 82%]
tests/test_validation.py::test_validation_representative_suite PASSED    [ 84%]
tests/test_validation.py::test_validation_arithmetic_equivalence PASSED  [ 86%]
tests/test_validation.py::test_validation_conditional_equivalence PASSED [ 88%]
tests/test_validation.py::test_validation_while_loop_equivalence PASSED  [ 90%]
tests/test_validation.py::test_validation_compilation_error_reporting PASSED [ 92%]
tests/test_validation.py::test_validation_diff_generator PASSED          [ 94%]
tests/test_explainable_optimization_records PASSED                       [ 96%]
tests/test_validation.py::test_profiler_empty_code PASSED                [ 98%]
tests/test_validation.py::test_profiler_success PASSED                   [100%]

============================= 51 passed in 9.75s ==============================
```

