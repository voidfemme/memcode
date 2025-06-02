"""
Function testing framework with automated test execution and validation.
"""

import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

from core.database import AsyncSessionLocal
from data.models import Function, FunctionExecution
from tools.execution import execute_function_safely
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)

class TestCase:
    """Represents a single test case for a function."""
    
    def __init__(
        self, 
        name: str,
        input_data: Any,
        expected_output: Any = None,
        expected_error: str = None,
        timeout: int = 5,
        description: str = ""
    ):
        self.name = name
        self.input_data = input_data
        self.expected_output = expected_output
        self.expected_error = expected_error
        self.timeout = timeout
        self.description = description
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert test case to dictionary for storage."""
        return {
            'name': self.name,
            'input_data': self.input_data,
            'expected_output': self.expected_output,
            'expected_error': self.expected_error,
            'timeout': self.timeout,
            'description': self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestCase':
        """Create test case from dictionary."""
        return cls(
            name=data.get('name', ''),
            input_data=data.get('input_data'),
            expected_output=data.get('expected_output'),
            expected_error=data.get('expected_error'),
            timeout=data.get('timeout', 5),
            description=data.get('description', '')
        )

class TestResult:
    """Represents the result of executing a test case."""
    
    def __init__(
        self,
        test_name: str,
        passed: bool,
        execution_time_ms: int,
        output: Any = None,
        error: str = None,
        expected_output: Any = None,
        details: str = ""
    ):
        self.test_name = test_name
        self.passed = passed
        self.execution_time_ms = execution_time_ms
        self.output = output
        self.error = error
        self.expected_output = expected_output
        self.details = details
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert test result to dictionary for storage."""
        return {
            'test_name': self.test_name,
            'passed': self.passed,
            'execution_time_ms': self.execution_time_ms,
            'output': self.output,
            'error': self.error,
            'expected_output': self.expected_output,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }

