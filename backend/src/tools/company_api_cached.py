"""
Cached wrapper for Company API integration.

Provides the same interface as company_api.py but with Redis caching
for improved performance.
"""

from typing import Dict, Any, Optional
from loguru import logger

from .company_api import (
    get_load_status as _get_load_status,
    list_loads as _list_loads,
    get_inventory as _get_inventory,
    list_inventory as _list_inventory,
    get_equipment_status as _get_equipment_status,
    list_equipment as _list_equipment,
    CompanyAPIError
)
from ..utils.cache import (
    cache_manager,
    get_cached_company_data,
    set_cached_company_data
)
from ..utils.performance import performance_monitor


async def get_load_status(load_id: str, use_cache: bool = True) -> Dict[str, Any]:
    """
    Get load status with caching.

    Args:
        load_id: Load identifier
        use_cache: Whether to use cache (default: True)

    Returns:
        Load information dictionary
    """
    async with performance_monitor.track("company_api_load"):
        # Try cache first
        if use_cache:
            cached = await get_cached_company_data("load", load_id)
            if cached:
                logger.debug(f"Using cached load status for {load_id}")
                return cached

        # Fetch from API
        data = _get_load_status(load_id)

        # Cache result
        if use_cache:
            await set_cached_company_data("load", load_id, data)

        return data


async def list_loads(use_cache: bool = True) -> Dict[str, Any]:
    """
    List all loads with caching.

    Args:
        use_cache: Whether to use cache (default: True)

    Returns:
        Dictionary with loads list and metadata
    """
    async with performance_monitor.track("company_api_loads_list"):
        cache_key = "all_loads"

        # Try cache first
        if use_cache:
            cached = await get_cached_company_data("load", cache_key)
            if cached:
                logger.debug("Using cached loads list")
                return cached

        # Fetch from API
        data = _list_loads()

        # Cache result
        if use_cache:
            await set_cached_company_data("load", cache_key, data)

        return data


async def get_inventory(sku: str, use_cache: bool = True) -> Dict[str, Any]:
    """
    Get inventory information with caching.

    Args:
        sku: Stock Keeping Unit identifier
        use_cache: Whether to use cache (default: True)

    Returns:
        Inventory information dictionary
    """
    async with performance_monitor.track("company_api_inventory"):
        # Try cache first
        if use_cache:
            cached = await get_cached_company_data("inventory", sku)
            if cached:
                logger.debug(f"Using cached inventory for {sku}")
                return cached

        # Fetch from API
        data = _get_inventory(sku)

        # Cache result
        if use_cache:
            await set_cached_company_data("inventory", sku, data)

        return data


async def list_inventory(use_cache: bool = True) -> Dict[str, Any]:
    """
    List all inventory items with caching.

    Args:
        use_cache: Whether to use cache (default: True)

    Returns:
        Dictionary with inventory items and metadata
    """
    async with performance_monitor.track("company_api_inventory_list"):
        cache_key = "all_inventory"

        # Try cache first
        if use_cache:
            cached = await get_cached_company_data("inventory", cache_key)
            if cached:
                logger.debug("Using cached inventory list")
                return cached

        # Fetch from API
        data = _list_inventory()

        # Cache result
        if use_cache:
            await set_cached_company_data("inventory", cache_key, data)

        return data


async def get_equipment_status(
    equipment_id: str,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Get equipment status with caching.

    Args:
        equipment_id: Equipment identifier
        use_cache: Whether to use cache (default: True)

    Returns:
        Equipment information dictionary
    """
    async with performance_monitor.track("company_api_equipment"):
        # Try cache first
        if use_cache:
            cached = await get_cached_company_data("equipment", equipment_id)
            if cached:
                logger.debug(f"Using cached equipment status for {equipment_id}")
                return cached

        # Fetch from API
        data = _get_equipment_status(equipment_id)

        # Cache result
        if use_cache:
            await set_cached_company_data("equipment", equipment_id, data)

        return data


async def list_equipment(use_cache: bool = True) -> Dict[str, Any]:
    """
    List all equipment with caching.

    Args:
        use_cache: Whether to use cache (default: True)

    Returns:
        Dictionary with equipment list and metadata
    """
    async with performance_monitor.track("company_api_equipment_list"):
        cache_key = "all_equipment"

        # Try cache first
        if use_cache:
            cached = await get_cached_company_data("equipment", cache_key)
            if cached:
                logger.debug("Using cached equipment list")
                return cached

        # Fetch from API
        data = _list_equipment()

        # Cache result
        if use_cache:
            await set_cached_company_data("equipment", cache_key, data)

        return data
