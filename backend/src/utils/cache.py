"""
Redis caching layer for performance optimization.

Provides caching functionality for frequently accessed data including:
- Company API responses (load status, inventory, equipment)
- Pinecone search results
- LLM responses for common queries
"""

import json
import hashlib
from typing import Any, Optional, Callable, Union
from functools import wraps
import asyncio
from datetime import timedelta

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from loguru import logger
from ..config.settings import settings


class CacheManager:
    """
    Redis-based cache manager with support for multiple cache strategies.

    Supports:
    - TTL-based expiration
    - Namespace-based organization
    - Automatic serialization/deserialization
    - Cache invalidation
    """

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize cache manager.

        Args:
            redis_url: Redis connection URL (uses settings.REDIS_URL if not provided)
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self._client: Optional[redis.Redis] = None
        self._enabled = bool(self.redis_url and REDIS_AVAILABLE)

        if not REDIS_AVAILABLE:
            logger.warning("redis package not installed - caching disabled")
        elif not self.redis_url:
            logger.warning("REDIS_URL not configured - caching disabled")
        else:
            logger.info(f"Cache manager initialized with Redis at {self.redis_url}")

    async def connect(self):
        """Establish Redis connection."""
        if not self._enabled:
            return

        try:
            self._client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self._client.ping()
            logger.info("Connected to Redis cache")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._enabled = False
            self._client = None

    async def disconnect(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            logger.info("Disconnected from Redis cache")

    def _make_key(self, namespace: str, key: str) -> str:
        """
        Create namespaced cache key.

        Args:
            namespace: Cache namespace (e.g., "company_api", "pinecone")
            key: Cache key

        Returns:
            Namespaced key string
        """
        return f"jarvis:{namespace}:{key}"

    async def get(
        self,
        key: str,
        namespace: str = "default"
    ) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key
            namespace: Cache namespace

        Returns:
            Cached value or None if not found
        """
        if not self._enabled or not self._client:
            return None

        try:
            cache_key = self._make_key(namespace, key)
            value = await self._client.get(cache_key)

            if value:
                logger.debug(f"Cache HIT: {cache_key}")
                return json.loads(value)
            else:
                logger.debug(f"Cache MISS: {cache_key}")
                return None

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        namespace: str = "default",
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            namespace: Cache namespace
            ttl_seconds: Time to live in seconds (optional)

        Returns:
            True if successful, False otherwise
        """
        if not self._enabled or not self._client:
            return False

        try:
            cache_key = self._make_key(namespace, key)
            serialized = json.dumps(value)

            if ttl_seconds:
                await self._client.setex(cache_key, ttl_seconds, serialized)
            else:
                await self._client.set(cache_key, serialized)

            logger.debug(f"Cache SET: {cache_key} (TTL: {ttl_seconds}s)")
            return True

        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def delete(
        self,
        key: str,
        namespace: str = "default"
    ) -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key
            namespace: Cache namespace

        Returns:
            True if successful, False otherwise
        """
        if not self._enabled or not self._client:
            return False

        try:
            cache_key = self._make_key(namespace, key)
            await self._client.delete(cache_key)
            logger.debug(f"Cache DELETE: {cache_key}")
            return True

        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    async def clear_namespace(self, namespace: str) -> int:
        """
        Clear all keys in a namespace.

        Args:
            namespace: Cache namespace to clear

        Returns:
            Number of keys deleted
        """
        if not self._enabled or not self._client:
            return 0

        try:
            pattern = self._make_key(namespace, "*")
            keys = []

            async for key in self._client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted = await self._client.delete(*keys)
                logger.info(f"Cleared {deleted} keys from namespace: {namespace}")
                return deleted

            return 0

        except Exception as e:
            logger.error(f"Cache clear namespace error: {e}")
            return 0

    async def exists(
        self,
        key: str,
        namespace: str = "default"
    ) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key
            namespace: Cache namespace

        Returns:
            True if key exists, False otherwise
        """
        if not self._enabled or not self._client:
            return False

        try:
            cache_key = self._make_key(namespace, key)
            return await self._client.exists(cache_key) > 0

        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False

    def cache_result(
        self,
        namespace: str = "default",
        ttl_seconds: Optional[int] = 300,
        key_builder: Optional[Callable] = None
    ):
        """
        Decorator for caching function results.

        Args:
            namespace: Cache namespace
            ttl_seconds: Time to live in seconds
            key_builder: Optional function to build cache key from args/kwargs

        Example:
            >>> @cache_manager.cache_result("company_api", ttl_seconds=600)
            ... async def get_load_status(load_id: str):
            ...     return await api.get_load(load_id)
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Build cache key
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    # Default: hash function name and arguments
                    key_data = f"{func.__name__}:{args}:{kwargs}"
                    cache_key = hashlib.md5(key_data.encode()).hexdigest()

                # Try to get from cache
                cached = await self.get(cache_key, namespace)
                if cached is not None:
                    return cached

                # Execute function
                result = await func(*args, **kwargs)

                # Cache result
                await self.set(cache_key, result, namespace, ttl_seconds)

                return result

            return wrapper
        return decorator


# Global cache manager instance
cache_manager = CacheManager()


# Predefined cache configurations for different data types
CACHE_CONFIG = {
    # Company API data - medium TTL since it changes periodically
    "company_api_load": {"ttl_seconds": 300, "namespace": "company_api:load"},
    "company_api_inventory": {"ttl_seconds": 600, "namespace": "company_api:inventory"},
    "company_api_equipment": {"ttl_seconds": 300, "namespace": "company_api:equipment"},

    # Pinecone search - longer TTL since documents change infrequently
    "pinecone_search": {"ttl_seconds": 3600, "namespace": "pinecone"},

    # LLM responses - short TTL for dynamic content
    "llm_response": {"ttl_seconds": 1800, "namespace": "llm"},

    # System configuration - very long TTL
    "config": {"ttl_seconds": 86400, "namespace": "config"},
}


async def get_cached_company_data(
    data_type: str,
    identifier: str
) -> Optional[Any]:
    """
    Get company data from cache.

    Args:
        data_type: Type of data ("load", "inventory", "equipment")
        identifier: Data identifier

    Returns:
        Cached data or None
    """
    namespace = CACHE_CONFIG[f"company_api_{data_type}"]["namespace"]
    return await cache_manager.get(identifier, namespace)


async def set_cached_company_data(
    data_type: str,
    identifier: str,
    data: Any
) -> bool:
    """
    Cache company data.

    Args:
        data_type: Type of data ("load", "inventory", "equipment")
        identifier: Data identifier
        data: Data to cache

    Returns:
        True if successful
    """
    config = CACHE_CONFIG[f"company_api_{data_type}"]
    return await cache_manager.set(
        identifier,
        data,
        config["namespace"],
        config["ttl_seconds"]
    )


async def invalidate_company_data(
    data_type: str,
    identifier: Optional[str] = None
) -> bool:
    """
    Invalidate company data cache.

    Args:
        data_type: Type of data ("load", "inventory", "equipment")
        identifier: Optional specific identifier to invalidate

    Returns:
        True if successful
    """
    namespace = CACHE_CONFIG[f"company_api_{data_type}"]["namespace"]

    if identifier:
        return await cache_manager.delete(identifier, namespace)
    else:
        await cache_manager.clear_namespace(namespace)
        return True
