"""CodeX Compiler Package

A modular source-to-source compiler from a Python-like language to C++17.
Phases:
1. Lexical Analysis (lexer.py)
2. Syntax Analysis & AST (parser.py, ast_nodes.py)
3. Semantic Analysis (semantic.py, symbol_table.py)
4. Three-Address Code Generation (tac.py)
5. TAC Optimization (optimizer.py)
6. C++17 Target Code Generation (codegen_cpp.py)
"""

from .pipeline import compile_source, CompilationResult
from .optimizer import TacOptimizer, optimize_tac
from .validator import profile_cpp_code

__all__ = ["compile_source", "CompilationResult", "TacOptimizer", "optimize_tac", "profile_cpp_code"]
