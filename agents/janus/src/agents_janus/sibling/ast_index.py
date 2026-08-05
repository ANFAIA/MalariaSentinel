"""Tree-sitter Python AST index — symbol-level conflict detection."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Symbol:
    name: str
    kind: str  # "function", "class", "method"
    start_line: int
    end_line: int
    start_byte: int
    end_byte: int


class ASTIndex:
    """Parse a Python file into symbols using tree-sitter."""

    def __init__(self):
        self._parser = None
        self._lang = None

    def _ensure_parser(self):
        if self._parser is None:
            try:
                import tree_sitter_python as tspython
                from tree_sitter import Language, Parser
                self._lang = Language(tspython.language())
                self._parser = Parser(self._lang)
            except ImportError:
                raise ImportError(
                    "tree-sitter and tree-sitter-python required: pip install tree-sitter tree-sitter-python"
                )

    def parse(self, filepath: str | Path) -> list[Symbol]:
        """Parse a Python file and return its top-level symbols."""
        self._ensure_parser()
        path = Path(filepath)
        code = path.read_bytes()
        tree = self._parser.parse(code)
        symbols = []
        self._walk_node(tree.root_node, symbols, depth=0)
        return symbols

    def _walk_node(self, node, symbols: list[Symbol], depth: int):
        """Walk AST tree, collecting function/class definitions at depth 0-1."""
        for child in node.children:
            if child.type == "function_definition":
                name_node = child.child_by_field_name("name")
                if name_node and depth <= 1:
                    symbols.append(Symbol(
                        name=name_node.text.decode(),
                        kind="method" if depth == 1 else "function",
                        start_line=child.start_point[0],
                        end_line=child.end_point[0],
                        start_byte=child.start_byte,
                        end_byte=child.end_byte,
                    ))
            elif child.type == "class_definition":
                name_node = child.child_by_field_name("name")
                if name_node and depth == 0:
                    symbols.append(Symbol(
                        name=name_node.text.decode(),
                        kind="class",
                        start_line=child.start_point[0],
                        end_line=child.end_point[0],
                        start_byte=child.start_byte,
                        end_byte=child.end_byte,
                    ))
            # Recurse into class bodies
            if child.type in ("class_definition", "module"):
                self._walk_node(child, symbols, depth + 1)

    def find_overlapping_symbols(self, filepath: str | Path, other_symbols: list[Symbol]) -> list[Symbol]:
        """Given symbols from another sibling, find which ones overlap with this file."""
        my_symbols = self.parse(filepath)
        overlapping = []
        for other in other_symbols:
            for mine in my_symbols:
                if other.name == mine.name and other.kind == mine.kind:
                    if not (other.end_line < mine.start_line or other.start_line > mine.end_line):
                        overlapping.append(other)
        return overlapping
