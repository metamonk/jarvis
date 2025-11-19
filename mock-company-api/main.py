"""
Jarvis Mock Company API
A realistic warehouse/manufacturing API simulator with SSE support.
Provides load status, inventory, and equipment data for Jarvis demos.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import asyncio
import random
import json
from datetime import datetime, timedelta
from typing import Dict, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Jarvis Mock Company API",
    description="Realistic warehouse/manufacturing data simulator",
    version="1.0.0"
)

# CORS configuration - allow all origins for demo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Mock Data Store
# ============================================================================

LOADS = {
    "2314": {
        "location": "Bay 3",
        "status": "ready_for_pickup",
        "scheduled_time": "4:00 PM",
        "weight_kg": 1250,
        "destination": "Distribution Center Alpha",
        "priority": "high"
    },
    "2315": {
        "location": "Bay 5",
        "status": "in_transit",
        "scheduled_time": "5:30 PM",
        "weight_kg": 890,
        "destination": "Warehouse B",
        "priority": "medium"
    },
    "2316": {
        "location": "Loading Dock A",
        "status": "loading",
        "scheduled_time": "3:00 PM",
        "weight_kg": 2100,
        "destination": "Customer Site 42",
        "priority": "high"
    },
    "2317": {
        "location": "Bay 1",
        "status": "awaiting_inspection",
        "scheduled_time": "6:00 PM",
        "weight_kg": 450,
        "destination": "Quality Control",
        "priority": "low"
    },
    "2318": {
        "location": "Storage Zone C",
        "status": "delayed",
        "scheduled_time": "2:30 PM",
        "weight_kg": 1580,
        "destination": "Port Terminal",
        "priority": "high"
    }
}

INVENTORY = {
    "SKU-001": {
        "name": "Hydraulic Pump Assembly",
        "quantity": 45,
        "location": "Warehouse A-12",
        "unit_price": 450.00,
        "reorder_level": 20,
        "supplier": "Industrial Parts Co"
    },
    "SKU-002": {
        "name": "Steel Bracket Type-M",
        "quantity": 230,
        "location": "Warehouse B-05",
        "unit_price": 12.50,
        "reorder_level": 100,
        "supplier": "MetalWorks Inc"
    },
    "SKU-003": {
        "name": "Conveyor Belt Motor",
        "quantity": 8,
        "location": "Warehouse A-18",
        "unit_price": 890.00,
        "reorder_level": 5,
        "supplier": "Motor Supply Ltd"
    },
    "SKU-004": {
        "name": "Safety Harness Pro",
        "quantity": 67,
        "location": "Safety Equipment Room",
        "unit_price": 125.00,
        "reorder_level": 30,
        "supplier": "SafetyFirst Equipment"
    },
    "SKU-005": {
        "name": "Forklift Battery 48V",
        "quantity": 12,
        "location": "Battery Charging Station",
        "unit_price": 2200.00,
        "reorder_level": 4,
        "supplier": "PowerCell Industries"
    }
}

EQUIPMENT = {
    "FORK-001": {
        "name": "Forklift Alpha",
        "status": "operational",
        "location": "Warehouse Floor A",
        "last_maintenance": "2024-11-10",
        "next_maintenance": "2024-12-10",
        "operator": "John Smith",
        "fuel_level": 85
    },
    "FORK-002": {
        "name": "Forklift Beta",
        "status": "maintenance",
        "location": "Maintenance Bay",
        "last_maintenance": "2024-11-15",
        "next_maintenance": "2024-12-15",
        "operator": None,
        "fuel_level": 0
    },
    "CRANE-001": {
        "name": "Overhead Crane 1",
        "status": "operational",
        "location": "Assembly Zone",
        "last_maintenance": "2024-11-01",
        "next_maintenance": "2024-12-01",
        "operator": "Maria Garcia",
        "load_capacity_kg": 5000
    },
    "CONV-001": {
        "name": "Main Conveyor Belt",
        "status": "operational",
        "location": "Shipping Line",
        "last_maintenance": "2024-10-20",
        "next_maintenance": "2024-11-20",
        "operator": "Automated",
        "speed_mpm": 15
    }
}

# ============================================================================
# Helper Functions
# ============================================================================

def get_current_time_str() -> str:
    """Get current time as ISO string"""
    return datetime.now().isoformat()

def simulate_load_update() -> Dict:
    """Simulate random load status change"""
    load_id = random.choice(list(LOADS.keys()))
    load = LOADS[load_id].copy()

    # Randomly update status
    statuses = ["loading", "ready_for_pickup", "in_transit", "delivered", "delayed"]
    new_status = random.choice(statuses)

    # Don't actually update the store, just return the change
    return {
        "load_id": load_id,
        "location": load["location"],
        "status": new_status,
        "scheduled_time": load["scheduled_time"],
        "timestamp": get_current_time_str(),
        "priority": load["priority"]
    }

# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """API root - health check"""
    return {
        "service": "Jarvis Mock Company API",
        "status": "operational",
        "version": "1.0.0",
        "endpoints": {
            "loads": "/api/v1/loads/{load_id}",
            "loads_list": "/api/v1/loads",
            "loads_stream": "/api/v1/loads/stream",
            "inventory": "/api/v1/inventory/{sku}",
            "inventory_list": "/api/v1/inventory",
            "equipment": "/api/v1/equipment/{equipment_id}",
            "equipment_list": "/api/v1/equipment"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": get_current_time_str()
    }

# ============================================================================
# Load Endpoints
# ============================================================================

@app.get("/api/v1/loads")
async def list_loads():
    """List all loads"""
    return {
        "loads": [
            {
                "load_id": load_id,
                **load,
                "last_updated": get_current_time_str()
            }
            for load_id, load in LOADS.items()
        ],
        "total_count": len(LOADS),
        "source": "warehouse_management_system"
    }

@app.get("/api/v1/loads/{load_id}")
async def get_load_status(load_id: str):
    """
    Get current load status

    Example: GET /api/v1/loads/2314
    """
    if load_id not in LOADS:
        raise HTTPException(status_code=404, detail=f"Load {load_id} not found")

    load = LOADS[load_id]
    return {
        "load_id": load_id,
        "location": load["location"],
        "status": load["status"],
        "scheduled_time": load["scheduled_time"],
        "weight_kg": load["weight_kg"],
        "destination": load["destination"],
        "priority": load["priority"],
        "last_updated": get_current_time_str(),
        "source": "warehouse_management_system"
    }

@app.get("/api/v1/loads/stream")
async def stream_load_updates():
    """
    Server-Sent Events endpoint for real-time load updates

    Updates broadcast every 30-60 seconds
    """
    async def event_generator():
        logger.info("Client connected to SSE stream")
        try:
            while True:
                # Wait 30-60 seconds between updates
                await asyncio.sleep(random.randint(30, 60))

                # Generate update
                update = simulate_load_update()

                logger.info(f"Broadcasting update: {update['load_id']} -> {update['status']}")

                # Yield SSE formatted data
                yield {
                    "event": "load_update",
                    "data": json.dumps(update)
                }
        except asyncio.CancelledError:
            logger.info("Client disconnected from SSE stream")
            raise

    return EventSourceResponse(event_generator())

# ============================================================================
# Inventory Endpoints
# ============================================================================

@app.get("/api/v1/inventory")
async def list_inventory():
    """List all inventory items"""
    return {
        "items": [
            {
                "sku": sku,
                **item,
                "last_updated": get_current_time_str()
            }
            for sku, item in INVENTORY.items()
        ],
        "total_items": len(INVENTORY),
        "source": "inventory_management_system"
    }

@app.get("/api/v1/inventory/{sku}")
async def get_inventory(sku: str):
    """
    Get inventory levels for a specific SKU

    Example: GET /api/v1/inventory/SKU-001
    """
    if sku not in INVENTORY:
        raise HTTPException(status_code=404, detail=f"SKU {sku} not found")

    item = INVENTORY[sku]

    # Check if below reorder level
    needs_reorder = item["quantity"] < item["reorder_level"]

    return {
        "sku": sku,
        "name": item["name"],
        "quantity": item["quantity"],
        "location": item["location"],
        "unit_price": item["unit_price"],
        "total_value": item["quantity"] * item["unit_price"],
        "reorder_level": item["reorder_level"],
        "needs_reorder": needs_reorder,
        "supplier": item["supplier"],
        "last_updated": get_current_time_str(),
        "source": "inventory_management_system"
    }

# ============================================================================
# Equipment Endpoints
# ============================================================================

@app.get("/api/v1/equipment")
async def list_equipment():
    """List all equipment"""
    return {
        "equipment": [
            {
                "equipment_id": eq_id,
                **eq,
                "last_updated": get_current_time_str()
            }
            for eq_id, eq in EQUIPMENT.items()
        ],
        "total_count": len(EQUIPMENT),
        "source": "equipment_tracking_system"
    }

@app.get("/api/v1/equipment/{equipment_id}")
async def get_equipment_status(equipment_id: str):
    """
    Get equipment status and maintenance info

    Example: GET /api/v1/equipment/FORK-001
    """
    if equipment_id not in EQUIPMENT:
        raise HTTPException(status_code=404, detail=f"Equipment {equipment_id} not found")

    eq = EQUIPMENT[equipment_id]

    # Calculate days until next maintenance
    next_maint = datetime.fromisoformat(eq["next_maintenance"])
    days_until_maintenance = (next_maint - datetime.now()).days

    return {
        "equipment_id": equipment_id,
        "name": eq["name"],
        "status": eq["status"],
        "location": eq["location"],
        "last_maintenance": eq["last_maintenance"],
        "next_maintenance": eq["next_maintenance"],
        "days_until_maintenance": days_until_maintenance,
        "operator": eq["operator"],
        "last_updated": get_current_time_str(),
        "source": "equipment_tracking_system",
        **{k: v for k, v in eq.items() if k not in ["name", "status", "location", "last_maintenance", "next_maintenance", "operator"]}
    }

# ============================================================================
# Run Application
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
