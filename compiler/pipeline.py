"""Compiler Pipeline for CodeX.

Integrates all six phases of compilation into a single unified entry point:
`compile_source(source: str) -> CompilationResult`.
Enforces graceful error stopping, structured diagnostics, and deterministic intermediate representations.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from .lexer import Token, Lexer, LexerError
from .ast_nodes import Program, format_ast_tree
from .parser import Parser, ParserError
from .symbol_table import SymbolTable, Symbol
from .semantic import SemanticAnalyzer, SemanticError
from .tac import TacInstruction, TacGenerator, format_tac_instructions
from .optimizer import TacOptimizer, OptimizationRecord, optimize_tac
from .codegen_cpp import generate_cpp


@dataclass
class Diagnostic:
    phase: str
    message: str
    line: int
    column: int
    severity: str = "ERROR"

    def __repr__(self) -> str:
        return f"[{self.severity}] {self.phase} (Line {self.line}, Col {self.column}): {self.message}"


@dataclass
class CompilationResult:
    success: bool
    phase_reached: str
    opt_level: int = 2
    tokens: List[Token] = field(default_factory=list)
    ast: Optional[Program] = None
    ast_tree_str: str = ""
    symbol_table: Optional[SymbolTable] = None
    symbols: List[Dict[str, Any]] = field(default_factory=list)
    diagnostics: List[Diagnostic] = field(default_factory=list)
    tac: List[TacInstruction] = field(default_factory=list)
    tac_str: str = ""
    optimized_tac: List[TacInstruction] = field(default_factory=list)
    optimized_tac_str: str = ""
    optimization_log: List[OptimizationRecord] = field(default_factory=list)
    cpp_code: str = ""
    error_message: Optional[str] = None


def compile_source(source: str, opt_level: int = 2) -> CompilationResult:
    """Executes the full CodeX compiler pipeline on the input source string.

    Args:
        source: The source code string to compile.
        opt_level: Optimization level 0–3 (-O0 through -O3). Default is 2 (-O2).
    """
    diagnostics: List[Diagnostic] = []

    # Phase 1: Lexical Analysis
    try:
        lexer = Lexer(source)
        tokens = lexer.tokenize()
    except LexerError as e:
        diag = Diagnostic(phase="Lexer", message=e.message, line=e.line, column=e.column)
        return CompilationResult(
            success=False,
            phase_reached="LEXICAL",
            diagnostics=[diag],
            error_message=str(e),
        )
    except Exception as e:
        diag = Diagnostic(phase="Lexer", message=str(e), line=1, column=1)
        return CompilationResult(
            success=False,
            phase_reached="LEXICAL",
            diagnostics=[diag],
            error_message=f"Lexer encountered unexpected error: {e}",
        )

    # Phase 2: Syntax Analysis (Parser)
    try:
        parser = Parser(tokens)
        ast = parser.parse()
        ast_tree_str = format_ast_tree(ast)
    except ParserError as e:
        diag = Diagnostic(phase="Parser", message=e.message, line=e.line, column=e.column)
        return CompilationResult(
            success=False,
            phase_reached="PARSER",
            tokens=tokens,
            diagnostics=[diag],
            error_message=str(e),
        )
    except Exception as e:
        diag = Diagnostic(phase="Parser", message=str(e), line=1, column=1)
        return CompilationResult(
            success=False,
            phase_reached="PARSER",
            tokens=tokens,
            diagnostics=[diag],
            error_message=f"Parser encountered unexpected error: {e}",
        )

    # Phase 3: Semantic Analysis
    try:
        analyzer = SemanticAnalyzer()
        symbol_table = analyzer.analyze(ast)
        symbols = [sym.to_dict() for sym in symbol_table.get_all_symbols()]
    except SemanticError as e:
        diag = Diagnostic(phase="Semantic", message=e.message, line=e.line, column=e.column)
        return CompilationResult(
            success=False,
            phase_reached="SEMANTIC",
            tokens=tokens,
            ast=ast,
            ast_tree_str=ast_tree_str,
            diagnostics=[diag],
            error_message=str(e),
        )
    except Exception as e:
        diag = Diagnostic(phase="Semantic", message=str(e), line=1, column=1)
        return CompilationResult(
            success=False,
            phase_reached="SEMANTIC",
            tokens=tokens,
            ast=ast,
            ast_tree_str=ast_tree_str,
            diagnostics=[diag],
            error_message=f"Semantic analysis encountered unexpected error: {e}",
        )

    # Phase 4: Three-Address Code (TAC) Generation
    try:
        tac_gen = TacGenerator()
        tac = tac_gen.generate(ast)
        tac_str = format_tac_instructions(tac)
    except Exception as e:
        diag = Diagnostic(phase="TAC Generation", message=str(e), line=1, column=1)
        return CompilationResult(
            success=False,
            phase_reached="TAC",
            tokens=tokens,
            ast=ast,
            ast_tree_str=ast_tree_str,
            symbol_table=symbol_table,
            symbols=symbols,
            diagnostics=[diag],
            error_message=f"TAC generation failed: {e}",
        )

    # Phase 5: TAC Optimization
    try:
        optimizer = TacOptimizer(level=opt_level)
        optimized_tac, opt_log = optimizer.optimize(tac)
        opt_tac_str = format_tac_instructions(optimized_tac)
    except Exception as e:
        diag = Diagnostic(phase="Optimizer", message=str(e), line=1, column=1)
        return CompilationResult(
            success=False,
            phase_reached="OPTIMIZER",
            tokens=tokens,
            ast=ast,
            ast_tree_str=ast_tree_str,
            symbol_table=symbol_table,
            symbols=symbols,
            tac=tac,
            tac_str=tac_str,
            diagnostics=[diag],
            error_message=f"Optimization failed: {e}",
        )

    # Phase 6: C++17 Target Code Generation
    try:
        cpp_code = generate_cpp(ast, symbol_table)
    except Exception as e:
        diag = Diagnostic(phase="Codegen", message=str(e), line=1, column=1)
        return CompilationResult(
            success=False,
            phase_reached="CODEGEN",
            tokens=tokens,
            ast=ast,
            ast_tree_str=ast_tree_str,
            symbol_table=symbol_table,
            symbols=symbols,
            tac=tac,
            tac_str=tac_str,
            optimized_tac=optimized_tac,
            optimized_tac_str=opt_tac_str,
            optimization_log=opt_log,
            diagnostics=[diag],
            error_message=f"C++ code generation failed: {e}",
        )

    return CompilationResult(
        success=True,
        phase_reached="COMPLETED",
        opt_level=opt_level,
        tokens=tokens,
        ast=ast,
        ast_tree_str=ast_tree_str,
        symbol_table=symbol_table,
        symbols=symbols,
        diagnostics=diagnostics,
        tac=tac,
        tac_str=tac_str,
        optimized_tac=optimized_tac,
        optimized_tac_str=opt_tac_str,
        optimization_log=opt_log,
        cpp_code=cpp_code,
    )
