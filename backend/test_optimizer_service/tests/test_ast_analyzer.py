"""Tests for AST analyzer."""

import pytest
from app.services.ast_analyzer import ASTAnalyzer


def test_ast_analyzer_initialization():
    """Test AST analyzer can be initialized."""
    analyzer = ASTAnalyzer()
    assert analyzer is not None


def test_analyze_file():
    """Test analyzing a Python file."""
    analyzer = ASTAnalyzer()
    code = """
def test_example():
    assert True
"""
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_path = f.name
    
    try:
        result = analyzer.analyze_file(temp_path)
        assert result is not None
        assert "test_functions" in result or "test_classes" in result
    finally:
        os.unlink(temp_path)


def test_analyze_directory():
    """Test analyzing a directory of test files."""
    analyzer = ASTAnalyzer()
    import tempfile
    import os
    
    temp_dir = tempfile.mkdtemp()
    test_file = os.path.join(temp_dir, "test_example.py")
    
    with open(test_file, 'w') as f:
        f.write("""
import pytest

def test_one():
    assert True

def test_two():
    assert False
""")
    
    try:
        result = analyzer.analyze_directory(temp_dir)
        assert result is not None
        assert "test_functions" in result or "total_test_functions" in result
    finally:
        import shutil
        shutil.rmtree(temp_dir)

