"""AST analyzer for Python test files."""

import ast
import re
from typing import Dict, Any, List, Set, Optional
from pathlib import Path
import structlog

logger = structlog.get_logger()


class ASTAnalyzer:
    """Analyzes Python test files using AST."""

    def analyze_file(self, file_path: str, content: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze a Python test file.

        Args:
            file_path: Path to the file
            content: File content (if None, reads from file_path)

        Returns:
            Analysis results
        """
        if content is None:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

        try:
            tree = ast.parse(content, filename=file_path)
            analyzer = TestFileAnalyzer()
            analyzer.visit(tree)
            return analyzer.get_results()
        except SyntaxError as e:
            logger.warning("Syntax error in file", file=file_path, error=str(e))
            return {
                "test_functions": [],
                "test_classes": [],
                "decorators": [],
                "assertions": [],
                "endpoints_tested": [],
                "has_errors": True,
                "error": str(e),
            }

    def analyze_directory(self, directory: str) -> Dict[str, Any]:
        """
        Analyze all Python test files in a directory.

        Args:
            directory: Directory path

        Returns:
            Aggregated analysis results
        """
        test_files = []
        for path in Path(directory).rglob("*.py"):
            if "test" in path.name.lower() or path.parent.name == "tests":
                test_files.append(str(path))

        all_tests = []
        all_classes = []
        all_decorators = []
        all_assertions = []
        all_endpoints = []
        files_analyzed = 0

        for file_path in test_files:
            try:
                result = self.analyze_file(file_path)
                if not result.get("has_errors"):
                    all_tests.extend(result.get("test_functions", []))
                    all_classes.extend(result.get("test_classes", []))
                    all_decorators.extend(result.get("decorators", []))
                    all_assertions.extend(result.get("assertions", []))
                    all_endpoints.extend(result.get("endpoints_tested", []))
                    files_analyzed += 1
            except Exception as e:
                logger.error("Failed to analyze file", file=file_path, error=str(e))

        return {
            "files_analyzed": files_analyzed,
            "total_test_functions": len(all_tests),
            "total_test_classes": len(all_classes),
            "test_functions": all_tests,
            "test_classes": all_classes,
            "decorators": list(set(all_decorators)),
            "assertions": all_assertions,
            "endpoints_tested": list(set(all_endpoints)),
        }


class TestFileAnalyzer(ast.NodeVisitor):
    """AST visitor for analyzing test files."""

    def __init__(self):
        self.test_functions: List[Dict[str, Any]] = []
        self.test_classes: List[Dict[str, Any]] = []
        self.decorators: Set[str] = set()
        self.assertions: List[Dict[str, Any]] = []
        self.endpoints_tested: Set[str] = set()
        self.current_class: Optional[str] = None
        self.current_function: Optional[str] = None

    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definition."""
        if "test" in node.name.lower():
            self.test_classes.append(
                {
                    "name": node.name,
                    "line": node.lineno,
                    "decorators": [self._get_decorator_name(d) for d in node.decorator_list],
                }
            )
            self.current_class = node.name
        self.generic_visit(node)
        self.current_class = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definition."""
        is_test = node.name.startswith("test_") or "test" in node.name.lower()

        if is_test or self.current_class:
            # Extract decorators
            for decorator in node.decorator_list:
                decorator_name = self._get_decorator_name(decorator)
                self.decorators.add(decorator_name)

            # Extract endpoint from decorators or function body
            endpoint = self._extract_endpoint(node)

            test_info = {
                "name": node.name,
                "line": node.lineno,
                "class": self.current_class,
                "decorators": [self._get_decorator_name(d) for d in node.decorator_list],
                "endpoint": endpoint,
            }

            self.test_functions.append(test_info)
            if endpoint:
                self.endpoints_tested.add(endpoint)

            self.current_function = node.name

        self.generic_visit(node)
        self.current_function = None

    def visit_Assert(self, node: ast.Assert):
        """Visit assert statement."""
        assertion_info = {
            "line": node.lineno,
            "function": self.current_function,
            "class": self.current_class,
        }
        self.assertions.append(assertion_info)

    def visit_Call(self, node: ast.Call):
        """Visit function call to extract API endpoints."""
        # Look for HTTP method calls (get, post, put, delete, etc.)
        if isinstance(node.func, ast.Attribute):
            method_name = node.func.attr
            if method_name in ["get", "post", "put", "delete", "patch"]:
                # Try to extract URL from arguments
                if node.args:
                    first_arg = node.args[0]
                    if isinstance(first_arg, ast.Constant):
                        url = first_arg.value
                        if isinstance(url, str) and url.startswith("/"):
                            self.endpoints_tested.add(url)

        self.generic_visit(node)

    def _get_decorator_name(self, decorator: ast.expr) -> str:
        """Extract decorator name."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return decorator.attr
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                return decorator.func.id
            elif isinstance(decorator.func, ast.Attribute):
                return decorator.func.attr
        return "unknown"

    def _extract_endpoint(self, node: ast.FunctionDef) -> Optional[str]:
        """Extract API endpoint from test function."""
        # Check decorators for route information
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    if decorator.func.attr in ["route", "get", "post", "put", "delete"]:
                        if decorator.args:
                            arg = decorator.args[0]
                            if isinstance(arg, ast.Constant):
                                return arg.value

        # Check function body for URL patterns
        for stmt in node.body:
            endpoint = self._find_url_in_node(stmt)
            if endpoint:
                return endpoint

        return None

    def _find_url_in_node(self, node: ast.AST) -> Optional[str]:
        """Recursively find URL patterns in AST node."""
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Attribute):
                if call.func.attr in ["get", "post", "put", "delete", "patch"]:
                    if call.args:
                        arg = call.args[0]
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            if arg.value.startswith("/"):
                                return arg.value

        # Recursively search in child nodes
        for child in ast.iter_child_nodes(node):
            result = self._find_url_in_node(child)
            if result:
                return result

        return None

    def get_results(self) -> Dict[str, Any]:
        """Get analysis results."""
        return {
            "test_functions": self.test_functions,
            "test_classes": self.test_classes,
            "decorators": list(self.decorators),
            "assertions": self.assertions,
            "endpoints_tested": list(self.endpoints_tested),
            "has_errors": False,
        }



