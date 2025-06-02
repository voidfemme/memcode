"""
Tests for the function testing framework.
"""

import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, patch

from services.function_testing import (
    FunctionTestingService, TestCase, TestResult, testing_service
)
from data.models import Function


class TestFunctionTestingFramework:
    """Test cases for the function testing framework."""
    
    def test_test_case_creation(self):
        """Test TestCase class functionality."""
        test_case = TestCase(
            name="test_addition",
            input_data={'a': 2, 'b': 3},
            expected_output=5,
            description="Test basic addition"
        )
        
        assert test_case.name == "test_addition"
        assert test_case.input_data == {'a': 2, 'b': 3}
        assert test_case.expected_output == 5
        assert test_case.description == "Test basic addition"
        
        # Test serialization
        test_dict = test_case.to_dict()
        assert test_dict['name'] == "test_addition"
        assert test_dict['input_data'] == {'a': 2, 'b': 3}
        
        # Test deserialization
        recreated = TestCase.from_dict(test_dict)
        assert recreated.name == test_case.name
        assert recreated.input_data == test_case.input_data
    
    def test_test_result_creation(self):
        """Test TestResult class functionality."""
        result = TestResult(
            test_name="test_addition",
            passed=True,
            execution_time_ms=100,
            output=5,
            expected_output=5
        )
        
        assert result.test_name == "test_addition"
        assert result.passed == True
        assert result.execution_time_ms == 100
        assert result.output == 5
        
        # Test serialization
        result_dict = result.to_dict()
        assert result_dict['test_name'] == "test_addition"
        assert result_dict['passed'] == True
        assert result_dict['execution_time_ms'] == 100
    
    @pytest.mark.asyncio
    async def test_output_comparison(self):
        """Test the output comparison logic."""
        service = FunctionTestingService()
        
        # Test exact matches
        assert service._compare_outputs(5, 5) == True
        assert service._compare_outputs("hello", "hello") == True
        assert service._compare_outputs([1, 2, 3], [1, 2, 3]) == True
        assert service._compare_outputs({'a': 1}, {'a': 1}) == True
        
        # Test mismatches
        assert service._compare_outputs(5, 6) == False
        assert service._compare_outputs("hello", "world") == False
        assert service._compare_outputs([1, 2, 3], [1, 2, 4]) == False
        assert service._compare_outputs({'a': 1}, {'a': 2}) == False
        
        # Test None expected (should always pass)
        assert service._compare_outputs(5, None) == True
        assert service._compare_outputs("anything", None) == True
    
    @pytest.mark.asyncio
    async def test_generate_test_cases(self):
        """Test automatic test case generation."""
        service = FunctionTestingService()
        
        # Test addition function
        add_function = Function(
            name="add_numbers",
            description="Add two numbers together",
            code="def add_numbers(a, b): return a + b"
        )
        
        test_cases = await service.generate_test_cases(add_function, count=3)
        
        assert len(test_cases) == 3
        assert all(isinstance(tc, TestCase) for tc in test_cases)
        assert any("addition" in tc.description.lower() for tc in test_cases)
        
        # Test sort function
        sort_function = Function(
            name="sort_list",
            description="Sort a list of numbers",
            code="def sort_list(lst): return sorted(lst)"
        )
        
        test_cases = await service.generate_test_cases(sort_function, count=3)
        
        assert len(test_cases) == 3
        assert any("sort" in tc.description.lower() for tc in test_cases)
    
    @pytest.mark.asyncio
    @patch('services.function_testing.AsyncSessionLocal')
    async def test_add_test_case(self, mock_session):
        """Test adding a test case to a function."""
        # Mock database session
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        # Mock function
        mock_function = Function(
            id="test-function-id",
            name="test_function",
            test_cases=None
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_function
        mock_session_instance.execute.return_value = mock_result
        
        service = FunctionTestingService()
        test_case = TestCase(
            name="test_basic",
            input_data={'x': 5},
            expected_output=10
        )
        
        result = await service.add_test_case("test-function-id", test_case)
        
        assert result == True
        mock_session_instance.commit.assert_called_once()
        
        # Check that test case was added to function
        assert mock_function.test_cases is not None
        test_cases_data = json.loads(mock_function.test_cases)
        assert len(test_cases_data) == 1
        assert test_cases_data[0]['name'] == "test_basic"
    
    @pytest.mark.asyncio
    @patch('services.function_testing.execute_function_safely')
    async def test_run_single_test_success(self, mock_execute):
        """Test running a single test case successfully."""
        # Mock execution result
        mock_execute.return_value = {
            'success': True,
            'test_results': [{
                'success': True,
                'output': 8,
                'error': None
            }],
            'errors': []
        }
        
        service = FunctionTestingService()
        function = Function(
            name="add_three",
            code="def add_three(x): return x + 3"
        )
        
        test_case = TestCase(
            name="test_add_three",
            input_data={'x': 5},
            expected_output=8
        )
        
        result = await service.run_single_test(function, test_case)
        
        assert result.passed == True
        assert result.output == 8
        assert result.test_name == "test_add_three"
        assert result.execution_time_ms > 0
    
    @pytest.mark.asyncio
    @patch('services.function_testing.execute_function_safely')
    async def test_run_single_test_failure(self, mock_execute):
        """Test running a single test case that fails."""
        # Mock execution result with wrong output
        mock_execute.return_value = {
            'success': True,
            'test_results': [{
                'success': True,
                'output': 10,  # Wrong output
                'error': None
            }],
            'errors': []
        }
        
        service = FunctionTestingService()
        function = Function(
            name="add_three",
            code="def add_three(x): return x + 3"
        )
        
        test_case = TestCase(
            name="test_add_three",
            input_data={'x': 5},
            expected_output=8  # Expected 8 but got 10
        )
        
        result = await service.run_single_test(function, test_case)
        
        assert result.passed == False
        assert result.output == 10
        assert result.expected_output == 8
    
    @pytest.mark.asyncio
    @patch('services.function_testing.execute_function_safely')
    async def test_run_single_test_error_expected(self, mock_execute):
        """Test running a test case that expects an error."""
        # Mock execution result with error
        mock_execute.return_value = {
            'success': True,
            'test_results': [{
                'success': False,
                'output': None,
                'error': {'message': 'ZeroDivisionError: division by zero'}
            }],
            'errors': []
        }
        
        service = FunctionTestingService()
        function = Function(
            name="divide",
            code="def divide(x, y): return x / y"
        )
        
        test_case = TestCase(
            name="test_divide_by_zero",
            input_data={'x': 10, 'y': 0},
            expected_error="ZeroDivisionError"
        )
        
        result = await service.run_single_test(function, test_case)
        
        assert result.passed == True  # Error was expected
        assert "ZeroDivisionError" in result.error
    
    @pytest.mark.asyncio
    @patch('services.function_testing.AsyncSessionLocal')
    @patch('services.function_testing.execute_function_safely')
    async def test_run_all_tests(self, mock_execute, mock_session):
        """Test running all test cases for a function."""
        # Mock database session
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        # Mock function with test cases
        test_cases_data = [
            {
                'name': 'test_1',
                'input_data': {'x': 2},
                'expected_output': 5,
                'timeout': 5,
                'description': 'Test 1'
            },
            {
                'name': 'test_2',
                'input_data': {'x': 3},
                'expected_output': 6,
                'timeout': 5,
                'description': 'Test 2'
            }
        ]
        
        mock_function = Function(
            id="test-function-id",
            name="add_three",
            test_cases=json.dumps(test_cases_data)
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_function
        mock_session_instance.execute.return_value = mock_result
        
        # Mock execution results
        mock_execute.side_effect = [
            {
                'success': True,
                'test_results': [{'success': True, 'output': 5, 'error': None}],
                'errors': []
            },
            {
                'success': True,
                'test_results': [{'success': True, 'output': 6, 'error': None}],
                'errors': []
            }
        ]
        
        service = FunctionTestingService()
        result = await service.run_all_tests("test-function-id")
        
        assert result['total_tests'] == 2
        assert result['passed'] == 2
        assert result['failed'] == 0
        assert result['success_rate'] == 100.0
        assert len(result['test_results']) == 2
    
    @pytest.mark.asyncio
    @patch('services.function_testing.AsyncSessionLocal')
    async def test_get_test_coverage_report(self, mock_session):
        """Test generating test coverage report."""
        # Mock database session
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        # Mock functions
        mock_functions = [
            Function(
                id="func1",
                name="function_with_tests",
                test_cases='[{"name": "test1"}]',
                test_success_count=5,
                test_failure_count=1
            ),
            Function(
                id="func2", 
                name="function_without_tests",
                test_cases=None,
                test_success_count=0,
                test_failure_count=0
            )
        ]
        
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = mock_functions
        mock_session_instance.execute.return_value = mock_result
        
        service = FunctionTestingService()
        report = await service.get_test_coverage_report()
        
        assert report['total_functions'] == 2
        assert report['functions_with_tests'] == 1
        assert report['functions_without_tests'] == 1
        assert report['total_test_cases'] == 1
        assert len(report['functions']) == 2
        
        # Check individual function reports
        func_with_tests = next(f for f in report['functions'] if f['name'] == "function_with_tests")
        assert func_with_tests['has_tests'] == True
        assert func_with_tests['test_count'] == 1
        assert func_with_tests['success_rate'] > 0
        
        func_without_tests = next(f for f in report['functions'] if f['name'] == "function_without_tests")
        assert func_without_tests['has_tests'] == False
        assert func_without_tests['test_count'] == 0