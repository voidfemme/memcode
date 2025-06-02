"""
Secure function execution module with sandboxing and safety features.
"""

import ast
import sys
import io
import traceback
import signal
import resource
import multiprocessing
import asyncio
from typing import Any, Dict, Optional, Tuple, List
from contextlib import contextmanager, redirect_stdout, redirect_stderr
from datetime import datetime
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Whitelist of allowed modules and builtins
ALLOWED_MODULES = {
    'math', 'random', 'datetime', 'collections', 'itertools', 
    'functools', 'operator', 'string', 're', 'json', 'uuid',
    'typing', 'dataclasses', 'enum', 'decimal', 'fractions',
    'statistics', 'heapq', 'bisect', 'copy', 'deepcopy'
}

ALLOWED_BUILTINS = {
    'abs', 'all', 'any', 'bin', 'bool', 'chr', 'dict', 'dir',
    'divmod', 'enumerate', 'filter', 'float', 'format', 'frozenset',
    'getattr', 'hasattr', 'hash', 'hex', 'id', 'int', 'isinstance',
    'issubclass', 'iter', 'len', 'list', 'map', 'max', 'min',
    'next', 'oct', 'ord', 'pow', 'range', 'repr', 'reversed',
    'round', 'set', 'setattr', 'slice', 'sorted', 'str', 'sum',
    'tuple', 'type', 'zip', 'print'
}

# Forbidden operations
FORBIDDEN_NODES = {
    ast.Import, ast.ImportFrom, ast.Exec, ast.Eval, ast.Call
}

class SecurityError(Exception):
    """Raised when code violates security constraints."""
    pass

class ExecutionTimeoutError(Exception):
    """Raised when code execution times out."""
    pass

class ExecutionMemoryError(Exception):
    """Raised when code exceeds memory limits."""
    pass

class CodeSecurityAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze code for security violations."""
    
    def __init__(self):
        self.errors = []
        self.imports = []
        self.function_calls = []
        
    def visit_Import(self, node):
        """Check import statements."""
        for alias in node.names:
            module_name = alias.name.split('.')[0]
            self.imports.append(module_name)
            if module_name not in ALLOWED_MODULES:
                self.errors.append(f"Forbidden import: {module_name}")
        self.generic_visit(node)
        
    def visit_ImportFrom(self, node):
        """Check from...import statements."""
        if node.module:
            module_name = node.module.split('.')[0]
            self.imports.append(module_name)
            if module_name not in ALLOWED_MODULES:
                self.errors.append(f"Forbidden import from: {module_name}")
        self.generic_visit(node)
        
    def visit_Call(self, node):
        """Check function calls for dangerous operations."""
        # Check for dangerous builtins
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            self.function_calls.append(func_name)
            
            dangerous_funcs = {'exec', 'eval', 'compile', '__import__', 
                             'open', 'file', 'input', 'raw_input'}
            if func_name in dangerous_funcs:
                self.errors.append(f"Forbidden function call: {func_name}")
                
        # Check for attribute access that might be dangerous
        elif isinstance(node.func, ast.Attribute):
            attr_name = node.func.attr
            dangerous_attrs = {'__import__', '__builtins__', '__globals__', 
                             '__locals__', '__code__', '__closure__'}
            if attr_name in dangerous_attrs:
                self.errors.append(f"Forbidden attribute access: {attr_name}")
                
        self.generic_visit(node)
        
    def visit_Attribute(self, node):
        """Check attribute access."""
        if isinstance(node.attr, str):
            dangerous_attrs = {'__class__', '__bases__', '__subclasses__',
                             '__mro__', '__dict__', '__code__', '__globals__'}
            if node.attr in dangerous_attrs:
                self.errors.append(f"Forbidden attribute: {node.attr}")
        self.generic_visit(node)

class SecureExecutor:
    """Secure code execution with sandboxing and resource limits."""
    
    def __init__(self, timeout: int = 5, memory_limit_mb: int = 64):
        self.timeout = timeout
        self.memory_limit = memory_limit_mb * 1024 * 1024  # Convert to bytes
        
    def analyze_code_security(self, code: str) -> Tuple[bool, List[str]]:
        """Analyze code for security violations."""
        try:
            tree = ast.parse(code)
            analyzer = CodeSecurityAnalyzer()
            analyzer.visit(tree)
            
            is_safe = len(analyzer.errors) == 0
            return is_safe, analyzer.errors
            
        except SyntaxError as e:
            return False, [f"Syntax error: {e}"]
        except Exception as e:
            return False, [f"Analysis error: {e}"]
    
    @contextmanager
    def resource_limits(self):
        """Set resource limits for execution."""
        old_limits = {}
        
        try:
            # Set memory limit
            old_limits['memory'] = resource.getrlimit(resource.RLIMIT_AS)
            resource.setrlimit(resource.RLIMIT_AS, (self.memory_limit, self.memory_limit))
            
            # Set CPU time limit
            old_limits['cpu'] = resource.getrlimit(resource.RLIMIT_CPU)
            resource.setrlimit(resource.RLIMIT_CPU, (self.timeout, self.timeout))
            
            yield
            
        finally:
            # Restore original limits
            for limit_type, old_limit in old_limits.items():
                if limit_type == 'memory':
                    resource.setrlimit(resource.RLIMIT_AS, old_limit)
                elif limit_type == 'cpu':
                    resource.setrlimit(resource.RLIMIT_CPU, old_limit)
    
    def create_secure_globals(self) -> Dict[str, Any]:
        """Create a restricted global namespace."""
        secure_builtins = {}
        
        # Add allowed builtins
        for builtin_name in ALLOWED_BUILTINS:
            if hasattr(__builtins__, builtin_name):
                secure_builtins[builtin_name] = getattr(__builtins__, builtin_name)
            elif isinstance(__builtins__, dict) and builtin_name in __builtins__:
                secure_builtins[builtin_name] = __builtins__[builtin_name]
        
        # Create secure namespace
        secure_globals = {
            '__builtins__': secure_builtins,
            '__name__': '__main__',
            '__doc__': None,
        }
        
        return secure_globals
    
    def execute_with_timeout(self, code: str, globals_dict: Dict, locals_dict: Dict) -> Any:
        """Execute code with timeout using multiprocessing."""
        def target_function(code, globals_dict, locals_dict, result_queue, error_queue):
            try:
                with self.resource_limits():
                    # Redirect stdout and stderr
                    stdout_capture = io.StringIO()
                    stderr_capture = io.StringIO()
                    
                    with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                        exec(code, globals_dict, locals_dict)
                    
                    # Get captured output
                    stdout_output = stdout_capture.getvalue()
                    stderr_output = stderr_capture.getvalue()
                    
                    # Prepare result
                    result = {
                        'locals': {k: v for k, v in locals_dict.items() 
                                 if not k.startswith('__')},
                        'stdout': stdout_output,
                        'stderr': stderr_output,
                        'success': True
                    }
                    
                    result_queue.put(result)
                    
            except Exception as e:
                error_info = {
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'traceback': traceback.format_exc(),
                    'success': False
                }
                error_queue.put(error_info)
        
        # Create queues for communication
        result_queue = multiprocessing.Queue()
        error_queue = multiprocessing.Queue()
        
        # Start process
        process = multiprocessing.Process(
            target=target_function,
            args=(code, globals_dict, locals_dict, result_queue, error_queue)
        )
        
        process.start()
        process.join(timeout=self.timeout)
        
        if process.is_alive():
            process.terminate()
            process.join()
            raise ExecutionTimeoutError(f"Code execution timed out after {self.timeout} seconds")
        
        # Check for errors
        if not error_queue.empty():
            error_info = error_queue.get()
            if error_info['error_type'] == 'MemoryError':
                raise ExecutionMemoryError("Code exceeded memory limit")
            else:
                raise RuntimeError(f"{error_info['error_type']}: {error_info['error_message']}")
        
        # Get result
        if not result_queue.empty():
            return result_queue.get()
        else:
            raise RuntimeError("No result returned from execution")
    
    async def execute_function_safely(
        self, 
        code: str, 
        function_name: str = None,
        test_inputs: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Safely execute a function with comprehensive error handling.
        
        Args:
            code: The function code to execute
            function_name: Name of the function to call (if None, just exec the code)
            test_inputs: List of test input dictionaries to run the function with
            
        Returns:
            Dictionary with execution results, metrics, and any errors
        """
        execution_start = datetime.utcnow()
        result = {
            'success': False,
            'function_name': function_name,
            'execution_time_ms': 0,
            'memory_peak_mb': 0,
            'stdout': '',
            'stderr': '',
            'return_value': None,
            'test_results': [],
            'errors': [],
            'security_warnings': []
        }
        
        try:
            logger.info(f"Starting secure execution of function: {function_name}")
            
            # 1. Security Analysis
            is_safe, security_errors = self.analyze_code_security(code)
            if not is_safe:
                result['errors'] = security_errors
                result['security_warnings'] = security_errors
                logger.warning(f"Security violations found: {security_errors}")
                return result
            
            # 2. Create secure execution environment
            secure_globals = self.create_secure_globals()
            secure_locals = {}
            
            # 3. Execute the function definition
            exec_result = self.execute_with_timeout(code, secure_globals, secure_locals)
            
            result['stdout'] = exec_result['stdout']
            result['stderr'] = exec_result['stderr']
            
            # 4. If function_name provided, test the function
            if function_name and function_name in secure_locals:
                func = secure_locals[function_name]
                
                # Test with provided inputs
                if test_inputs:
                    for i, test_input in enumerate(test_inputs):
                        test_result = {
                            'input': test_input,
                            'success': False,
                            'output': None,
                            'error': None
                        }
                        
                        try:
                            # Call function with test input
                            if isinstance(test_input, dict):
                                output = func(**test_input)
                            elif isinstance(test_input, (list, tuple)):
                                output = func(*test_input)
                            else:
                                output = func(test_input)
                            
                            test_result['output'] = output
                            test_result['success'] = True
                            
                        except Exception as e:
                            test_result['error'] = {
                                'type': type(e).__name__,
                                'message': str(e)
                            }
                        
                        result['test_results'].append(test_result)
                
                # If no test inputs, try to call function with no args
                elif function_name in secure_locals:
                    try:
                        output = func()
                        result['return_value'] = output
                    except TypeError:
                        # Function requires arguments
                        result['return_value'] = f"Function {function_name} requires arguments"
                    except Exception as e:
                        result['errors'].append(f"Error calling {function_name}: {e}")
            
            result['success'] = True
            logger.info(f"Function execution completed successfully")
            
        except ExecutionTimeoutError as e:
            result['errors'].append(str(e))
            logger.error(f"Execution timeout: {e}")
            
        except ExecutionMemoryError as e:
            result['errors'].append(str(e))
            logger.error(f"Memory limit exceeded: {e}")
            
        except Exception as e:
            result['errors'].append(f"Execution error: {type(e).__name__}: {str(e)}")
            logger.error(f"Unexpected execution error: {e}")
            
        finally:
            # Calculate execution time
            execution_end = datetime.utcnow()
            result['execution_time_ms'] = int((execution_end - execution_start).total_seconds() * 1000)
        
        return result

# Global executor instance
executor = SecureExecutor()

async def execute_function_safely(
    code: str, 
    function_name: str = None,
    test_inputs: List[Dict] = None,
    timeout: int = 5,
    memory_limit_mb: int = 64
) -> Dict[str, Any]:
    """
    Public interface for safe function execution.
    
    Args:
        code: The function code to execute
        function_name: Name of the function to call
        test_inputs: List of test inputs to validate the function
        timeout: Maximum execution time in seconds
        memory_limit_mb: Maximum memory usage in MB
        
    Returns:
        Execution result dictionary
    """
    # Create executor with custom limits if needed
    if timeout != 5 or memory_limit_mb != 64:
        custom_executor = SecureExecutor(timeout=timeout, memory_limit_mb=memory_limit_mb)
        return await custom_executor.execute_function_safely(code, function_name, test_inputs)
    
    # Use global executor
    return await executor.execute_function_safely(code, function_name, test_inputs)