"""
Tests for enhanced retrieval service with semantic search.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock

from services.retrieval_service import RetrievalService, retrieval_service
from data.models import Function


class TestEnhancedRetrieval:
    """Test cases for enhanced retrieval service."""
    
    def test_retrieval_service_initialization(self):
        """Test that retrieval service initializes correctly."""
        service = RetrievalService()
        
        # Should have embedding model or gracefully fail
        assert hasattr(service, 'embedding_model')
        assert hasattr(service, 'tfidf_vectorizer')
    
    @patch('services.retrieval_service.SentenceTransformer')
    def test_embedding_generation(self, mock_sentence_transformer):
        """Test embedding generation functionality."""
        # Mock the sentence transformer
        mock_model = MagicMock()
        mock_model.encode.return_value = [[0.1, 0.2, 0.3, 0.4]]
        mock_sentence_transformer.return_value = mock_model
        
        service = RetrievalService()
        service.embedding_model = mock_model
        
        embedding = service.generate_embedding("test function description")
        
        assert embedding == [0.1, 0.2, 0.3, 0.4]
        mock_model.encode.assert_called_once_with(["test function description"])
    
    def test_semantic_similarity_calculation(self):
        """Test cosine similarity calculation."""
        service = RetrievalService()
        
        # Test identical vectors (should be 1.0)
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        similarity = service.calculate_semantic_similarity(vec1, vec2)
        assert abs(similarity - 1.0) < 0.01
        
        # Test orthogonal vectors (should be 0.0)
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = service.calculate_semantic_similarity(vec1, vec2)
        assert abs(similarity - 0.0) < 0.01
        
        # Test opposite vectors (should be -1.0)
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        similarity = service.calculate_semantic_similarity(vec1, vec2)
        assert abs(similarity - (-1.0)) < 0.01
    
    @pytest.mark.asyncio
    @patch('services.retrieval_service.AsyncSessionLocal')
    async def test_keyword_search(self, mock_session):
        """Test keyword-based search functionality."""
        # Mock database session
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        # Mock functions
        mock_functions = [
            Function(
                id="func1",
                name="sort_list",
                description="Sort a list of numbers",
                language="python",
                is_active=True
            ),
            Function(
                id="func2",
                name="bubble_sort",
                description="Implement bubble sort algorithm",
                language="python",
                is_active=True
            )
        ]
        
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = mock_functions
        mock_session_instance.execute.return_value = mock_result
        
        service = RetrievalService()
        results = await service.keyword_search("sort", limit=5)
        
        assert len(results) == 2
        assert all(result['match_type'] == 'keyword' for result in results)
        assert all(result['similarity'] == 1.0 for result in results)
        
        # Check that functions are included
        function_names = [result['function'].name for result in results]
        assert "sort_list" in function_names
        assert "bubble_sort" in function_names
    
    @pytest.mark.asyncio
    @patch('services.retrieval_service.AsyncSessionLocal')
    async def test_semantic_search_without_model(self, mock_session):
        """Test semantic search fallback when model is not available."""
        service = RetrievalService()
        service.embedding_model = None  # Simulate no model available
        
        # Mock the keyword search method
        service.keyword_search = AsyncMock(return_value=[{'match_type': 'keyword'}])
        
        results = await service.semantic_search("test query")
        
        # Should fall back to keyword search
        service.keyword_search.assert_called_once_with("test query", 10, None)
        assert results == [{'match_type': 'keyword'}]
    
    @pytest.mark.asyncio
    @patch('services.retrieval_service.AsyncSessionLocal')
    async def test_semantic_search_with_embeddings(self, mock_session):
        """Test semantic search with embeddings."""
        # Mock database session
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        # Mock functions with embeddings
        mock_functions = [
            Function(
                id="func1",
                name="calculate_area",
                description="Calculate circle area",
                description_embedding=json.dumps([0.9, 0.1, 0.0]),
                is_active=True
            ),
            Function(
                id="func2",
                name="compute_volume",
                description="Compute sphere volume",
                description_embedding=json.dumps([0.8, 0.2, 0.1]),
                is_active=True
            )
        ]
        
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = mock_functions
        mock_session_instance.execute.return_value = mock_result
        
        service = RetrievalService()
        # Mock embedding generation
        service.generate_embedding = MagicMock(return_value=[0.95, 0.05, 0.0])
        
        results = await service.semantic_search("area calculation", min_similarity=0.5)
        
        assert len(results) <= 2
        assert all(result['match_type'] == 'semantic' for result in results)
        assert all(result['similarity'] >= 0.5 for result in results)
        
        # Results should be sorted by similarity
        if len(results) > 1:
            assert results[0]['similarity'] >= results[1]['similarity']
    
    @pytest.mark.asyncio
    async def test_function_categorization(self):
        """Test automatic function categorization."""
        service = RetrievalService()
        
        # Test Python function
        python_func = Function(
            name="sort_numbers",
            description="Sort a list of numbers",
            code="def sort_numbers(lst):\n    return sorted(lst)"
        )
        categories = await service.categorize_function(python_func)
        assert 'python' in categories
        assert 'algorithms' in categories
        
        # Test async function
        async_func = Function(
            name="fetch_data",
            description="Fetch data from API",
            code="async def fetch_data():\n    await asyncio.sleep(1)\n    return data"
        )
        categories = await service.categorize_function(async_func)
        assert 'python' in categories
        assert 'async' in categories
        
        # Test data science function
        data_func = Function(
            name="analyze_data",
            description="Analyze data using pandas",
            code="import pandas as pd\ndef analyze_data(df):\n    return df.describe()"
        )
        categories = await service.categorize_function(data_func)
        assert 'python' in categories
        assert 'data-science' in categories
        
        # Test math function
        math_func = Function(
            name="calculate_area",
            description="Calculate the area of a circle",
            code="import math\ndef calculate_area(radius):\n    return math.pi * radius ** 2"
        )
        categories = await service.categorize_function(math_func)
        assert 'python' in categories
        assert 'math' in categories
    
    @pytest.mark.asyncio
    @patch('services.retrieval_service.AsyncSessionLocal')
    async def test_hybrid_search(self, mock_session):
        """Test hybrid search combining semantic and keyword search."""
        service = RetrievalService()
        
        # Mock both search methods
        semantic_results = [
            {'function': Function(id="func1", name="semantic_match"), 'similarity': 0.8, 'match_type': 'semantic'}
        ]
        keyword_results = [
            {'function': Function(id="func2", name="keyword_match"), 'similarity': 1.0, 'match_type': 'keyword'}
        ]
        
        service.semantic_search = AsyncMock(return_value=semantic_results)
        service.keyword_search = AsyncMock(return_value=keyword_results)
        
        results = await service.hybrid_search("test query", limit=5)
        
        assert len(results) <= 2
        # Should have combined results with scores
        assert all('score' in result for result in results)
        assert all('match_types' in result for result in results)
    
    @pytest.mark.asyncio
    @patch('services.retrieval_service.AsyncSessionLocal')
    async def test_function_recommendations(self, mock_session):
        """Test function recommendation system."""
        # Mock database session
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        # Mock reference function
        ref_function = Function(
            id="ref_func",
            name="sort_list",
            description="Sort a list",
            language="python",
            description_embedding=json.dumps([0.5, 0.5, 0.0])
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = ref_function
        mock_session_instance.execute.return_value = mock_result
        
        service = RetrievalService()
        # Mock semantic search for recommendations
        service.semantic_search = AsyncMock(return_value=[
            {'function': Function(id="rec1", name="bubble_sort"), 'similarity': 0.9}
        ])
        
        recommendations = await service.get_function_recommendations("ref_func", limit=3)
        
        assert len(recommendations) <= 3
        service.semantic_search.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('services.retrieval_service.AsyncSessionLocal')
    async def test_update_all_embeddings(self, mock_session):
        """Test bulk embedding update functionality."""
        # Mock database session
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        # Mock functions without embeddings
        mock_functions = [
            Function(
                id="func1",
                name="test_function_1",
                description="Test function 1",
                description_embedding=None,
                tags='["test", "utility"]',
                is_active=True
            ),
            Function(
                id="func2",
                name="test_function_2", 
                description="Test function 2",
                description_embedding=None,
                tags=None,
                is_active=True
            )
        ]
        
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = mock_functions
        mock_session_instance.execute.return_value = mock_result
        
        service = RetrievalService()
        # Mock embedding generation
        service.generate_embedding = MagicMock(return_value=[0.1, 0.2, 0.3])
        
        result = await service.update_all_embeddings()
        
        assert result['updated'] == 2
        assert result['failed'] == 0
        
        # Check that embeddings were added
        for func in mock_functions:
            assert func.description_embedding is not None
            embedding_data = json.loads(func.description_embedding)
            assert embedding_data == [0.1, 0.2, 0.3]
        
        mock_session_instance.commit.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('services.retrieval_service.AsyncSessionLocal')
    async def test_get_functions_by_categories(self, mock_session):
        """Test getting functions by category."""
        # Mock database session
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        # Mock functions with tags
        mock_functions = [
            Function(
                id="func1",
                name="math_function",
                tags='["math", "calculation"]',
                is_active=True
            ),
            Function(
                id="func2",
                name="data_function",
                tags='["data-science", "analysis"]',
                is_active=True
            )
        ]
        
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = mock_functions
        mock_session_instance.execute.return_value = mock_result
        
        service = RetrievalService()
        results = await service.get_functions_by_categories(["math"], limit=10)
        
        assert len(results) == 2  # Mock returns all functions
        assert all(result['match_type'] == 'category' for result in results)
        assert all(result['similarity'] == 0.8 for result in results)