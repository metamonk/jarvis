"""
GitHub code search functionality.

Provides code search capabilities using GitHub API
with proper source attribution for all results.
"""

import os
from typing import List, Dict, Any, Optional
import httpx
from loguru import logger


class GitHubSearchError(Exception):
    """Custom exception for GitHub search errors."""
    pass


def get_github_token() -> Optional[str]:
    """
    Get GitHub API token from environment.

    Returns:
        GitHub token or None if not set

    Note:
        GitHub API has rate limits:
        - Unauthenticated: 10 requests/minute
        - Authenticated: 30 requests/minute for code search
    """
    token = os.getenv("GITHUB_TOKEN")

    if not token:
        logger.warning(
            "GITHUB_TOKEN not set. GitHub API rate limits will be very restrictive. "
            "See: https://docs.github.com/en/rest/search#rate-limit"
        )

    return token


def search_github_code(
    query: str,
    max_results: int = 5,
    sort: str = "indexed",
    order: str = "desc",
    per_page: int = 30,
    language: Optional[str] = None,
    repo: Optional[str] = None,
    org: Optional[str] = None,
    user: Optional[str] = None,
    path: Optional[str] = None,
    extension: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search for code on GitHub using the GitHub API.

    Args:
        query: Search query string
        max_results: Maximum number of results to return (default: 5)
        sort: Sort field - "indexed" or "best-match" (default: "indexed")
        order: Sort order - "desc" or "asc" (default: "desc")
        per_page: Results per page for API call (max: 100, default: 30)
        language: Filter by programming language (e.g., "python", "javascript")
        repo: Filter by repository (e.g., "owner/repo")
        org: Filter by organization
        user: Filter by user
        path: Filter by file path
        extension: Filter by file extension (e.g., "py", "js")

    Returns:
        Dictionary containing:
        - total_count: Total number of results available
        - items: List of code search results
        - query_metadata: Information about the query
        - source: Attribution information

        Each item contains:
        - name: File name
        - path: File path
        - sha: Git SHA of the file
        - url: GitHub web URL
        - git_url: Git API URL
        - html_url: HTML URL to view on GitHub
        - repository: Repository information
        - score: Relevance score
        - text_matches: Matching text fragments (if available)
        - source: Attribution for this specific result

    Raises:
        GitHubSearchError: If search fails

    Example:
        >>> # Search for Python files containing "fastapi"
        >>> results = search_github_code(
        ...     query="fastapi",
        ...     language="python",
        ...     max_results=5
        ... )
        >>> for item in results['items']:
        ...     print(f"File: {item['path']}")
        ...     print(f"Repo: {item['repository']['full_name']}")
        ...     print(f"URL: {item['html_url']}")
    """
    try:
        # Build search query with qualifiers
        search_parts = [query]

        if language:
            search_parts.append(f"language:{language}")
        if repo:
            search_parts.append(f"repo:{repo}")
        if org:
            search_parts.append(f"org:{org}")
        if user:
            search_parts.append(f"user:{user}")
        if path:
            search_parts.append(f"path:{path}")
        if extension:
            search_parts.append(f"extension:{extension}")

        full_query = " ".join(search_parts)

        # Prepare API request
        url = "https://api.github.com/search/code"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Jarvis-Voice-Assistant",
        }

        token = get_github_token()
        if token:
            headers["Authorization"] = f"token {token}"

        params = {
            "q": full_query,
            "sort": sort,
            "order": order,
            "per_page": min(per_page, 100),  # GitHub API max is 100
        }

        logger.info(f"GitHub code search query: {full_query}")

        # Make API request
        with httpx.Client(timeout=15.0) as client:
            response = client.get(url, params=params, headers=headers)

            # Check rate limiting
            if response.status_code == 403:
                rate_limit_remaining = response.headers.get("X-RateLimit-Remaining", "0")
                if rate_limit_remaining == "0":
                    reset_time = response.headers.get("X-RateLimit-Reset", "unknown")
                    raise GitHubSearchError(
                        f"GitHub API rate limit exceeded. Resets at: {reset_time}. "
                        "Consider setting GITHUB_TOKEN for higher limits."
                    )

            response.raise_for_status()
            data = response.json()

        # Limit results to max_results
        items = data.get("items", [])[:max_results]

        # Format results with source attribution
        formatted_items = []
        for item in items:
            formatted_item = {
                "name": item.get("name"),
                "path": item.get("path"),
                "sha": item.get("sha"),
                "url": item.get("url"),
                "git_url": item.get("git_url"),
                "html_url": item.get("html_url"),
                "repository": {
                    "id": item.get("repository", {}).get("id"),
                    "name": item.get("repository", {}).get("name"),
                    "full_name": item.get("repository", {}).get("full_name"),
                    "owner": item.get("repository", {}).get("owner", {}).get("login"),
                    "html_url": item.get("repository", {}).get("html_url"),
                    "description": item.get("repository", {}).get("description"),
                    "private": item.get("repository", {}).get("private", False),
                },
                "score": item.get("score"),
                "source": {
                    "type": "github",
                    "platform": "GitHub Code Search",
                    "repository": item.get("repository", {}).get("full_name"),
                    "file_path": item.get("path"),
                    "html_url": item.get("html_url"),
                    "sha": item.get("sha"),
                    "api_url": item.get("url"),
                }
            }

            # Include text matches if available
            if "text_matches" in item:
                formatted_item["text_matches"] = [
                    {
                        "object_url": match.get("object_url"),
                        "object_type": match.get("object_type"),
                        "property": match.get("property"),
                        "fragment": match.get("fragment"),
                        "matches": match.get("matches", []),
                    }
                    for match in item.get("text_matches", [])
                ]

            formatted_items.append(formatted_item)

        # Build response with metadata
        result = {
            "total_count": data.get("total_count", 0),
            "items": formatted_items,
            "query_metadata": {
                "original_query": query,
                "full_query": full_query,
                "language": language,
                "repo": repo,
                "org": org,
                "user": user,
                "path": path,
                "extension": extension,
                "max_results": max_results,
                "sort": sort,
                "order": order,
            },
            "source": {
                "type": "github",
                "platform": "GitHub Code Search API",
                "api_endpoint": url,
                "authenticated": token is not None,
                "rate_limit_remaining": response.headers.get("X-RateLimit-Remaining"),
                "rate_limit_reset": response.headers.get("X-RateLimit-Reset"),
            }
        }

        logger.info(
            f"GitHub search returned {len(formatted_items)} results "
            f"(total available: {data.get('total_count', 0)})"
        )

        return result

    except httpx.HTTPStatusError as e:
        logger.error(f"GitHub API HTTP error: {e.response.status_code} - {e.response.text}")
        raise GitHubSearchError(
            f"GitHub API request failed with status {e.response.status_code}: {e.response.text}"
        )
    except httpx.RequestError as e:
        logger.error(f"GitHub API request error: {e}")
        raise GitHubSearchError(f"Failed to connect to GitHub API: {e}")
    except GitHubSearchError:
        raise
    except Exception as e:
        logger.error(f"GitHub search error: {e}")
        raise GitHubSearchError(f"GitHub code search failed: {e}")


def get_file_content(
    owner: str,
    repo: str,
    path: str,
    ref: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get the content of a specific file from a GitHub repository.

    Args:
        owner: Repository owner (user or organization)
        repo: Repository name
        path: File path within the repository
        ref: Git reference (branch, tag, or commit SHA). Default: main/master

    Returns:
        Dictionary containing:
        - name: File name
        - path: File path
        - sha: Git SHA
        - size: File size in bytes
        - content: Base64-encoded file content
        - decoded_content: UTF-8 decoded content (if text file)
        - encoding: Content encoding (usually "base64")
        - html_url: URL to view on GitHub
        - download_url: Direct download URL
        - source: Attribution information

    Raises:
        GitHubSearchError: If file retrieval fails

    Example:
        >>> content = get_file_content(
        ...     owner="fastapi",
        ...     repo="fastapi",
        ...     path="fastapi/main.py"
        ... )
        >>> print(content['decoded_content'])
    """
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Jarvis-Voice-Assistant",
        }

        token = get_github_token()
        if token:
            headers["Authorization"] = f"token {token}"

        params = {}
        if ref:
            params["ref"] = ref

        logger.info(f"Fetching GitHub file: {owner}/{repo}/{path}")

        with httpx.Client(timeout=15.0) as client:
            response = client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

        # Decode base64 content if it's a file (not a directory)
        decoded_content = None
        if data.get("type") == "file" and data.get("content"):
            import base64
            try:
                content_bytes = base64.b64decode(data.get("content", ""))
                decoded_content = content_bytes.decode("utf-8")
            except Exception as e:
                logger.warning(f"Could not decode file content as UTF-8: {e}")

        result = {
            "name": data.get("name"),
            "path": data.get("path"),
            "sha": data.get("sha"),
            "size": data.get("size"),
            "content": data.get("content"),
            "decoded_content": decoded_content,
            "encoding": data.get("encoding"),
            "html_url": data.get("html_url"),
            "download_url": data.get("download_url"),
            "type": data.get("type"),
            "source": {
                "type": "github",
                "platform": "GitHub Contents API",
                "repository": f"{owner}/{repo}",
                "file_path": path,
                "html_url": data.get("html_url"),
                "sha": data.get("sha"),
                "ref": ref or "default branch",
            }
        }

        logger.info(f"Retrieved file content: {path} ({data.get('size', 0)} bytes)")
        return result

    except httpx.HTTPStatusError as e:
        logger.error(f"GitHub API HTTP error: {e.response.status_code}")
        raise GitHubSearchError(
            f"Failed to get file content (status {e.response.status_code})"
        )
    except httpx.RequestError as e:
        logger.error(f"GitHub API request error: {e}")
        raise GitHubSearchError(f"Failed to connect to GitHub API: {e}")
    except Exception as e:
        logger.error(f"GitHub file retrieval error: {e}")
        raise GitHubSearchError(f"Failed to retrieve file content: {e}")
