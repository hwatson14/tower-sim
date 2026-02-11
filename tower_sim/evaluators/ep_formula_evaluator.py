from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Iterable, List, Mapping, Sequence

from tower_sim.registry.ep_formula_registry import (
    LambdaMechanic,
    load_ep_formula_registry,
)


class EpFormulaError(ValueError):
    pass


class UnknownParameterError(EpFormulaError):
    pass


class FormulaParseError(EpFormulaError):
    pass


class FormulaEvalError(EpFormulaError):
    pass


TokenType = str


@dataclass(frozen=True)
class Token:
    kind: TokenType
    value: str


@dataclass(frozen=True)
class NumberNode:
    value: float


@dataclass(frozen=True)
class IdentifierNode:
    name: str


@dataclass(frozen=True)
class UnaryNode:
    op: str
    operand: "ExprNode"


@dataclass(frozen=True)
class BinaryNode:
    left: "ExprNode"
    op: str
    right: "ExprNode"


@dataclass(frozen=True)
class CallNode:
    name: str
    args: Sequence["ExprNode"]


ExprNode = NumberNode | IdentifierNode | UnaryNode | BinaryNode | CallNode


def evaluate_lambda(
    lambda_name: str,
    args: Mapping[str, float] | Sequence[float],
) -> float:
    registry = load_ep_formula_registry(strict=False)
    if lambda_name not in registry.mechanics:
        raise UnknownParameterError(f"Unknown LAMBDA mechanic {lambda_name!r}.")
    mechanic = registry.mechanics[lambda_name]
    bindings = _bind_parameters(mechanic, args)
    expr = _parse_expression(mechanic.body)
    return float(_eval_expr(expr, bindings))


def _bind_parameters(
    mechanic: LambdaMechanic,
    args: Mapping[str, float] | Sequence[float],
) -> Dict[str, float]:
    if isinstance(args, Mapping):
        missing = [name for name in mechanic.parameters if name not in args]
        if missing:
            raise UnknownParameterError(
                f"LAMBDA {mechanic.name} missing parameters: {missing}"
            )
        return _with_identifier_case_aliases(
            {name: float(args[name]) for name in mechanic.parameters}
        )
    if len(args) != len(mechanic.parameters):
        raise UnknownParameterError(
            f"LAMBDA {mechanic.name} expects {len(mechanic.parameters)} args; got {len(args)}."
        )
    return _with_identifier_case_aliases(
        {
            name: float(value)
            for name, value in zip(mechanic.parameters, args, strict=True)
        }
    )


def _with_identifier_case_aliases(bindings: Dict[str, float]) -> Dict[str, float]:
    """Excel identifiers are case-insensitive; mirror parameter bindings accordingly."""
    aliased = dict(bindings)
    for name, value in list(bindings.items()):
        aliased.setdefault(name.lower(), value)
        aliased.setdefault(name.upper(), value)
    return aliased


def _eval_expr(expr: ExprNode, env: Dict[str, float]) -> float:
    if isinstance(expr, NumberNode):
        return float(expr.value)
    if isinstance(expr, IdentifierNode):
        if expr.name not in env:
            raise FormulaEvalError(f"Unknown identifier {expr.name!r}.")
        return float(env[expr.name])
    if isinstance(expr, UnaryNode):
        value = _eval_expr(expr.operand, env)
        if expr.op == "+":
            return value
        if expr.op == "-":
            return -value
        raise FormulaEvalError(f"Unknown unary operator {expr.op!r}.")
    if isinstance(expr, BinaryNode):
        left = _eval_expr(expr.left, env)
        right = _eval_expr(expr.right, env)
        if expr.op == "+":
            return left + right
        if expr.op == "-":
            return left - right
        if expr.op == "*":
            return left * right
        if expr.op == "/":
            return left / right
        if expr.op == "^":
            return left**right
        if expr.op == "=":
            return float(left == right)
        if expr.op == "<>":
            return float(left != right)
        if expr.op == "<":
            return float(left < right)
        if expr.op == "<=":
            return float(left <= right)
        if expr.op == ">":
            return float(left > right)
        if expr.op == ">=":
            return float(left >= right)
        raise FormulaEvalError(f"Unknown binary operator {expr.op!r}.")
    if isinstance(expr, CallNode):
        return _eval_call(expr, env)
    raise FormulaEvalError(f"Unsupported expression node {expr!r}.")


def _eval_call(node: CallNode, env: Dict[str, float]) -> float:
    name = node.name.upper()
    if name == "LET":
        return _eval_let(node.args, env)
    if name == "IF":
        if len(node.args) != 3:
            raise FormulaEvalError("IF expects three arguments.")
        cond = _eval_expr(node.args[0], env)
        return _eval_expr(node.args[1], env) if cond else _eval_expr(node.args[2], env)
    if name == "AND":
        return float(all(_eval_expr(arg, env) for arg in node.args))
    if name == "OR":
        return float(any(_eval_expr(arg, env) for arg in node.args))
    if name == "MIN":
        values = [_eval_expr(arg, env) for arg in node.args]
        return float(min(values))
    if name == "MAX":
        values = [_eval_expr(arg, env) for arg in node.args]
        return float(max(values))
    raise FormulaEvalError(f"Unsupported function call {node.name!r}.")


