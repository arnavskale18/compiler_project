import pytest
from compiler.parser import parse_source
from compiler.semantic import SemanticAnalyzer, SemanticError


def test_semantic_valid_variable_declaration():
    src = (
        "x = 10\n"
        "y = 3.14\n"
        "s = \"hello\"\n"
        "b = True\n"
        "z = x + 5\n"
    )
    ast = parse_source(src)
    analyzer = SemanticAnalyzer()
    sym_tab = analyzer.analyze(ast)

    assert sym_tab.lookup("x").type_name == "int"
    assert sym_tab.lookup("y").type_name == "float"
    assert sym_tab.lookup("s").type_name == "string"
    assert sym_tab.lookup("b").type_name == "bool"
    assert sym_tab.lookup("z").type_name == "int"


def test_semantic_undeclared_variable():
    src = "x = y + 1\n"
    ast = parse_source(src)
    analyzer = SemanticAnalyzer()
    with pytest.raises(SemanticError) as exc_info:
        analyzer.analyze(ast)
    assert "Undeclared variable 'y'" in exc_info.value.message


def test_semantic_type_mismatch_assignment():
    src = (
        "x = 10\n"
        "x = \"cannot assign string to int\"\n"
    )
    ast = parse_source(src)
    analyzer = SemanticAnalyzer()
    with pytest.raises(SemanticError) as exc_info:
        analyzer.analyze(ast)
    assert "Cannot assign expression of type 'string' to variable 'x'" in exc_info.value.message


def test_semantic_invalid_binary_operands():
    src = (
        "a = 10\n"
        "b = \"text\"\n"
        "c = a + b\n"
    )
    ast = parse_source(src)
    analyzer = SemanticAnalyzer()
    with pytest.raises(SemanticError) as exc_info:
        analyzer.analyze(ast)
    assert "Invalid operand types" in exc_info.value.message


def test_semantic_condition_must_be_bool():
    src = (
        "if 10 + 20:\n"
        "    x = 1\n"
    )
    ast = parse_source(src)
    analyzer = SemanticAnalyzer()
    with pytest.raises(SemanticError) as exc_info:
        analyzer.analyze(ast)
    assert "Condition in 'if' statement must be of type 'bool'" in exc_info.value.message


def test_semantic_string_concatenation():
    src = (
        "greeting = \"Hello, \" + \"world!\"\n"
    )
    ast = parse_source(src)
    analyzer = SemanticAnalyzer()
    sym_tab = analyzer.analyze(ast)
    assert sym_tab.lookup("greeting").type_name == "string"


def test_semantic_float_promotion():
    src = (
        "x = 10 + 2.5\n"
    )
    ast = parse_source(src)
    analyzer = SemanticAnalyzer()
    sym_tab = analyzer.analyze(ast)
    assert sym_tab.lookup("x").type_name == "float"
