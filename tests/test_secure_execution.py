"""
Tests for secure function execution system.
"""

import pytest
import asyncio
from tools.execution import execute_function_safely, SecurityError, ExecutionTimeoutError

class TestSecureExecution:
    """Test cases for secure function execution."""
    
    @pytest.mark.asyncio
    async def test_basic_function_execution(self):
        """Test basic safe function execution."""
        code = '''
def add_numbers(a, b):
    """Add two numbers together."""
    return a + b
'''
        
        result = await execute_function_safely(
            code=code,
            function_name="add_numbers",
            test_inputs=[{'a': 2, 'b': 3}]
        )
        
        assert result['success'] == True
        assert len(result['test_results']) == 1
        assert result['test_results'][0]['success'] == True
        assert result['test_results'][0]['output'] == 5
        assert result['execution_time_ms'] > 0
    
    @pytest.mark.asyncio
    async def test_forbidden_import_detection(self):
        """Test detection of forbidden imports."""
        code = '''
import os
def dangerous_function():
    return os.system("ls")
'''
        
        result = await execute_function_safely(
            code=code,
            function_name="dangerous_function"
        )
        
        assert result['success'] == False
        assert any('Forbidden import: os' in error for error in result['errors'])
    
    @pytest.mark.asyncio
    async def test_forbidden_builtin_detection(self):
        """Test detection of forbidden builtin functions."""
        code = '''
def dangerous_function():
    return eval("1 + 1")
'''
        
        result = await execute_function_safely(
            code=code,
            function_name="dangerous_function"
        )
        
        assert result['success'] == False
        assert any('Forbidden function call: eval' in error for error in result['errors'])
    
    @pytest.mark.asyncio
    async def test_timeout_protection(self):
        """Test timeout protection for long-running functions."""
        code = '''
import time
def slow_function():
    time.sleep(10)  # This should timeout
    return "done"
'''
        
        # This should be caught during security analysis
        result = await execute_function_safely(
            code=code,
            function_name="slow_function",
            timeout=1
        )
        
        # Should fail at security analysis stage due to time import
        assert result['success'] == False
    
    @pytest.mark.asyncio
    async def test_allowed_operations(self):
        """Test that allowed operations work correctly."""
        code = '''
import math
def calculate_circle_area(radius):
    """Calculate the area of a circle."""
    return math.pi * radius ** 2
'''
        
        result = await execute_function_safely(
            code=code,
            function_name="calculate_circle_area",
            test_inputs=[{'radius': 5}]
        )
        
        assert result['success'] == True
        assert len(result['test_results']) == 1
        assert result['test_results'][0]['success'] == True
        expected_area = 3.14159 * 25  # Approximately
        assert abs(result['test_results'][0]['output'] - expected_area) < 0.1
    
    @pytest.mark.asyncio
    async def test_multiple_test_inputs(self):
        """Test execution with multiple test inputs."""
        code = '''
def multiply(x, y):
    """Multiply two numbers."""
    return x * y
'''
        
        test_inputs = [
            {'x': 2, 'y': 3},
            {'x': 4, 'y': 5},
            {'x': 0, 'y': 10}
        ]
        
        result = await execute_function_safely(
            code=code,
            function_name="multiply",
            test_inputs=test_inputs
        )
        
        assert result['success'] == True
        assert len(result['test_results']) == 3
        assert result['test_results'][0]['output'] == 6
        assert result['test_results'][1]['output'] == 20
        assert result['test_results'][2]['output'] == 0
    
    @pytest.mark.asyncio
    async def test_syntax_error_handling(self):
        """Test handling of syntax errors in code."""
        code = '''
def broken_function(
    return "missing colon and parenthesis"
'''
        
        result = await execute_function_safely(
            code=code,
            function_name="broken_function"
        )
        
        assert result['success'] == False
        assert any('Syntax error' in error for error in result['errors'])
    
    @pytest.mark.asyncio
    async def test_runtime_error_handling(self):
        """Test handling of runtime errors."""
        code = '''
def divide_by_zero():
    """This function will cause a runtime error."""
    return 10 / 0
'''
        
        result = await execute_function_safely(
            code=code,
            function_name="divide_by_zero"
        )
        
        # Should execute but the test should fail
        assert result['success'] == True  # Code executed
        assert len(result['test_results']) == 1
        assert result['test_results'][0]['success'] == False
        assert 'ZeroDivisionError' in result['test_results'][0]['error']['type']
    
    @pytest.mark.asyncio
    async def test_function_with_no_parameters(self):
        """Test execution of function with no parameters."""
        code = '''
def get_constant():
    """Return a constant value."""
    return 42
'''
        
        result = await execute_function_safely(
            code=code,
            function_name="get_constant"
        )
        
        assert result['success'] == True
        assert result['return_value'] == 42
    
    @pytest.mark.asyncio
    async def test_complex_data_structures(self):
        """Test handling of complex data structures."""
        code = '''
def process_data(data):
    """Process a dictionary of data."""
    return {
        'total': sum(data.values()),
        'keys': list(data.keys()),
        'max_value': max(data.values())
    }
'''
        
        test_data = {'a': 10, 'b': 20, 'c': 5}
        
        result = await execute_function_safely(
            code=code,
            function_name="process_data",
            test_inputs=[{'data': test_data}]
        )
        
        assert result['success'] == True
        output = result['test_results'][0]['output']
        assert output['total'] == 35
        assert set(output['keys']) == {'a', 'b', 'c'}
        assert output['max_value'] == 20