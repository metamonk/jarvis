"""
Pinecone vector database search functionality.

Provides document search capabilities using Pinecone vector database
with proper source attribution for all results.
"""

import os
from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec
from loguru import logger


class PineconeSearchError(Exception):
    """Custom exception for Pinecone search errors."""
    pass


def initialize_pinecone() -> Pinecone:
    """
    Initialize Pinecone client.

    Returns:
        Pinecone: Initialized Pinecone client instance

    Raises:
        PineconeSearchError: If API key is missing or initialization fails
    """
    api_key = os.getenv("PINECONE_API_KEY")

    if not api_key:
        raise PineconeSearchError(
            "PINECONE_API_KEY environment variable not set. "
            "Please configure it in your .env file."
        )

    try:
        pc = Pinecone(api_key=api_key)
        logger.info("Pinecone client initialized successfully")
        return pc
    except Exception as e:
        logger.error(f"Failed to initialize Pinecone: {e}")
        raise PineconeSearchError(f"Failed to initialize Pinecone: {e}")


def search_pinecone(
    query_vector: List[float],
    index_name: str = "jarvis-docs",
    namespace: str = "",
    top_k: int = 5,
    filter_metadata: Optional[Dict[str, Any]] = None,
    include_metadata: bool = True,
    include_values: bool = False
) -> List[Dict[str, Any]]:
    """
    Search Pinecone vector database for relevant documents.

    Args:
        query_vector: The query embedding vector (list of floats)
        index_name: Name of the Pinecone index to query
        namespace: Namespace within the index (optional)
        top_k: Number of top results to return
        filter_metadata: Metadata filter for results (optional)
        include_metadata: Whether to include metadata in results
        include_values: Whether to include vector values in results

    Returns:
        List of search results with source attribution. Each result contains:
        - id: Document ID
        - score: Similarity score
        - metadata: Document metadata (if include_metadata=True)
        - values: Vector values (if include_values=True)
        - source: Attribution information

    Raises:
        PineconeSearchError: If search fails

    Example:
        >>> # Assuming you have a query embedding
        >>> results = search_pinecone(
        ...     query_vector=[0.1, 0.2, ...],
        ...     index_name="jarvis-docs",
        ...     top_k=5
        ... )
        >>> for result in results:
        ...     print(f"Document: {result['metadata']['title']}")
        ...     print(f"Source: {result['source']}")
    """
    try:
        # Initialize Pinecone client
        pc = initialize_pinecone()

        # Get index
        if index_name not in pc.list_indexes().names():
            raise PineconeSearchError(f"Index '{index_name}' does not exist")

        index = pc.Index(index_name)
        logger.info(f"Querying Pinecone index: {index_name}")

        # Perform search
        search_params = {
            "vector": query_vector,
            "top_k": top_k,
            "namespace": namespace,
            "include_metadata": include_metadata,
            "include_values": include_values,
        }

        if filter_metadata:
            search_params["filter"] = filter_metadata

        results = index.query(**search_params)

        # Format results with source attribution
        formatted_results = []
        for match in results.matches:
            result = {
                "id": match.id,
                "score": match.score,
                "source": {
                    "type": "pinecone",
                    "index": index_name,
                    "namespace": namespace,
                    "document_id": match.id,
                    "timestamp": match.metadata.get("timestamp") if include_metadata and match.metadata else None,
                }
            }

            if include_metadata and match.metadata:
                result["metadata"] = match.metadata

                # Add specific source attribution from metadata if available
                if "source_url" in match.metadata:
                    result["source"]["url"] = match.metadata["source_url"]
                if "source_type" in match.metadata:
                    result["source"]["document_type"] = match.metadata["source_type"]
                if "title" in match.metadata:
                    result["source"]["title"] = match.metadata["title"]

            if include_values and match.values:
                result["values"] = match.values

            formatted_results.append(result)

        logger.info(f"Pinecone search returned {len(formatted_results)} results")
        return formatted_results

    except PineconeSearchError:
        raise
    except Exception as e:
        logger.error(f"Pinecone search failed: {e}")
        raise PineconeSearchError(f"Search operation failed: {e}")


def get_index_stats(index_name: str = "jarvis-docs") -> Dict[str, Any]:
    """
    Get statistics about a Pinecone index.

    Args:
        index_name: Name of the Pinecone index

    Returns:
        Dictionary containing index statistics

    Raises:
        PineconeSearchError: If stats retrieval fails
    """
    try:
        pc = initialize_pinecone()

        if index_name not in pc.list_indexes().names():
            raise PineconeSearchError(f"Index '{index_name}' does not exist")

        index = pc.Index(index_name)
        stats = index.describe_index_stats()

        return {
            "index_name": index_name,
            "total_vector_count": stats.total_vector_count,
            "dimension": stats.dimension,
            "namespaces": stats.namespaces,
            "source": {
                "type": "pinecone",
                "index": index_name,
            }
        }

    except PineconeSearchError:
        raise
    except Exception as e:
        logger.error(f"Failed to get index stats: {e}")
        raise PineconeSearchError(f"Failed to get index stats: {e}")
