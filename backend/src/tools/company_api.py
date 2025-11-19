"""
Company API integration for warehouse/manufacturing data.

Provides functions to interact with the company's internal API
for loads, inventory, and equipment tracking with source attribution.
"""

import os
from typing import Dict, Any, Optional, List
import httpx
from loguru import logger


class CompanyAPIError(Exception):
    """Custom exception for Company API errors."""
    pass


def get_api_config() -> Dict[str, str]:
    """
    Get Company API configuration from environment.

    Returns:
        Dictionary with base_url and api_key (if required)

    Raises:
        CompanyAPIError: If required configuration is missing
    """
    base_url = os.getenv("COMPANY_API_URL", "http://localhost:8000")

    # API key is optional for mock API but may be required for production
    api_key = os.getenv("COMPANY_API_KEY")

    logger.info(f"Company API configured with base URL: {base_url}")

    return {
        "base_url": base_url.rstrip("/"),
        "api_key": api_key,
    }


def _make_request(
    endpoint: str,
    method: str = "GET",
    params: Optional[Dict[str, Any]] = None,
    timeout: float = 10.0
) -> Dict[str, Any]:
    """
    Make HTTP request to Company API.

    Args:
        endpoint: API endpoint path (e.g., "/api/v1/loads/2314")
        method: HTTP method (default: GET)
        params: Query parameters (optional)
        timeout: Request timeout in seconds

    Returns:
        Parsed JSON response

    Raises:
        CompanyAPIError: If request fails
    """
    try:
        config = get_api_config()
        url = f"{config['base_url']}{endpoint}"

        headers = {}
        if config["api_key"]:
            headers["Authorization"] = f"Bearer {config['api_key']}"

        logger.debug(f"Company API request: {method} {url}")

        with httpx.Client(timeout=timeout) as client:
            response = client.request(
                method=method,
                url=url,
                params=params,
                headers=headers
            )

            response.raise_for_status()
            data = response.json()

            logger.debug(f"Company API response: {response.status_code}")
            return data

    except httpx.HTTPStatusError as e:
        logger.error(f"Company API HTTP error: {e.response.status_code} - {e.response.text}")
        raise CompanyAPIError(
            f"API request failed with status {e.response.status_code}: {e.response.text}"
        )
    except httpx.RequestError as e:
        logger.error(f"Company API request error: {e}")
        raise CompanyAPIError(f"Failed to connect to Company API: {e}")
    except Exception as e:
        logger.error(f"Company API error: {e}")
        raise CompanyAPIError(f"Company API request failed: {e}")


def get_load_status(load_id: str) -> Dict[str, Any]:
    """
    Get the status of a specific load.

    Args:
        load_id: Load identifier (e.g., "2314")

    Returns:
        Dictionary containing load information with source attribution:
        - load_id: Load identifier
        - location: Current location of the load
        - status: Current status (e.g., "ready_for_pickup", "in_transit")
        - scheduled_time: Scheduled pickup/delivery time
        - weight_kg: Weight in kilograms
        - destination: Destination location
        - priority: Priority level (high, medium, low)
        - last_updated: Last update timestamp
        - source: Attribution information

    Raises:
        CompanyAPIError: If load not found or request fails

    Example:
        >>> load = get_load_status("2314")
        >>> print(f"Load {load['load_id']} is {load['status']}")
        >>> print(f"Source: {load['source']['system']}")
    """
    endpoint = f"/api/v1/loads/{load_id}"
    data = _make_request(endpoint)

    # Add enhanced source attribution
    data["source"] = {
        "type": "company_api",
        "system": data.get("source", "warehouse_management_system"),
        "endpoint": endpoint,
        "load_id": load_id,
        "last_updated": data.get("last_updated"),
    }

    logger.info(f"Retrieved load status for {load_id}: {data.get('status')}")
    return data


def list_loads() -> Dict[str, Any]:
    """
    List all loads in the system.

    Returns:
        Dictionary containing:
        - loads: List of load objects
        - total_count: Total number of loads
        - source: Attribution information

    Raises:
        CompanyAPIError: If request fails

    Example:
        >>> result = list_loads()
        >>> for load in result['loads']:
        ...     print(f"Load {load['load_id']}: {load['status']}")
    """
    endpoint = "/api/v1/loads"
    data = _make_request(endpoint)

    # Add enhanced source attribution
    data["source"] = {
        "type": "company_api",
        "system": data.get("source", "warehouse_management_system"),
        "endpoint": endpoint,
        "total_count": data.get("total_count", 0),
    }

    logger.info(f"Retrieved {data.get('total_count', 0)} loads")
    return data


def get_inventory(sku: str) -> Dict[str, Any]:
    """
    Get inventory information for a specific SKU.

    Args:
        sku: Stock Keeping Unit identifier (e.g., "SKU-001")

    Returns:
        Dictionary containing inventory information with source attribution:
        - sku: SKU identifier
        - name: Product name
        - quantity: Current quantity in stock
        - location: Storage location
        - unit_price: Price per unit
        - total_value: Total value of inventory
        - reorder_level: Minimum stock level before reorder
        - needs_reorder: Boolean indicating if reorder is needed
        - supplier: Supplier name
        - last_updated: Last update timestamp
        - source: Attribution information

    Raises:
        CompanyAPIError: If SKU not found or request fails

    Example:
        >>> item = get_inventory("SKU-001")
        >>> if item['needs_reorder']:
        ...     print(f"{item['name']} needs reordering from {item['supplier']}")
    """
    endpoint = f"/api/v1/inventory/{sku}"
    data = _make_request(endpoint)

    # Add enhanced source attribution
    data["source"] = {
        "type": "company_api",
        "system": data.get("source", "inventory_management_system"),
        "endpoint": endpoint,
        "sku": sku,
        "last_updated": data.get("last_updated"),
    }

    logger.info(f"Retrieved inventory for {sku}: {data.get('quantity')} units")
    return data


