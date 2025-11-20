"""Integration tests for tool functions.

Tests verify:
1. Tool imports work correctly
2. Source attribution is properly included in all responses
3. Custom exceptions are defined and importable
"""

import pytest
from unittest.mock import patch, MagicMock


# ============================================================================
# Import Tests - Verify all tools can be imported
# ============================================================================

def test_import_pinecone_tool():
    """Test that Pinecone tool imports successfully."""
    from src.tools import search_pinecone
    from src.tools.pinecone_search import PineconeSearchError

    assert callable(search_pinecone)
    assert issubclass(PineconeSearchError, Exception)


def test_import_company_api_tool():
    """Test that Company API tool imports successfully."""
    from src.tools import get_company_data
    from src.tools.company_api import CompanyAPIError

    assert callable(get_company_data)
    assert issubclass(CompanyAPIError, Exception)


def test_import_github_search_tool():
    """Test that GitHub search tool imports successfully."""
    from src.tools import search_github_code
    from src.tools.github_search import GitHubSearchError

    assert callable(search_github_code)
    assert issubclass(GitHubSearchError, Exception)


def test_import_all_tools_from_package():
    """Test that all tools are exported from tools package."""
    from src.tools import search_pinecone, get_company_data, search_github_code

    # Verify all three main functions are available
    assert callable(search_pinecone)
    assert callable(get_company_data)
    assert callable(search_github_code)


# ============================================================================
# Source Attribution Tests - Verify source metadata in responses
# ============================================================================

def test_source_attribution_pinecone():
    """Test that Pinecone results include proper source attribution."""
    from src.tools.pinecone_search import search_pinecone

    # Mock Pinecone client and results
    with patch('src.tools.pinecone_search.Pinecone') as mock_pinecone_class:
        mock_pc = MagicMock()
        mock_pinecone_class.return_value = mock_pc

        # Mock index list
        mock_pc.list_indexes.return_value.names.return_value = ['jarvis-docs']

        # Mock index and query results
        mock_index = MagicMock()
        mock_pc.Index.return_value = mock_index

        # Create mock match result
        mock_match = MagicMock()
        mock_match.id = "doc-123"
        mock_match.score = 0.95
        mock_match.metadata = {
            "title": "Test Document",
            "source_url": "https://example.com/doc",
            "timestamp": "2024-01-01"
        }
        mock_match.values = None

        mock_index.query.return_value.matches = [mock_match]

        # Mock environment variable
        with patch.dict('os.environ', {'PINECONE_API_KEY': 'test-key'}):
            # Execute search
            results = search_pinecone(
                query_vector=[0.1, 0.2, 0.3],
                index_name="jarvis-docs",
                top_k=1
            )

            # Verify source attribution is present
            assert len(results) == 1
            result = results[0]

            assert 'source' in result
            assert result['source']['type'] == 'pinecone'
            assert result['source']['index'] == 'jarvis-docs'
            assert result['source']['document_id'] == 'doc-123'
            assert 'url' in result['source']


def test_source_attribution_company_api():
    """Test that Company API results include proper source attribution."""
    from src.tools.company_api import get_load_status

    # Mock httpx client
    with patch('src.tools.company_api.httpx.Client') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "load_id": "2314",
            "status": "in_transit",
            "location": "Denver, CO"
        }
        mock_client.request.return_value = mock_response

        # Execute request
        result = get_load_status("2314")

        # Verify source attribution is present
        assert 'source' in result
        assert result['source']['type'] == 'company_api'
        assert result['source']['endpoint'] == '/api/v1/loads/2314'
        assert 'last_updated' in result['source']


