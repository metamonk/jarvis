# Jarvis Tool Functions Documentation

This directory contains custom tool functions that enable the Jarvis voice assistant to interact with external data sources and services. All tools are designed to return data with proper **source attribution** to ensure transparency and traceability.

## Table of Contents

- [Overview](#overview)
- [Available Tools](#available-tools)
- [Installation & Setup](#installation--setup)
- [Usage Examples](#usage-examples)
- [Source Attribution](#source-attribution)
- [Error Handling](#error-handling)
- [Testing](#testing)
- [API Reference](#api-reference)

---

## Overview

The Jarvis tool functions provide integration with:

1. **Pinecone** - Vector database for semantic document search
2. **Company API** - Internal warehouse/manufacturing data (loads, inventory, equipment)
3. **GitHub** - Code search across public and private repositories

All functions follow a consistent pattern:
- Clear, type-annotated function signatures
- Comprehensive docstrings with examples
- Custom error classes for better error handling
- **Mandatory source attribution** in all responses

---

## Available Tools

### 1. Pinecone Search (`pinecone_search.py`)

Search vector database for relevant documents using semantic similarity.

**Key Functions:**
- `search_pinecone()` - Perform vector similarity search
- `get_index_stats()` - Get metadata about a Pinecone index
- `initialize_pinecone()` - Initialize Pinecone client (internal)

**Use Cases:**
- Finding relevant documentation
- Semantic search across company knowledge base
- Context retrieval for LLM prompts

### 2. Company API (`company_api.py`)

Interact with internal warehouse/manufacturing systems.

**Key Functions:**
- `get_company_data()` - Generic wrapper for all data types
- `get_load_status()` - Get status of specific loads
- `list_loads()` - List all loads
- `get_inventory()` - Get SKU inventory details
- `list_inventory()` - List all inventory items
- `get_equipment_status()` - Get equipment status
- `list_equipment()` - List all equipment

**Use Cases:**
- Checking load status and location
- Monitoring inventory levels
- Equipment status tracking
- Reorder alerts

### 3. GitHub Search (`github_search.py`)

Search code across GitHub repositories.

**Key Functions:**
- `search_github_code()` - Search for code using GitHub API
- `get_file_content()` - Retrieve specific file contents
- `get_github_token()` - Get GitHub token from environment (internal)

**Use Cases:**
- Finding code examples
- Locating specific implementations
- API usage reference
- Code documentation lookup

---

## Installation & Setup

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt
```

### Environment Configuration

Create a `.env` file in the backend root directory:

```bash
# Required for Pinecone
PINECONE_API_KEY=your_pinecone_api_key_here

# Optional: Pinecone configuration
PINECONE_INDEX_NAME=jarvis-docs  # Default index name

# Optional for GitHub (required for private repos and higher rate limits)
GITHUB_TOKEN=ghp_your_github_token_here

# Optional for Company API
COMPANY_API_URL=https://api.example.com  # Default: http://localhost:8000
COMPANY_API_KEY=your_api_key_here  # Optional for mock API

# Required for production voice features
DEEPGRAM_API_KEY=your_deepgram_key
OPENAI_API_KEY=your_openai_key
ELEVENLABS_API_KEY=your_elevenlabs_key
```

### API Key Setup Guide

**Pinecone:**
1. Sign up at [https://www.pinecone.io/](https://www.pinecone.io/)
2. Create an index named `jarvis-docs` (or customize via `PINECONE_INDEX_NAME`)
3. Copy your API key to `.env`

**GitHub:**
1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate new token with `repo` and `read:org` scopes
3. Copy token to `.env` as `GITHUB_TOKEN`

**Company API:**
- For development: Use the mock API provided in `/mock-company-api`
- For production: Set `COMPANY_API_URL` to your company's API endpoint

---

## Usage Examples

### Pinecone Search

```python
from src.tools import search_pinecone

# Assuming you have a query embedding from OpenAI or similar
query_embedding = [0.1, 0.2, 0.3, ...]  # 1536-dimensional vector for OpenAI

# Basic search
results = search_pinecone(
    query_vector=query_embedding,
    index_name="jarvis-docs",
    top_k=5
)

# Process results
for result in results:
    print(f"Document ID: {result['id']}")
    print(f"Similarity Score: {result['score']}")
    print(f"Title: {result['metadata']['title']}")
    print(f"Source: {result['source']}")
    print(f"URL: {result['source']['url']}")
    print("---")

# Search with metadata filtering
results = search_pinecone(
    query_vector=query_embedding,
    namespace="production",
    filter_metadata={"source_type": "documentation"},
    top_k=3
)

# Get index statistics
from src.tools.pinecone_search import get_index_stats

stats = get_index_stats("jarvis-docs")
print(f"Total vectors: {stats['total_vector_count']}")
print(f"Dimensions: {stats['dimension']}")
```

### Company API

```python
from src.tools import get_company_data

# Get specific load status
load = get_company_data("load", "2314")
print(f"Load {load['load_id']} is {load['status']}")
print(f"Location: {load['location']}")
print(f"Scheduled: {load['scheduled_time']}")
print(f"Source: {load['source']['system']}")

# List all loads
all_loads = get_company_data("load")
for load in all_loads['loads']:
    if load['status'] == 'delayed':
        print(f"ALERT: Load {load['load_id']} is delayed!")

# Check inventory
item = get_company_data("inventory", "SKU-001")
if item['needs_reorder']:
    print(f"LOW STOCK: {item['name']} - Only {item['quantity']} left")
    print(f"Supplier: {item['supplier']}")

# Monitor equipment
equipment = get_company_data("equipment", "FORK-001")
print(f"{equipment['name']}: {equipment['status']}")
if equipment['days_until_maintenance'] < 7:
    print(f"Maintenance due in {equipment['days_until_maintenance']} days")
```

### GitHub Search

```python
from src.tools import search_github_code

# Search for FastAPI WebSocket examples
results = search_github_code(
    query="WebSocket",
    language="python",
    org="fastapi",
    max_results=5
)

print(f"Found {results['total_count']} total results")
print(f"Rate limit remaining: {results['source']['rate_limit_remaining']}")

for item in results['items']:
    print(f"\nFile: {item['path']}")
    print(f"Repository: {item['repository']['full_name']}")
    print(f"URL: {item['html_url']}")
    print(f"Score: {item['score']}")

# Get specific file content
from src.tools.github_search import get_file_content

content = get_file_content(
    owner="fastapi",
    repo="fastapi",
    path="fastapi/main.py",
    ref="master"
)

print(content['decoded_content'])  # UTF-8 decoded content
print(f"File size: {content['size']} bytes")
print(f"Source: {content['source']['html_url']}")
```

### Unified Import

```python
# Import all tools at once
from src.tools import (
    search_pinecone,
    get_company_data,
    search_github_code
)

# Or import specific modules
from src.tools import pinecone_search, company_api, github_search

# Access additional functions
stats = pinecone_search.get_index_stats("jarvis-docs")
load = company_api.get_load_status("2314")
file = github_search.get_file_content("owner", "repo", "path/to/file.py")
```

---

## Source Attribution

### Why Source Attribution Matters

Source attribution is **mandatory** for all tool functions to ensure:

1. **Transparency** - Users know where information came from
2. **Traceability** - Ability to verify and audit data sources
3. **Compliance** - Meeting data provenance requirements
4. **Trust** - Building confidence in AI-generated responses

### Attribution Format

All tool functions return data with a `source` field containing:

```python
{
    "type": "pinecone" | "company_api" | "github",
    "platform": "Human-readable platform name",
    # Additional fields specific to each tool...
}
```

### Pinecone Attribution

```python
{
    "source": {
        "type": "pinecone",
        "index": "jarvis-docs",
        "namespace": "production",
        "document_id": "doc-123",
        "timestamp": "2024-11-18T10:30:00Z",
        "url": "https://example.com/docs",
        "document_type": "documentation",
        "title": "API Documentation"
    }
}
```

### Company API Attribution

```python
{
    "source": {
        "type": "company_api",
        "system": "warehouse_management_system",
        "endpoint": "/api/v1/loads/2314",
        "load_id": "2314",
        "last_updated": "2024-11-18T10:30:00Z"
    }
}
```

### GitHub Attribution

```python
{
    "source": {
        "type": "github",
        "platform": "GitHub Code Search",
        "repository": "fastapi/fastapi",
        "file_path": "fastapi/main.py",
        "html_url": "https://github.com/fastapi/fastapi/blob/main/fastapi/main.py",
        "sha": "abc123def456",
        "api_url": "https://api.github.com/repos/fastapi/fastapi/contents/fastapi/main.py"
    }
}
```

### Best Practices for Attribution

1. **Always display source information** when presenting data to users
2. **Include source URLs** when available for verification
3. **Log source information** for audit trails
4. **Preserve source metadata** when passing data between functions
5. **Cite sources** in voice responses (e.g., "According to the warehouse management system...")

Example voice response:
```
"Load 2314 is ready for pickup in Bay 3, scheduled for 4:00 PM.
This information is from the warehouse management system, last updated at 10:30 AM."
```

---

## Error Handling

All tools define custom exception classes for clear error handling:

### Pinecone Errors

```python
from src.tools.pinecone_search import PineconeSearchError

try:
    results = search_pinecone(query_vector)
except PineconeSearchError as e:
    if "PINECONE_API_KEY" in str(e):
        print("Error: Pinecone API key not configured")
    elif "does not exist" in str(e):
        print("Error: Index not found")
    else:
        print(f"Pinecone error: {e}")
```

### Company API Errors

```python
from src.tools.company_api import CompanyAPIError

try:
    load = get_company_data("load", "9999")
except CompanyAPIError as e:
    if "404" in str(e):
        print("Error: Load not found")
    elif "Failed to connect" in str(e):
        print("Error: Company API is unreachable")
    else:
        print(f"Company API error: {e}")
```

### GitHub Errors

```python
from src.tools.github_search import GitHubSearchError

try:
    results = search_github_code("test query")
except GitHubSearchError as e:
    if "rate limit" in str(e).lower():
        print("Error: GitHub API rate limit exceeded")
        print("Consider setting GITHUB_TOKEN for higher limits")
    elif "422" in str(e):
        print("Error: Invalid search query")
    else:
        print(f"GitHub error: {e}")
```

### Error Handling Best Practices

1. **Catch specific exceptions** rather than generic `Exception`
2. **Log errors** with context for debugging
3. **Provide user-friendly messages** in voice responses
4. **Implement retry logic** for transient failures
5. **Graceful degradation** when services are unavailable

---

## Testing

### Running Tests

```bash
# Run all tool tests
pytest tests/tools/ -v

# Run specific tool tests
pytest tests/tools/test_pinecone_search.py -v
pytest tests/tools/test_company_api.py -v
pytest tests/tools/test_github_search.py -v

# Run integration tests
pytest tests/tools/test_integration.py -v

# Run with coverage
pytest tests/tools/ --cov=src/tools --cov-report=html
```

### Test Structure

```
tests/tools/
├── __init__.py
├── test_pinecone_search.py      # Pinecone unit tests
├── test_company_api.py           # Company API unit tests
├── test_github_search.py         # GitHub search unit tests
└── test_integration.py           # Integration tests
```

### Test Coverage

All tools have comprehensive test coverage including:

- ✅ Successful operations
- ✅ Error conditions
- ✅ Source attribution validation
- ✅ Edge cases and boundary conditions
- ✅ Mock external services
- ✅ Parameter validation
- ✅ Documentation completeness

---

## API Reference

### Pinecone Search

#### `search_pinecone(query_vector, **kwargs)`

Perform vector similarity search against Pinecone index.

**Parameters:**
- `query_vector` (List[float]): Query embedding vector
- `index_name` (str): Pinecone index name (default: "jarvis-docs")
- `namespace` (str): Namespace within index (default: "")
- `top_k` (int): Number of results to return (default: 5)
- `filter_metadata` (Dict): Metadata filter (optional)
- `include_metadata` (bool): Include metadata in results (default: True)
- `include_values` (bool): Include vector values (default: False)

**Returns:** List[Dict] - Search results with source attribution

**Raises:** `PineconeSearchError` - On search failure

---

### Company API

#### `get_company_data(data_type, identifier=None)`

Generic function to retrieve company data.

**Parameters:**
- `data_type` (str): Type of data ("load", "inventory", "equipment")
- `identifier` (str, optional): Specific ID/SKU to retrieve

**Returns:** Dict - Data with source attribution

**Raises:** `CompanyAPIError` - On API failure

---

### GitHub Search

#### `search_github_code(query, **kwargs)`

Search for code on GitHub.

**Parameters:**
- `query` (str): Search query
- `max_results` (int): Maximum results (default: 5)
- `language` (str, optional): Programming language filter
- `repo` (str, optional): Repository filter ("owner/repo")
- `org` (str, optional): Organization filter
- `user` (str, optional): User filter
- `path` (str, optional): File path filter
- `extension` (str, optional): File extension filter

**Returns:** Dict - Search results with source attribution

**Raises:** `GitHubSearchError` - On search failure

---

## Additional Resources

- **Pinecone Documentation:** https://docs.pinecone.io/
- **GitHub API Documentation:** https://docs.github.com/en/rest/search
- **Mock Company API:** See `/mock-company-api/README.md`

---

## Contributing

When adding new tool functions:

1. Follow the established patterns for source attribution
2. Define custom error classes
3. Write comprehensive docstrings with examples
4. Add unit tests with >90% coverage
5. Update this documentation
6. Ensure all functions return source attribution

---

## License

Part of the Jarvis MVP project - Internal use only.

---

**Questions or Issues?**

Contact the Jarvis development team or file an issue in the project repository.
