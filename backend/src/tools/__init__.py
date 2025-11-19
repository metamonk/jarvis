"""
Tool functions for Jarvis MVP.

This module provides integration functions for:
- Pinecone vector database for document search
- Company API for internal data
- GitHub API for code search

All functions return data with proper source attribution.
"""

from .pinecone_search import search_pinecone
from .company_api import get_company_data
from .github_search import search_github_code

__all__ = [
    "search_pinecone",
    "get_company_data",
    "search_github_code",
]
