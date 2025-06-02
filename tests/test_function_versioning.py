"""
Tests for function versioning system.
"""

import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, patch

from services.function_manager import FunctionManager
from data.models import Function, FunctionExecution, FunctionDependency


class TestFunctionVersioning:
    """Test cases for function versioning system."""
    
    @pytest.mark.asyncio
    @patch('services.function_manager.AsyncSessionLocal')
    async def test_create_initial_function_version(self, mock_session):
        """Test creating the first version of a function."""
        # Mock database session
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        # Mock successful function creation
        mock_function = Function(id="new-func-id")
        mock_session_instance.add = AsyncMock()
        mock_session_instance.commit = AsyncMock()
        mock_session_instance.refresh = AsyncMock()
        
        # Simulate the refresh setting the ID
        async def mock_refresh(obj):
            obj.id = "new-func-id"
        mock_session_instance.refresh.side_effect = mock_refresh
        
        manager = FunctionManager()
        function_id = await manager.store_function(
            name="calculate_sum",
            code="def calculate_sum(a, b):\n    return a + b",
            description="Calculate sum of two numbers",
            language="python"
        )
        
        assert function_id == "new-func-id"
        mock_session_instance.add.assert_called_once()
        mock_session_instance.commit.assert_called_once()
        
        # Check that the added function has version 1 and is latest
        added_function = mock_session_instance.add.call_args[0][0]
        assert added_function.version == 1  # Default from model
        assert added_function.is_latest_version == True  # Default from model
        assert added_function.base_function_id is None  # Should be None for initial version
    
    def test_function_model_versioning_fields(self):
        """Test that Function model has all versioning fields."""
        function = Function(
            name="test_function",
            description="Test function",
            code="def test(): pass",
            version=2,
            base_function_id="base-id",
            is_latest_version=False,
            parent_version_id="parent-id",
            change_summary="Updated algorithm",
            created_by="user123",
            modified_by="user456"
        )
        
        assert function.version == 2
        assert function.base_function_id == "base-id"
        assert function.is_latest_version == False
        assert function.parent_version_id == "parent-id"
        assert function.change_summary == "Updated algorithm"
        assert function.created_by == "user123"
        assert function.modified_by == "user456"
    
    def test_function_execution_model(self):
        """Test FunctionExecution model for tracking execution history."""
        execution = FunctionExecution(
            function_id="func-id",
            execution_context="test",
            input_data='{"x": 5}',
            output_data='{"result": 10}',
            execution_time_ms=150,
            memory_usage_mb=2.5,
            success=True,
            executed_by="user123"
        )
        
        assert execution.function_id == "func-id"
        assert execution.execution_context == "test"
        assert execution.execution_time_ms == 150
        assert execution.memory_usage_mb == 2.5
        assert execution.success == True
        assert execution.executed_by == "user123"
    
    def test_function_dependency_model(self):
        """Test FunctionDependency model for tracking function relationships."""
        dependency = FunctionDependency(
            function_id="func1",
            depends_on_function_id="func2",
            dependency_type="calls",
            is_active=True
        )
        
        assert dependency.function_id == "func1"
        assert dependency.depends_on_function_id == "func2"
        assert dependency.dependency_type == "calls"
        assert dependency.is_active == True
    
    @pytest.mark.asyncio
    @patch('services.function_manager.AsyncSessionLocal')
    async def test_search_functions_with_versioning(self, mock_session):
        """Test that search respects versioning (only returns latest versions)."""
        # Mock database session
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        # Mock functions with different versions
        mock_functions = [
            Function(
                id="func1-v2",
                name="calculate_sum",
                description="Calculate sum of two numbers",
                version=2,
                is_latest_version=True,
                is_active=True
            ),
            # Old version should not be returned if we filter by is_latest_version
            Function(
                id="func1-v1",
                name="calculate_sum",
                description="Calculate sum of two numbers",
                version=1,
                is_latest_version=False,
                is_active=True
            )
        ]
        
        # Mock only returning the latest version
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [mock_functions[0]]  # Only latest
        mock_session_instance.execute.return_value = mock_result
        
        manager = FunctionManager()
        results = await manager.search_functions("calculate sum")
        
        assert len(results) == 1
        assert results[0].id == "func1-v2"
        assert results[0].version == 2
        assert results[0].is_latest_version == True
    
    def test_function_performance_tracking_fields(self):
        """Test that Function model has performance tracking fields."""
        function = Function(
            name="test_function",
            description="Test function",
            code="def test(): pass",
            execution_count=10,
            success_rate=95.5,
            avg_execution_time_ms=120.5,
            total_execution_time_ms=1205,
            security_score=0.9,
            complexity_score=2.5,
            code_quality_score=0.85
        )
        
        assert function.execution_count == 10
        assert function.success_rate == 95.5
        assert function.avg_execution_time_ms == 120.5
        assert function.total_execution_time_ms == 1205
        assert function.security_score == 0.9
        assert function.complexity_score == 2.5
        assert function.code_quality_score == 0.85
    
    def test_function_testing_fields(self):
        """Test that Function model has testing framework fields."""
        test_cases = [
            {
                "name": "test_basic",
                "input_data": {"x": 5},
                "expected_output": 10
            }
        ]
        
        test_results = {
            "total_tests": 1,
            "passed": 1,
            "failed": 0,
            "success_rate": 100.0
        }
        
        function = Function(
            name="test_function",
            description="Test function",
            code="def test(): pass",
            test_cases=json.dumps(test_cases),
            test_results=json.dumps(test_results),
            last_test_run=datetime.utcnow(),
            test_success_count=1,
            test_failure_count=0
        )
        
        assert function.test_cases is not None
        assert function.test_results is not None
        assert function.last_test_run is not None
        assert function.test_success_count == 1
        assert function.test_failure_count == 0
        
        # Test JSON parsing
        parsed_test_cases = json.loads(function.test_cases)
        assert len(parsed_test_cases) == 1
        assert parsed_test_cases[0]["name"] == "test_basic"
        
        parsed_test_results = json.loads(function.test_results)
        assert parsed_test_results["success_rate"] == 100.0
    
    @pytest.mark.asyncio
    @patch('services.function_manager.AsyncSessionLocal')
    async def test_get_function_by_id_with_versioning(self, mock_session):
        """Test getting a specific function version by ID."""
        # Mock database session
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        # Mock function with version info
        mock_function = Function(
            id="func-v2-id",
            name="calculate_sum",
            description="Calculate sum of two numbers",
            version=2,
            base_function_id="func-base-id",
            is_latest_version=True,
            parent_version_id="func-v1-id",
            change_summary="Improved performance"
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_function
        mock_session_instance.execute.return_value = mock_result
        
        manager = FunctionManager()
        result = await manager.get_function_by_id("func-v2-id")
        
        assert result is not None
        assert result.id == "func-v2-id"
        assert result.version == 2
        assert result.is_latest_version == True
        assert result.change_summary == "Improved performance"
    
    def test_function_repr_includes_version(self):
        """Test that Function __repr__ includes version information."""
        function = Function(
            name="test_function",
            version=3,
            language="python"
        )
        
        repr_str = repr(function)
        assert "test_function" in repr_str
        assert "version=3" in repr_str
        assert "python" in repr_str
    
    def test_function_execution_repr(self):
        """Test FunctionExecution __repr__ method."""
        execution = FunctionExecution(
            function_id="func-id",
            success=True
        )
        
        repr_str = repr(execution)
        assert "func-id" in repr_str
        assert "success=True" in repr_str
    
    def test_function_dependency_repr(self):
        """Test FunctionDependency __repr__ method."""
        dependency = FunctionDependency(
            function_id="func1",
            depends_on_function_id="func2"
        )
        
        repr_str = repr(dependency)
        assert "func1" in repr_str
        assert "func2" in repr_str