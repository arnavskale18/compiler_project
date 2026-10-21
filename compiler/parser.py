"""Recursive Descent Parser for CodeX.

Constructs an explicit AST from a token stream with rigorous operator precedence,
associativity, and precise syntax error diagnostics.
"""

from typing import List, Optional
from .lexer import Token, TokenType
from .ast_nodes import (
    Program,
    Statement,
    AssignStmt,
    PrintStmt,
    PassStmt,
    IfStmt,
    ElifBranch,
    WhileStmt,
    Expression,
    BinaryOp,
    UnaryOp,
    Literal,
    Identifier,
)


class ParserError(Exception):
    def __init__(self, message: str, line: int, column: int):
        super().__init__(f"ParserError at line {line}, col {column}: {message}")
        self.message = message
        self.line = line
        self.column = column


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.cursor = 0

    def current(self) -> Token:
        if self.cursor < len(self.tokens):
            return self.tokens[self.cursor]
        return self.tokens[-1]  # Return EOF or last token

    def peek(self, offset: int = 1) -> Token:
        pos = self.cursor + offset
        if pos < len(self.tokens):
            return self.tokens[pos]
        return self.tokens[-1]

    def advance(self) -> Token:
        tok = self.current()
        if self.cursor < len(self.tokens):
            self.cursor += 1
        return tok

    def check(self, *token_types: TokenType) -> bool:
        return self.current().type in token_types

    def match(self, *token_types: TokenType) -> Optional[Token]:
        if self.check(*token_types):
            return self.advance()
        return None

    def consume(self, token_type: TokenType, err_msg: str) -> Token:
        if self.check(token_type):
            return self.advance()
        curr = self.current()
        raise ParserError(f"{err_msg} (got {curr.type.value!r})", curr.line, curr.column)

    def parse(self) -> Program:
        statements: List[Statement] = []
        while not self.check(TokenType.EOF):
            if self.match(TokenType.NEWLINE):
                continue
            stmt = self.statement()
            if stmt is not None:
                statements.append(stmt)
        return Program(statements=statements)

    # --------------------------------------------------------------------------
    # Statements
    # --------------------------------------------------------------------------

    def statement(self) -> Statement:
        curr = self.current()
        if curr.type == TokenType.IF:
            return self.if_statement()
        if curr.type == TokenType.WHILE:
            return self.while_statement()
        return self.simple_statement()

    def simple_statement(self) -> Statement:
        curr = self.current()
        if curr.type == TokenType.PRINT:
            stmt = self.print_statement()
        elif curr.type == TokenType.PASS:
            self.advance()
            stmt = PassStmt(line=curr.line, column=curr.column)
        elif curr.type == TokenType.IDENTIFIER and self.peek().type == TokenType.ASSIGN:
            stmt = self.assign_statement()
        else:
            raise ParserError(
                f"Unexpected token {curr.type.value!r} at start of statement",
                curr.line,
                curr.column,
            )

        # Simple statements must end with a NEWLINE or EOF
        if not self.check(TokenType.EOF, TokenType.DEDENT):
            self.consume(TokenType.NEWLINE, "Expected newline after statement")
        return stmt

    def assign_statement(self) -> AssignStmt:
        id_tok = self.consume(TokenType.IDENTIFIER, "Expected identifier in assignment")
        self.consume(TokenType.ASSIGN, "Expected '=' in assignment")
        val = self.expr()
        return AssignStmt(
            target=Identifier(name=id_tok.value, line=id_tok.line, column=id_tok.column),
            value=val,
            line=id_tok.line,
            column=id_tok.column,
        )

    def print_statement(self) -> PrintStmt:
        p_tok = self.consume(TokenType.PRINT, "Expected 'print'")
        self.consume(TokenType.LPAREN, "Expected '(' after 'print'")
        expressions: List[Expression] = []

        if not self.check(TokenType.RPAREN):
            expressions.append(self.expr())
            while self.match(TokenType.COMMA):
                expressions.append(self.expr())

        self.consume(TokenType.RPAREN, "Expected ')' to close print arguments")
        return PrintStmt(expressions=expressions, line=p_tok.line, column=p_tok.column)

    def block(self) -> List[Statement]:
        self.consume(TokenType.COLON, "Expected ':' before block")
        self.consume(TokenType.NEWLINE, "Expected newline after ':'")
        self.consume(TokenType.INDENT, "Expected indented block")

        statements: List[Statement] = []
        while not self.check(TokenType.DEDENT, TokenType.EOF):
            if self.match(TokenType.NEWLINE):
                continue
            statements.append(self.statement())

        self.consume(TokenType.DEDENT, "Expected dedent at end of block")
        if not statements:
            raise ParserError("Empty block is not allowed; use 'pass' if intentional", self.current().line, self.current().column)
        return statements

    def if_statement(self) -> IfStmt:
        if_tok = self.consume(TokenType.IF, "Expected 'if'")
        cond = self.expr()
        then_body = self.block()

        elif_branches: List[ElifBranch] = []
        while self.check(TokenType.ELIF):
            elif_tok = self.advance()
            elif_cond = self.expr()
            elif_body = self.block()
            elif_branches.append(
                ElifBranch(condition=elif_cond, body=elif_body, line=elif_tok.line, column=elif_tok.column)
            )

        else_body: Optional[List[Statement]] = None
        if self.match(TokenType.ELSE):
            else_body = self.block()

        return IfStmt(
            condition=cond,
            then_body=then_body,
            elif_branches=elif_branches,
            else_body=else_body,
            line=if_tok.line,
            column=if_tok.column,
        )

    def while_statement(self) -> WhileStmt:
        w_tok = self.consume(TokenType.WHILE, "Expected 'while'")
        cond = self.expr()
        body = self.block()
        return WhileStmt(condition=cond, body=body, line=w_tok.line, column=w_tok.column)

    # --------------------------------------------------------------------------
    # Expressions & Precedence
    # --------------------------------------------------------------------------

    def expr(self) -> Expression:
        return self.or_expr()

    def or_expr(self) -> Expression:
        node = self.and_expr()
        while self.check(TokenType.OR):
            op_tok = self.advance()
            right = self.and_expr()
            node = BinaryOp(left=node, op="or", right=right, line=op_tok.line, column=op_tok.column)
        return node

    def and_expr(self) -> Expression:
        node = self.not_expr()
        while self.check(TokenType.AND):
            op_tok = self.advance()
            right = self.not_expr()
            node = BinaryOp(left=node, op="and", right=right, line=op_tok.line, column=op_tok.column)
        return node

    def not_expr(self) -> Expression:
        if self.check(TokenType.NOT):
            op_tok = self.advance()
            operand = self.not_expr()
            return UnaryOp(op="not", operand=operand, line=op_tok.line, column=op_tok.column)
        return self.comparison_expr()

    def comparison_expr(self) -> Expression:
        node = self.term_expr()
        cmp_ops = (
            TokenType.EQ,
            TokenType.NEQ,
            TokenType.LT,
            TokenType.LTE,
            TokenType.GT,
            TokenType.GTE,
        )
        while self.check(*cmp_ops):
            op_tok = self.advance()
            right = self.term_expr()
            node = BinaryOp(left=node, op=op_tok.value, right=right, line=op_tok.line, column=op_tok.column)
        return node

    def term_expr(self) -> Expression:
        node = self.factor_expr()
        while self.check(TokenType.PLUS, TokenType.MINUS):
            op_tok = self.advance()
            right = self.factor_expr()
            node = BinaryOp(left=node, op=op_tok.value, right=right, line=op_tok.line, column=op_tok.column)
        return node

    def factor_expr(self) -> Expression:
        node = self.unary_expr()
        mul_ops = (TokenType.STAR, TokenType.SLASH, TokenType.DOUBLE_SLASH, TokenType.PERCENT)
        while self.check(*mul_ops):
            op_tok = self.advance()
            right = self.unary_expr()
            node = BinaryOp(left=node, op=op_tok.value, right=right, line=op_tok.line, column=op_tok.column)
        return node

    def unary_expr(self) -> Expression:
        if self.check(TokenType.PLUS, TokenType.MINUS):
            op_tok = self.advance()
            operand = self.unary_expr()
            return UnaryOp(op=op_tok.value, operand=operand, line=op_tok.line, column=op_tok.column)
        return self.primary_expr()

    def primary_expr(self) -> Expression:
        curr = self.current()

        if curr.type == TokenType.INT_LITERAL:
            self.advance()
            return Literal(value=curr.value, lit_type="int", line=curr.line, column=curr.column)

        if curr.type == TokenType.FLOAT_LITERAL:
            self.advance()
            return Literal(value=curr.value, lit_type="float", line=curr.line, column=curr.column)

        if curr.type == TokenType.STRING_LITERAL:
            self.advance()
            return Literal(value=curr.value, lit_type="string", line=curr.line, column=curr.column)

        if curr.type == TokenType.BOOL_LITERAL:
            self.advance()
            return Literal(value=curr.value, lit_type="bool", line=curr.line, column=curr.column)

        if curr.type == TokenType.IDENTIFIER:
            self.advance()
            return Identifier(name=curr.value, line=curr.line, column=curr.column)

        if curr.type == TokenType.LPAREN:
            self.advance()
            expr = self.expr()
            self.consume(TokenType.RPAREN, "Expected ')' to close expression")
            return expr

        raise ParserError(f"Unexpected token in expression: {curr.type.value!r}", curr.line, curr.column)


def parse_source(source: str) -> Program:
    from .lexer import tokenize
    tokens = tokenize(source)
    parser = Parser(tokens)
    return parser.parse()