class FunctionTestingService:
    """Service for managing and executing function tests."""
    
    def __init__(self):
        self.test_history = {}
    
    async def add_test_case(
        self,
        function_id: str,
        test_case: TestCase
    ) -> bool:
        """Add a test case to a function."""
        async with AsyncSessionLocal() as session:
            try:
                stmt = select(Function).where(Function.id == function_id)
                result = await session.execute(stmt)
                function = result.scalar_one_or_none()
                
                if not function:
                    logger.error(f"Function {function_id} not found")
                    return False
                
                # Get existing test cases
                existing_tests = []
                if function.test_cases:
                    try:
                        existing_tests = json.loads(function.test_cases)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid test cases JSON for function {function_id}")
                        existing_tests = []
                
                # Add new test case
                existing_tests.append(test_case.to_dict())
                function.test_cases = json.dumps(existing_tests)
                
                await session.commit()
                logger.info(f"Added test case '{test_case.name}' to function {function_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error adding test case: {e}")
                await session.rollback()
                return False
    
    async def run_single_test(
        self,
        function: Function,
        test_case: TestCase
    ) -> TestResult:
        """Execute a single test case against a function."""
        start_time = datetime.utcnow()
        
        try:
            # Execute the function with test input
            execution_result = await execute_function_safely(
                code=function.code,
                function_name=function.name,
                test_inputs=[test_case.input_data],
                timeout=test_case.timeout
            )
            
            end_time = datetime.utcnow()
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Check if execution was successful
            if not execution_result['success']:
                return TestResult(
                    test_name=test_case.name,
                    passed=False,
                    execution_time_ms=execution_time_ms,
                    error='; '.join(execution_result['errors']),
                    expected_output=test_case.expected_output,
                    details="Function execution failed"
                )
            
            # Get the actual output
            actual_output = None
            if execution_result['test_results']:
                test_result = execution_result['test_results'][0]
                if test_result['success']:
                    actual_output = test_result['output']
                else:
                    error_msg = test_result['error']['message'] if test_result['error'] else "Unknown error"
                    
                    # Check if we expected an error
                    if test_case.expected_error:
                        passed = test_case.expected_error.lower() in error_msg.lower()
                        return TestResult(
                            test_name=test_case.name,
                            passed=passed,
                            execution_time_ms=execution_time_ms,
                            error=error_msg,
                            expected_output=test_case.expected_error,
                            details="Expected error occurred" if passed else "Different error than expected"
                        )
                    else:
                        return TestResult(
                            test_name=test_case.name,
                            passed=False,
                            execution_time_ms=execution_time_ms,
                            error=error_msg,
                            expected_output=test_case.expected_output,
                            details="Unexpected error during execution"
                        )
            
            # Compare output with expected result
            if test_case.expected_error:
                # We expected an error but got a result
                return TestResult(
                    test_name=test_case.name,
                    passed=False,
                    execution_time_ms=execution_time_ms,
                    output=actual_output,
                    expected_output=test_case.expected_error,
                    details="Expected error but function executed successfully"
                )
            
            # Compare actual vs expected output
            passed = self._compare_outputs(actual_output, test_case.expected_output)
            
            return TestResult(
                test_name=test_case.name,
                passed=passed,
                execution_time_ms=execution_time_ms,
                output=actual_output,
                expected_output=test_case.expected_output,
                details="Output matches expected" if passed else "Output differs from expected"
            )
            
        except Exception as e:
            end_time = datetime.utcnow()
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return TestResult(
                test_name=test_case.name,
                passed=False,
                execution_time_ms=execution_time_ms,
                error=str(e),
                expected_output=test_case.expected_output,
                details="Exception during test execution"
            )
    
    def _compare_outputs(self, actual: Any, expected: Any) -> bool:
        """Compare actual output with expected output."""
        if expected is None:
            # If no expected output specified, just check if execution was successful
            return True
        
        try:
            # Handle different types of comparisons
            if isinstance(expected, (int, float, str, bool)):
                return actual == expected
            elif isinstance(expected, (list, tuple)):
                if not isinstance(actual, (list, tuple)):
                    return False
                if len(actual) != len(expected):
                    return False
                return all(a == e for a, e in zip(actual, expected))
            elif isinstance(expected, dict):
                if not isinstance(actual, dict):
                    return False
                return actual == expected
            else:
                # For complex objects, use string comparison
                return str(actual) == str(expected)
                
        except Exception as e:
            logger.warning(f"Error comparing outputs: {e}")
            return False
    
    async def run_all_tests(
        self,
        function_id: str,
        save_results: bool = True
    ) -> Dict[str, Any]:
        """Run all test cases for a function."""
        async with AsyncSessionLocal() as session:
            try:
                stmt = select(Function).where(Function.id == function_id)
                result = await session.execute(stmt)
                function = result.scalar_one_or_none()
                
                if not function:
                    return {'error': f'Function {function_id} not found'}
                
                if not function.test_cases:
                    return {'error': 'No test cases defined for this function'}
                
                # Parse test cases
                try:
                    test_cases_data = json.loads(function.test_cases)
                    test_cases = [TestCase.from_dict(tc) for tc in test_cases_data]
                except json.JSONDecodeError:
                    return {'error': 'Invalid test cases format'}
                
                # Run all tests
                test_results = []
                passed_count = 0
                total_execution_time = 0
                
                for test_case in test_cases:
                    result = await self.run_single_test(function, test_case)
                    test_results.append(result)
                    
                    if result.passed:
                        passed_count += 1
                    
                    total_execution_time += result.execution_time_ms
                
                # Calculate metrics
                total_tests = len(test_cases)
                success_rate = (passed_count / total_tests) * 100 if total_tests > 0 else 0
                avg_execution_time = total_execution_time / total_tests if total_tests > 0 else 0
                
                # Prepare summary
                summary = {
                    'function_id': function_id,
                    'function_name': function.name,
                    'total_tests': total_tests,
                    'passed': passed_count,
                    'failed': total_tests - passed_count,
                    'success_rate': success_rate,
                    'total_execution_time_ms': total_execution_time,
                    'avg_execution_time_ms': avg_execution_time,
                    'test_results': [tr.to_dict() for tr in test_results],
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                # Save results to database if requested
                if save_results:
                    await self._save_test_results(function, summary, session)
                
                return summary
                
            except Exception as e:
                logger.error(f"Error running tests for function {function_id}: {e}")
                return {'error': str(e)}
    
    async def _save_test_results(
        self,
        function: Function,
        summary: Dict[str, Any],
        session
    ):
        """Save test results to the database."""
        try:
            # Update function test metrics
            function.test_results = json.dumps(summary)
            function.last_test_run = datetime.utcnow()
            function.test_success_count = summary['passed']
            function.test_failure_count = summary['failed']
            
            # Update performance metrics
            if summary['success_rate'] == 100:
                # Only update success rate if all tests pass
                function.success_rate = summary['success_rate']
            
            # Update execution time metrics
            if summary['avg_execution_time_ms'] > 0:
                if function.avg_execution_time_ms:
                    # Weighted average with previous results
                    function.avg_execution_time_ms = (
                        function.avg_execution_time_ms * 0.7 + 
                        summary['avg_execution_time_ms'] * 0.3
                    )
                else:
                    function.avg_execution_time_ms = summary['avg_execution_time_ms']
            
            # Save individual test executions
            for test_result_data in summary['test_results']:
                execution = FunctionExecution(
                    function_id=function.id,
                    execution_context='test',
                    input_data=json.dumps(test_result_data.get('input_data')),
                    output_data=json.dumps(test_result_data.get('output')),
                    error_message=test_result_data.get('error'),
                    execution_time_ms=test_result_data['execution_time_ms'],
                    success=test_result_data['passed'],
                    executed_at=datetime.utcnow()
                )
                session.add(execution)
            
            await session.commit()
            logger.info(f"Saved test results for function {function.id}")
            
        except Exception as e:
            logger.error(f"Error saving test results: {e}")
            await session.rollback()
    
    async def generate_test_cases(
        self,
        function: Function,
        count: int = 3
    ) -> List[TestCase]:
        """Generate basic test cases for a function based on its signature."""
        test_cases = []
        
        try:
            # Basic test case generation based on function analysis
            # This is a simple implementation - could be enhanced with LLM generation
            
            # Extract function name and basic info
            func_name = function.name.lower()
            description = function.description.lower()
            
            # Generate test cases based on common patterns
            if 'add' in func_name or 'sum' in func_name:
                test_cases.extend([
                    TestCase("basic_addition", [2, 3], 5, description="Basic addition test"),
                    TestCase("zero_addition", [0, 5], 5, description="Addition with zero"),
                    TestCase("negative_addition", [-2, 3], 1, description="Addition with negative")
                ])
            
            elif 'multiply' in func_name or 'mult' in func_name:
                test_cases.extend([
                    TestCase("basic_multiplication", [2, 3], 6, description="Basic multiplication"),
                    TestCase("zero_multiplication", [0, 5], 0, description="Multiplication by zero"),
                    TestCase("one_multiplication", [1, 7], 7, description="Multiplication by one")
                ])
            
            elif 'sort' in func_name or 'arrange' in func_name:
                test_cases.extend([
                    TestCase("sort_numbers", [[3, 1, 4, 1, 5]], [1, 1, 3, 4, 5], description="Sort number list"),
                    TestCase("sort_empty", [[]], [], description="Sort empty list"),
                    TestCase("sort_single", [[42]], [42], description="Sort single element")
                ])
            
            elif 'reverse' in func_name:
                test_cases.extend([
                    TestCase("reverse_string", ["hello"], "olleh", description="Reverse string"),
                    TestCase("reverse_list", [[1, 2, 3]], [3, 2, 1], description="Reverse list"),
                    TestCase("reverse_empty", [""], "", description="Reverse empty string")
                ])
            
            else:
                # Generic test cases
                test_cases.extend([
                    TestCase("basic_test", None, description="Basic execution test"),
                    TestCase("empty_input", [], description="Empty input test"),
                    TestCase("none_input", None, description="None input test")
                ])
            
            return test_cases[:count]
            
        except Exception as e:
            logger.error(f"Error generating test cases: {e}")
            return []
    
    async def get_test_coverage_report(
        self,
        function_id: str = None
    ) -> Dict[str, Any]:
        """Generate a test coverage report for functions."""
        async with AsyncSessionLocal() as session:
            try:
                if function_id:
                    stmt = select(Function).where(Function.id == function_id)
                else:
                    stmt = select(Function).where(Function.is_active == True)
                
                result = await session.execute(stmt)
                functions = result.scalars().all()
                
                report = {
                    'total_functions': len(functions),
                    'functions_with_tests': 0,
                    'functions_without_tests': 0,
                    'total_test_cases': 0,
                    'avg_success_rate': 0,
                    'functions': []
                }
                
                success_rates = []
                
                for func in functions:
                    func_report = {
                        'id': func.id,
                        'name': func.name,
                        'has_tests': bool(func.test_cases),
                        'test_count': 0,
                        'last_test_run': func.last_test_run.isoformat() if func.last_test_run else None,
                        'success_count': func.test_success_count,
                        'failure_count': func.test_failure_count,
                        'success_rate': 0
                    }
                    
                    if func.test_cases:
                        try:
                            test_cases = json.loads(func.test_cases)
                            func_report['test_count'] = len(test_cases)
                            report['total_test_cases'] += len(test_cases)
                            report['functions_with_tests'] += 1
                        except:
                            report['functions_without_tests'] += 1
                        
                        # Calculate success rate
                        total_tests = func.test_success_count + func.test_failure_count
                        if total_tests > 0:
                            success_rate = (func.test_success_count / total_tests) * 100
                            func_report['success_rate'] = success_rate
                            success_rates.append(success_rate)
                    else:
                        report['functions_without_tests'] += 1
                    
                    report['functions'].append(func_report)
                
                # Calculate average success rate
                if success_rates:
                    report['avg_success_rate'] = sum(success_rates) / len(success_rates)
                
                return report
                
            except Exception as e:
                logger.error(f"Error generating coverage report: {e}")
                return {'error': str(e)}

# Global testing service instance
testing_service = FunctionTestingService()