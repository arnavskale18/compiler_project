import pytest
from compiler.lexer import tokenize, TokenType, LexerError


def test_lexer_literals():
    src = '42 3.14 "hello world" True False'
    tokens = tokenize(src)
    assert tokens[0].type == TokenType.INT_LITERAL
    assert tokens[0].value == 42
    assert tokens[1].type == TokenType.FLOAT_LITERAL
    assert tokens[1].value == 3.14
    assert tokens[2].type == TokenType.STRING_LITERAL
    assert tokens[2].value == "hello world"
    assert tokens[3].type == TokenType.BOOL_LITERAL
    assert tokens[3].value is True
    assert tokens[4].type == TokenType.BOOL_LITERAL
    assert tokens[4].value is False


def test_lexer_operators_and_keywords():
    src = "if elif else while print and or not pass == != <= >= < > + - * / // % ="
    tokens = tokenize(src)
    types = [t.type for t in tokens if t.type not in (TokenType.NEWLINE, TokenType.EOF)]
    expected = [
        TokenType.IF,
        TokenType.ELIF,
        TokenType.ELSE,
        TokenType.WHILE,
        TokenType.PRINT,
        TokenType.AND,
        TokenType.OR,
        TokenType.NOT,
        TokenType.PASS,
        TokenType.EQ,
        TokenType.NEQ,
        TokenType.LTE,
        TokenType.GTE,
        TokenType.LT,
        TokenType.GT,
        TokenType.PLUS,
        TokenType.MINUS,
        TokenType.STAR,
        TokenType.SLASH,
        TokenType.DOUBLE_SLASH,
        TokenType.PERCENT,
        TokenType.ASSIGN,
    ]
    assert types == expected


def test_lexer_indentation():
    src = (
        "if True:\n"
        "    x = 1\n"
        "    if x > 0:\n"
        "        y = 2\n"
        "    z = 3\n"
    )
    tokens = tokenize(src)
    type_names = [t.type.value for t in tokens]
    assert "INDENT" in type_names
    assert "DEDENT" in type_names
    assert tokens[-1].type == TokenType.EOF


def test_lexer_comments_and_blanks():
    src = (
        "# Top comment\n"
        "\n"
        "x = 10  # Inline comment\n"
        "\n"
        "# Bottom comment\n"
    )
    tokens = tokenize(src)
    meaningful = [t for t in tokens if t.type not in (TokenType.NEWLINE, TokenType.EOF)]
    assert len(meaningful) == 3
    assert meaningful[0].value == "x"
    assert meaningful[1].value == "="
    assert meaningful[2].value == 10


def test_lexer_invalid_character():
    src = "x = 10 @ 5"
    with pytest.raises(LexerError) as exc_info:
        tokenize(src)
    assert "Unexpected character" in exc_info.value.message
    assert exc_info.value.line == 1


def test_lexer_unclosed_string():
    src = 'x = "unclosed string\n'
    with pytest.raises(LexerError) as exc_info:
        tokenize(src)
    assert "Unclosed string literal" in exc_info.value.message


def test_lexer_bad_indentation():
    src = (
        "if True:\n"
        "    x = 1\n"
        "  y = 2\n"
    )
    with pytest.raises(LexerError) as exc_info:
        tokenize(src)
    assert "Unindent does not match" in exc_info.value.message
