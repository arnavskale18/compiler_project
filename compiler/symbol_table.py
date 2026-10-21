"""Symbol Table for CodeX Semantic Analysis.

Manages scoped identifiers, types, declaration positions, and initialization states.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any


@dataclass
class Symbol:
    name: str
    type_name: str  # "int", "float", "bool", "string"
    scope_level: int
    line_declared: int
    column_declared: int
    is_initialized: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type_name,
            "scope_level": self.scope_level,
            "line_declared": self.line_declared,
            "column_declared": self.column_declared,
            "is_initialized": self.is_initialized,
        }


class Scope:
    def __init__(self, level: int, parent: Optional["Scope"] = None):
        self.level = level
        self.parent = parent
        self.symbols: Dict[str, Symbol] = {}

    def insert(self, symbol: Symbol) -> None:
        self.symbols[symbol.name] = symbol

    def lookup_local(self, name: str) -> Optional[Symbol]:
        return self.symbols.get(name)

    def lookup(self, name: str) -> Optional[Symbol]:
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        return None


class SymbolTable:
    def __init__(self):
        self.global_scope = Scope(level=0)
        self.current_scope = self.global_scope
        self.scope_level = 0
        self.all_symbols_list: List[Symbol] = []

    def enter_scope(self) -> None:
        self.scope_level += 1
        new_scope = Scope(level=self.scope_level, parent=self.current_scope)
        self.current_scope = new_scope

    def exit_scope(self) -> None:
        if self.current_scope.parent is not None:
            self.current_scope = self.current_scope.parent
            self.scope_level -= 1

    def define(self, name: str, type_name: str, line: int, column: int) -> Symbol:
        sym = Symbol(
            name=name,
            type_name=type_name,
            scope_level=self.scope_level,
            line_declared=line,
            column_declared=column,
        )
        self.current_scope.insert(sym)
        self.all_symbols_list.append(sym)
        return sym

    def lookup(self, name: str) -> Optional[Symbol]:
        return self.current_scope.lookup(name)

    def lookup_current(self, name: str) -> Optional[Symbol]:
        return self.current_scope.lookup_local(name)

    def get_all_symbols(self) -> List[Symbol]:
        return list(self.all_symbols_list)
