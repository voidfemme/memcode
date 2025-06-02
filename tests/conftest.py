"""
Test configuration and fixtures for MemCode tests.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock
from datetime import datetime

@pytest.fixture
def mock_db_session():
    """Mock database session for testing."""
    return AsyncMock()

@pytest.fixture
def sample_function_data():
    """Sample function data for testing."""
    return {
        "name": "add_numbers",
        "description": "Add two numbers together",
        "code": "def add_numbers(a, b):\n    return a + b",
        "language": "python"
    }

@pytest.fixture
def sample_function_with_versioning():
    """Sample function with versioning data."""
    return {
        "name": "calculate_area",
        "description": "Calculate the area of a circle",
        "code": "import math\ndef calculate_area(radius):\n    return math.pi * radius ** 2",
        "language": "python",
        "version": 1,
        "is_latest_version": True,
        "created_by": "test_user",
        "test_cases": '[{"name": "test_basic", "input_data": {"radius": 5}, "expected_output": 78.54}]'
    }

@pytest.fixture
def sample_test_case():
    """Sample test case data."""
    return {
        "name": "test_addition",
        "input_data": {"a": 2, "b": 3},
        "expected_output": 5,
        "description": "Test basic addition functionality"
    }

@pytest.fixture
def sample_execution_result():
    """Sample function execution result."""
    return {
        "success": True,
        "function_name": "add_numbers",
        "execution_time_ms": 10,
        "stdout": "",
        "stderr": "",
        "return_value": 5,
        "test_results": [
            {
                "input": {"a": 2, "b": 3},
                "success": True,
                "output": 5,
                "error": None
            }
        ],
        "errors": [],
        "security_warnings": []
    }

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()