def test_source_attribution_github_search():
    """Test that GitHub search results include proper source attribution."""
    from src.tools.github_search import search_github_code

    # Mock httpx client
    with patch('src.tools.github_search.httpx.Client') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {
            "X-RateLimit-Remaining": "30",
            "X-RateLimit-Reset": "1234567890"
        }
        mock_response.json.return_value = {
            "total_count": 1,
            "items": [{
                "name": "test.py",
                "path": "src/test.py",
                "sha": "abc123",
                "html_url": "https://github.com/owner/repo/blob/main/src/test.py",
                "url": "https://api.github.com/repos/owner/repo/contents/src/test.py",
                "git_url": "https://api.github.com/repos/owner/repo/git/blobs/abc123",
                "repository": {
                    "id": 12345,
                    "name": "repo",
                    "full_name": "owner/repo",
                    "html_url": "https://github.com/owner/repo",
                    "owner": {"login": "owner"}
                },
                "score": 1.0
            }]
        }
        mock_client.get.return_value = mock_response

        # Execute search
        result = search_github_code("test query", max_results=1)

        # Verify source attribution is present
        assert 'source' in result
        assert result['source']['type'] == 'github'
        assert result['source']['platform'] == 'GitHub Code Search API'
        assert 'api_endpoint' in result['source']

        # Verify item-level attribution
        assert len(result['items']) == 1
        item = result['items'][0]
        assert 'source' in item
        assert item['source']['type'] == 'github'
        assert item['source']['repository'] == 'owner/repo'
        assert item['source']['html_url'] == 'https://github.com/owner/repo/blob/main/src/test.py'


# ============================================================================
# Additional Integration Tests
# ============================================================================

def test_pinecone_error_handling():
    """Test that Pinecone tool raises appropriate errors."""
    from src.tools.pinecone_search import search_pinecone, PineconeSearchError

    # Test with missing API key
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(PineconeSearchError, match="PINECONE_API_KEY"):
            search_pinecone(query_vector=[0.1, 0.2, 0.3])


def test_company_api_error_handling():
    """Test that Company API tool raises appropriate errors."""
    from src.tools.company_api import get_load_status, CompanyAPIError

    # Mock httpx client to simulate API error
    with patch('src.tools.company_api.httpx.Client') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        # Mock 404 response
        import httpx
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Load not found"
        mock_client.request.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=mock_response
        )

        with pytest.raises(CompanyAPIError, match="404"):
            get_load_status("invalid-id")


def test_github_search_error_handling():
    """Test that GitHub search tool raises appropriate errors."""
    from src.tools.github_search import search_github_code, GitHubSearchError

    # Mock httpx client to simulate API error
    with patch('src.tools.github_search.httpx.Client') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        # Mock request error
        import httpx
        mock_client.get.side_effect = httpx.RequestError("Connection failed")

        with pytest.raises(GitHubSearchError, match="Connection failed"):
            search_github_code("test query")


def test_all_tools_have_documentation():
    """Test that all tool functions have proper docstrings."""
    from src.tools import search_pinecone, get_company_data, search_github_code

    # Verify docstrings exist and are comprehensive
    assert search_pinecone.__doc__ is not None
    assert len(search_pinecone.__doc__) > 100
    assert "Args:" in search_pinecone.__doc__
    assert "Returns:" in search_pinecone.__doc__

    assert get_company_data.__doc__ is not None
    assert len(get_company_data.__doc__) > 100

    assert search_github_code.__doc__ is not None
    assert len(search_github_code.__doc__) > 100
    assert "Args:" in search_github_code.__doc__
    assert "Returns:" in search_github_code.__doc__


def test_tools_readme_exists():
    """Test that tools README documentation exists."""
    import os

    readme_path = os.path.join(
        os.path.dirname(__file__),
        "..", "src", "tools", "README.md"
    )

    assert os.path.exists(readme_path), "Tools README.md should exist"

    # Verify README has substantial content
    with open(readme_path, 'r') as f:
        content = f.read()
        assert len(content) > 500, "README should have comprehensive documentation"
        assert "Pinecone" in content
        assert "Company API" in content
        assert "GitHub" in content


def test_tool_exceptions_are_distinct():
    """Test that each tool has its own distinct exception class."""
    from src.tools.pinecone_search import PineconeSearchError
    from src.tools.company_api import CompanyAPIError
    from src.tools.github_search import GitHubSearchError

    # Verify all are Exception subclasses
    assert issubclass(PineconeSearchError, Exception)
    assert issubclass(CompanyAPIError, Exception)
    assert issubclass(GitHubSearchError, Exception)

    # Verify they are distinct classes (not the same)
    assert PineconeSearchError is not CompanyAPIError
    assert CompanyAPIError is not GitHubSearchError
    assert GitHubSearchError is not PineconeSearchError

    # Verify they have proper names
    assert PineconeSearchError.__name__ == "PineconeSearchError"
    assert CompanyAPIError.__name__ == "CompanyAPIError"
    assert GitHubSearchError.__name__ == "GitHubSearchError"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