def _eval_let(args: Sequence[ExprNode], env: Dict[str, float]) -> float:
    if len(args) < 2:
        raise FormulaEvalError("LET expects at least two arguments.")
    if len(args) % 2 == 0:
        raise FormulaEvalError("LET expects pairs of name/value plus a result expression.")
    scope = dict(env)
    for index in range(0, len(args) - 1, 2):
        name_node = args[index]
        if not isinstance(name_node, IdentifierNode):
            raise FormulaEvalError("LET variable name must be an identifier.")
        value = _eval_expr(args[index + 1], scope)
        scope[name_node.name] = float(value)
    return _eval_expr(args[-1], scope)


@lru_cache(maxsize=128)
def _parse_expression(expr: str) -> ExprNode:
    tokens = _tokenize(expr)
    parser = _Parser(tokens)
    parsed = parser.parse_expression()
    if not parser.is_at_end():
        raise FormulaParseError("Unexpected trailing tokens in formula.")
    return parsed


def _tokenize(expr: str) -> List[Token]:
    tokens: List[Token] = []
    i = 0
    while i < len(expr):
        char = expr[i]
        if char.isspace():
            i += 1
            continue
        if char.isdigit() or (char == "." and i + 1 < len(expr) and expr[i + 1].isdigit()):
            start = i
            i += 1
            while i < len(expr) and (expr[i].isdigit() or expr[i] == "."):
                i += 1
            value = expr[start:i]
            if i < len(expr) and expr[i] == "%":
                tokens.append(Token("NUMBER", str(float(value) / 100.0)))
                i += 1
                continue
            tokens.append(Token("NUMBER", value))
            continue
        if char.isalpha() or char == "_":
            start = i
            i += 1
            while i < len(expr) and (expr[i].isalnum() or expr[i] == "_"):
                i += 1
            tokens.append(Token("IDENT", expr[start:i]))
            continue
        if expr.startswith("<=", i) or expr.startswith(">=", i) or expr.startswith("<>", i):
            tokens.append(Token("OP", expr[i : i + 2]))
            i += 2
            continue
        if char in "+-*/^=<>(),":
            if char in "+-*/^=<>":
                tokens.append(Token("OP", char))
            elif char == "(":
                tokens.append(Token("LPAREN", char))
            elif char == ")":
                tokens.append(Token("RPAREN", char))
            elif char == ",":
                tokens.append(Token("COMMA", char))
            i += 1
            continue
        raise FormulaParseError(f"Unexpected character {char!r} in formula.")
    return tokens


class _Parser:
    def __init__(self, tokens: Sequence[Token]) -> None:
        self._tokens = list(tokens)
        self._pos = 0

    def parse_expression(self) -> ExprNode:
        return self._parse_comparison()

    def _parse_comparison(self) -> ExprNode:
        node = self._parse_addition()
        while self._match_op({"=", "<>", "<", "<=", ">", ">="}):
            op = self._previous().value
            right = self._parse_addition()
            node = BinaryNode(node, op, right)
        return node

    def _parse_addition(self) -> ExprNode:
        node = self._parse_multiplication()
        while self._match_op({"+", "-"}):
            op = self._previous().value
            right = self._parse_multiplication()
            node = BinaryNode(node, op, right)
        return node

    def _parse_multiplication(self) -> ExprNode:
        node = self._parse_power()
        while self._match_op({"*", "/"}):
            op = self._previous().value
            right = self._parse_power()
            node = BinaryNode(node, op, right)
        return node

    def _parse_power(self) -> ExprNode:
        node = self._parse_unary()
        while self._match_op({"^"}):
            op = self._previous().value
            right = self._parse_unary()
            node = BinaryNode(node, op, right)
        return node

    def _parse_unary(self) -> ExprNode:
        if self._match_op({"+", "-"}):
            op = self._previous().value
            operand = self._parse_unary()
            return UnaryNode(op, operand)
        return self._parse_primary()

    def _parse_primary(self) -> ExprNode:
        if self._match("NUMBER"):
            return NumberNode(float(self._previous().value))
        if self._match("IDENT"):
            ident = self._previous().value
            if self._match("LPAREN"):
                args = self._parse_arguments()
                return CallNode(ident, args)
            return IdentifierNode(ident)
        if self._match("LPAREN"):
            expr = self.parse_expression()
            if not self._match("RPAREN"):
                raise FormulaParseError("Expected ')' in formula.")
            return expr
        raise FormulaParseError("Unexpected token in formula.")

    def _parse_arguments(self) -> Sequence[ExprNode]:
        args: List[ExprNode] = []
        if self._check("RPAREN"):
            self._advance()
            return args
        while True:
            args.append(self.parse_expression())
            if self._match("COMMA"):
                continue
            if self._match("RPAREN"):
                break
            raise FormulaParseError("Expected ',' or ')' in arguments.")
        return args

    def _match(self, kind: TokenType) -> bool:
        if self._check(kind):
            self._advance()
            return True
        return False

    def _match_op(self, ops: Iterable[str]) -> bool:
        if self._check("OP") and self._peek().value in ops:
            self._advance()
            return True
        return False

    def _check(self, kind: TokenType) -> bool:
        if self.is_at_end():
            return False
        return self._peek().kind == kind

    def _advance(self) -> Token:
        token = self._tokens[self._pos]
        self._pos += 1
        return token

    def _peek(self) -> Token:
        return self._tokens[self._pos]

    def _previous(self) -> Token:
        return self._tokens[self._pos - 1]

    def is_at_end(self) -> bool:
        return self._pos >= len(self._tokens)


__all__ = [
    "EpFormulaError",
    "FormulaEvalError",
    "FormulaParseError",
    "UnknownParameterError",
    "evaluate_lambda",
]
