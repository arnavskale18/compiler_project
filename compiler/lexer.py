"""Lexical Analyzer (Scanner) for CodeX.

Handles token recognition, source location tracking (line, column),
Python-style indentation (INDENT/DEDENT), comments, and lexical error reporting.
"""

from dataclasses import dataclass
from typing import List, Optional, Any
import enum


class TokenType(str, enum.Enum):
    # Literals
    INT_LITERAL = "INT_LITERAL"
    FLOAT_LITERAL = "FLOAT_LITERAL"
    STRING_LITERAL = "STRING_LITERAL"
    BOOL_LITERAL = "BOOL_LITERAL"

    # Identifier
    IDENTIFIER = "IDENTIFIER"

    # Keywords
    IF = "if"
    ELIF = "elif"
    ELSE = "else"
    WHILE = "while"
    PRINT = "print"
    AND = "and"
    OR = "or"
    NOT = "not"
    PASS = "pass"

    # Operators
    PLUS = "+"
    MINUS = "-"
    STAR = "*"
    SLASH = "/"
    DOUBLE_SLASH = "//"
    PERCENT = "%"

    EQ = "=="
    NEQ = "!="
    LTE = "<="
    GTE = ">="
    LT = "<"
    GT = ">"
    ASSIGN = "="

    # Punctuation
    LPAREN = "("
    RPAREN = ")"
    COLON = ":"
    COMMA = ","

    # Layout
    NEWLINE = "NEWLINE"
    INDENT = "INDENT"
    DEDENT = "DEDENT"
    EOF = "EOF"


KEYWORDS = {
    "if": TokenType.IF,
    "elif": TokenType.ELIF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "print": TokenType.PRINT,
    "and": TokenType.AND,
    "or": TokenType.OR,
    "not": TokenType.NOT,
    "pass": TokenType.PASS,
    "True": TokenType.BOOL_LITERAL,
    "False": TokenType.BOOL_LITERAL,
}


@dataclass
class Token:
    type: TokenType
    value: Any
    line: int
    column: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, line={self.line}, col={self.column})"


class LexerError(Exception):
    def __init__(self, message: str, line: int, column: int):
        super().__init__(f"LexerError at line {line}, col {column}: {message}")
        self.message = message
        self.line = line
        self.column = column