def list_inventory() -> Dict[str, Any]:
    """
    List all inventory items in the system.

    Returns:
        Dictionary containing:
        - items: List of inventory items
        - total_items: Total number of items
        - source: Attribution information

    Raises:
        CompanyAPIError: If request fails

    Example:
        >>> result = list_inventory()
        >>> for item in result['items']:
        ...     if item['needs_reorder']:
        ...         print(f"Low stock alert: {item['name']}")
    """
    endpoint = "/api/v1/inventory"
    data = _make_request(endpoint)

    # Add enhanced source attribution and calculate needs_reorder for each item
    enriched_items = []
    for item in data.get("items", []):
        item["needs_reorder"] = item["quantity"] < item["reorder_level"]
        item["total_value"] = item["quantity"] * item["unit_price"]
        enriched_items.append(item)

    data["items"] = enriched_items
    data["source"] = {
        "type": "company_api",
        "system": data.get("source", "inventory_management_system"),
        "endpoint": endpoint,
        "total_items": data.get("total_items", 0),
    }

    logger.info(f"Retrieved {data.get('total_items', 0)} inventory items")
    return data


def get_equipment_status(equipment_id: str) -> Dict[str, Any]:
    """
    Get the status of a specific piece of equipment.

    Args:
        equipment_id: Equipment identifier (e.g., "FORK-001")

    Returns:
        Dictionary containing equipment information with source attribution:
        - equipment_id: Equipment identifier
        - name: Equipment name
        - status: Current status (operational, maintenance, etc.)
        - location: Current location
        - last_maintenance: Last maintenance date
        - next_maintenance: Next scheduled maintenance date
        - days_until_maintenance: Days until next maintenance
        - operator: Current operator (if any)
        - last_updated: Last update timestamp
        - source: Attribution information
        - Additional fields specific to equipment type (fuel_level, load_capacity_kg, etc.)

    Raises:
        CompanyAPIError: If equipment not found or request fails

    Example:
        >>> equipment = get_equipment_status("FORK-001")
        >>> if equipment['days_until_maintenance'] < 7:
        ...     print(f"Maintenance due soon for {equipment['name']}")
    """
    endpoint = f"/api/v1/equipment/{equipment_id}"
    data = _make_request(endpoint)

    # Add enhanced source attribution
    data["source"] = {
        "type": "company_api",
        "system": data.get("source", "equipment_tracking_system"),
        "endpoint": endpoint,
        "equipment_id": equipment_id,
        "last_updated": data.get("last_updated"),
    }

    logger.info(f"Retrieved equipment status for {equipment_id}: {data.get('status')}")
    return data


def list_equipment() -> Dict[str, Any]:
    """
    List all equipment in the system.

    Returns:
        Dictionary containing:
        - equipment: List of equipment objects
        - total_count: Total number of equipment items
        - source: Attribution information

    Raises:
        CompanyAPIError: If request fails

    Example:
        >>> result = list_equipment()
        >>> for eq in result['equipment']:
        ...     if eq['status'] == 'maintenance':
        ...         print(f"{eq['name']} is under maintenance")
    """
    endpoint = "/api/v1/equipment"
    data = _make_request(endpoint)

    # Add enhanced source attribution
    data["source"] = {
        "type": "company_api",
        "system": data.get("source", "equipment_tracking_system"),
        "endpoint": endpoint,
        "total_count": data.get("total_count", 0),
    }

    logger.info(f"Retrieved {data.get('total_count', 0)} equipment items")
    return data


def get_company_data(
    data_type: str,
    identifier: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generic function to get company data of various types.

    This is a convenience wrapper that routes to specific functions
    based on the data type requested.

    Args:
        data_type: Type of data to retrieve ("load", "inventory", "equipment")
        identifier: Optional specific identifier (load_id, sku, equipment_id)

    Returns:
        Dictionary containing requested data with source attribution

    Raises:
        CompanyAPIError: If data_type is invalid or request fails

    Example:
        >>> # Get specific load
        >>> load = get_company_data("load", "2314")
        >>> # Get all inventory
        >>> inventory = get_company_data("inventory")
    """
    data_type = data_type.lower()

    if data_type == "load":
        if identifier:
            return get_load_status(identifier)
        else:
            return list_loads()

    elif data_type == "inventory":
        if identifier:
            return get_inventory(identifier)
        else:
            return list_inventory()

    elif data_type == "equipment":
        if identifier:
            return get_equipment_status(identifier)
        else:
            return list_equipment()

    else:
        raise CompanyAPIError(
            f"Invalid data_type: {data_type}. "
            f"Must be one of: load, inventory, equipment"
        )