class Lexer:
    """Scans Python-like source code into a sequence of Tokens with INDENT/DEDENT."""

    def __init__(self, source: str):
        self.source = source
        self.length = len(source)
        self.cursor = 0
        self.line = 1
        self.column = 1

        self.indent_stack = [0]
        self.tokens: List[Token] = []
        self.at_line_start = True

    def peek(self, offset: int = 0) -> str:
        pos = self.cursor + offset
        if pos < self.length:
            return self.source[pos]
        return ""

    def advance(self) -> str:
        if self.cursor >= self.length:
            return ""
        ch = self.source[self.cursor]
        self.cursor += 1
        if ch == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def _handle_line_start(self) -> None:
        """Processes blank lines, comments, and emits INDENT / DEDENT."""
        while self.cursor < self.length:
            spaces = 0
            start_line = self.line
            start_col = self.column

            while self.cursor < self.length:
                c = self.peek()
                if c == " ":
                    spaces += 1
                    self.advance()
                elif c == "\t":
                    spaces += 4
                    self.advance()
                else:
                    break

            c = self.peek()
            # Blank line
            if c == "\n":
                self.advance()
                continue
            if c == "\r":
                self.advance()
                if self.peek() == "\n":
                    self.advance()
                continue

            # Comment line
            if c == "#":
                while self.cursor < self.length and self.peek() not in ("\n", "\r"):
                    self.advance()
                if self.peek() == "\r":
                    self.advance()
                if self.peek() == "\n":
                    self.advance()
                continue

            # EOF reached with just spaces
            if self.cursor >= self.length:
                break

            # Meaningful code line
            current_indent = self.indent_stack[-1]
            if spaces > current_indent:
                self.indent_stack.append(spaces)
                self.tokens.append(Token(TokenType.INDENT, spaces, start_line, start_col))
            elif spaces < current_indent:
                while len(self.indent_stack) > 1 and self.indent_stack[-1] > spaces:
                    self.indent_stack.pop()
                    self.tokens.append(Token(TokenType.DEDENT, spaces, start_line, start_col))
                if self.indent_stack[-1] != spaces:
                    raise LexerError(
                        f"Unindent does not match any outer indentation level (got {spaces}, expected one of {self.indent_stack})",
                        start_line,
                        start_col,
                    )
            self.at_line_start = False
            return

    def tokenize(self) -> List[Token]:
        self.tokens = []
        self.indent_stack = [0]
        self.cursor = 0
        self.line = 1
        self.column = 1
        self.at_line_start = True

        while self.cursor < self.length:
            if self.at_line_start:
                self._handle_line_start()
                if self.cursor >= self.length:
                    break

            ch = self.peek()

            # Ignore inline whitespace (spaces, tabs)
            if ch in (" ", "\t", "\r"):
                self.advance()
                continue

            # Comments: # ... until end of line
            if ch == "#":
                while self.cursor < self.length and self.peek() not in ("\n", "\r"):
                    self.advance()
                continue

            # Newlines
            if ch == "\n" or ch == "\r":
                tok_line, tok_col = self.line, self.column
                if ch == "\r" and self.peek(1) == "\n":
                    self.advance()
                self.advance()
                # Only emit NEWLINE if the last emitted token is not already a NEWLINE or INDENT
                if self.tokens and self.tokens[-1].type not in (TokenType.NEWLINE, TokenType.INDENT):
                    self.tokens.append(Token(TokenType.NEWLINE, "\\n", tok_line, tok_col))
                self.at_line_start = True
                continue

            # Multi-character & Single-character operators/delimiters
            tok_line, tok_col = self.line, self.column

            if ch == "/" and self.peek(1) == "/":
                self.advance()
                self.advance()
                self.tokens.append(Token(TokenType.DOUBLE_SLASH, "//", tok_line, tok_col))
            elif ch == "=" and self.peek(1) == "=":
                self.advance()
                self.advance()
                self.tokens.append(Token(TokenType.EQ, "==", tok_line, tok_col))
            elif ch == "!" and self.peek(1) == "=":
                self.advance()
                self.advance()
                self.tokens.append(Token(TokenType.NEQ, "!=", tok_line, tok_col))
            elif ch == "<" and self.peek(1) == "=":
                self.advance()
                self.advance()
                self.tokens.append(Token(TokenType.LTE, "<=", tok_line, tok_col))
            elif ch == ">" and self.peek(1) == "=":
                self.advance()
                self.advance()
                self.tokens.append(Token(TokenType.GTE, ">=", tok_line, tok_col))
            elif ch == "+":
                self.advance()
                self.tokens.append(Token(TokenType.PLUS, "+", tok_line, tok_col))
            elif ch == "-":
                self.advance()
                self.tokens.append(Token(TokenType.MINUS, "-", tok_line, tok_col))
            elif ch == "*":
                self.advance()
                self.tokens.append(Token(TokenType.STAR, "*", tok_line, tok_col))
            elif ch == "/":
                self.advance()
                self.tokens.append(Token(TokenType.SLASH, "/", tok_line, tok_col))
            elif ch == "%":
                self.advance()
                self.tokens.append(Token(TokenType.PERCENT, "%", tok_line, tok_col))
            elif ch == "<":
                self.advance()
                self.tokens.append(Token(TokenType.LT, "<", tok_line, tok_col))
            elif ch == ">":
                self.advance()
                self.tokens.append(Token(TokenType.GT, ">", tok_line, tok_col))
            elif ch == "=":
                self.advance()
                self.tokens.append(Token(TokenType.ASSIGN, "=", tok_line, tok_col))
            elif ch == "(":
                self.advance()
                self.tokens.append(Token(TokenType.LPAREN, "(", tok_line, tok_col))
            elif ch == ")":
                self.advance()
                self.tokens.append(Token(TokenType.RPAREN, ")", tok_line, tok_col))
            elif ch == ":":
                self.advance()
                self.tokens.append(Token(TokenType.COLON, ":", tok_line, tok_col))
            elif ch == ",":
                self.advance()
                self.tokens.append(Token(TokenType.COMMA, ",", tok_line, tok_col))
            elif ch in ('"', "'"):
                self.tokens.append(self._scan_string(ch))
            elif ch.isdigit():
                self.tokens.append(self._scan_number())
            elif ch.isalpha() or ch == "_":
                self.tokens.append(self._scan_identifier())
            else:
                raise LexerError(f"Unexpected character: {ch!r}", tok_line, tok_col)

        # Handle trailing newlines and dedents
        if self.tokens and self.tokens[-1].type not in (TokenType.NEWLINE, TokenType.DEDENT):
            self.tokens.append(Token(TokenType.NEWLINE, "\\n", self.line, self.column))

        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            self.tokens.append(Token(TokenType.DEDENT, "", self.line, self.column))

        self.tokens.append(Token(TokenType.EOF, "", self.line, self.column))
        return self.tokens

    def _scan_string(self, quote: str) -> Token:
        tok_line, tok_col = self.line, self.column
        self.advance()  # consume opening quote
        chars = []

        while self.cursor < self.length:
            ch = self.peek()
            if ch == quote:
                self.advance()  # consume closing quote
                return Token(TokenType.STRING_LITERAL, "".join(chars), tok_line, tok_col)
            elif ch == "\\":
                self.advance()
                esc = self.peek()
                if esc == "n":
                    chars.append("\n")
                elif esc == "t":
                    chars.append("\t")
                elif esc == "\\":
                    chars.append("\\")
                elif esc == quote:
                    chars.append(quote)
                else:
                    chars.append(esc)
                self.advance()
            elif ch == "\n":
                raise LexerError("Unclosed string literal before newline", tok_line, tok_col)
            else:
                chars.append(ch)
                self.advance()

        raise LexerError("Unclosed string literal at end of file", tok_line, tok_col)

    def _scan_number(self) -> Token:
        tok_line, tok_col = self.line, self.column
        start_cursor = self.cursor
        is_float = False

        while self.cursor < self.length:
            ch = self.peek()
            if ch.isdigit():
                self.advance()
            elif ch == ".":
                if is_float:
                    raise LexerError("Malformed numeric literal with multiple decimal points", tok_line, tok_col)
                if self.peek(1).isdigit():
                    is_float = True
                    self.advance()
                else:
                    break
            else:
                break

        num_str = self.source[start_cursor : self.cursor]
        if is_float:
            return Token(TokenType.FLOAT_LITERAL, float(num_str), tok_line, tok_col)
        return Token(TokenType.INT_LITERAL, int(num_str), tok_line, tok_col)

    def _scan_identifier(self) -> Token:
        tok_line, tok_col = self.line, self.column
        start_cursor = self.cursor

        while self.cursor < self.length:
            ch = self.peek()
            if ch.isalnum() or ch == "_":
                self.advance()
            else:
                break

        ident = self.source[start_cursor : self.cursor]
        if ident in KEYWORDS:
            tok_type = KEYWORDS[ident]
            if tok_type == TokenType.BOOL_LITERAL:
                return Token(tok_type, ident == "True", tok_line, tok_col)
            return Token(tok_type, ident, tok_line, tok_col)

        return Token(TokenType.IDENTIFIER, ident, tok_line, tok_col)


def tokenize(source: str) -> List[Token]:
    lexer = Lexer(source)
    return lexer.tokenize()
