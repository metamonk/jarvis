# Jarvis Mock Company API

A realistic warehouse/manufacturing API simulator for Jarvis voice assistant demos.

## Features

- **Load Tracking:** Real-time load status, location, and scheduling
- **Inventory Management:** SKU tracking with reorder alerts
- **Equipment Monitoring:** Equipment status and maintenance schedules
- **Server-Sent Events:** Real-time updates every 30-60 seconds
- **RESTful API:** Clean JSON responses with full metadata

## Endpoints

### Health & Info
- `GET /` - API information
- `GET /health` - Health check

### Loads
- `GET /api/v1/loads` - List all loads
- `GET /api/v1/loads/{load_id}` - Get specific load status
- `GET /api/v1/loads/stream` - SSE stream for real-time updates

### Inventory
- `GET /api/v1/inventory` - List all inventory items
- `GET /api/v1/inventory/{sku}` - Get specific SKU details

### Equipment
- `GET /api/v1/equipment` - List all equipment
- `GET /api/v1/equipment/{equipment_id}` - Get specific equipment status

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
python main.py

# Or with uvicorn
uvicorn main:app --reload --port 8000
```

Server runs at `http://localhost:8000`

## Docker

```bash
# Build
docker build -t jarvis-mock-api .

# Run
docker run -p 8000:8000 jarvis-mock-api
```

## Deploy to Fly.io (Recommended)

### Prerequisites
- Install Fly.io CLI: `curl -L https://fly.io/install.sh | sh`
- Sign up: `fly auth signup` (or login: `fly auth login`)

### Deployment

```bash
# From this directory
cd mock-company-api

# Launch app (first time)
fly launch --no-deploy

# Deploy
fly deploy

# Check status
fly status

# View logs
fly logs

# Get public URL
fly apps list
```

Your API will be available at: `https://jarvis-mock-api.fly.dev`

### Fly.io Configuration

- **Region:** `dfw` (Dallas - closest to Austin, TX)
- **Memory:** 256MB (sufficient for mock API)
- **Always-on:** Yes (required for SSE streaming)
- **Cost:** FREE (within free tier limits)

## Alternative: Deploy to Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize
railway init

# Deploy
railway up

# Get URL
railway domain
```

## Example Usage

### Get Load Status
```bash
curl https://jarvis-mock-api.fly.dev/api/v1/loads/2314
```

Response:
```json
{
  "load_id": "2314",
  "location": "Bay 3",
  "status": "ready_for_pickup",
  "scheduled_time": "4:00 PM",
  "weight_kg": 1250,
  "destination": "Distribution Center Alpha",
  "priority": "high",
  "last_updated": "2025-11-18T10:30:00.123456",
  "source": "warehouse_management_system"
}
```

### Stream Real-Time Updates
```bash
curl -N https://jarvis-mock-api.fly.dev/api/v1/loads/stream
```

Response (SSE):
```
event: load_update
data: {"load_id":"2315","location":"Bay 5","status":"in_transit","scheduled_time":"5:30 PM","timestamp":"2025-11-18T10:31:00.123456","priority":"medium"}

event: load_update
data: {"load_id":"2314","location":"Bay 3","status":"delivered","scheduled_time":"4:00 PM","timestamp":"2025-11-18T10:32:00.123456","priority":"high"}
```

### Get Inventory Item
```bash
curl https://jarvis-mock-api.fly.dev/api/v1/inventory/SKU-001
```

Response:
```json
{
  "sku": "SKU-001",
  "name": "Hydraulic Pump Assembly",
  "quantity": 45,
  "location": "Warehouse A-12",
  "unit_price": 450.0,
  "total_value": 20250.0,
  "reorder_level": 20,
  "needs_reorder": false,
  "supplier": "Industrial Parts Co",
  "last_updated": "2025-11-18T10:30:00.123456",
  "source": "inventory_management_system"
}
```

## Integration with Jarvis

Update your Jarvis backend environment:

```bash
# .env
COMPANY_API_URL=https://jarvis-mock-api.fly.dev
```

No API key needed for mock API!

## Mock Data

### Loads
- 5 sample loads with various statuses
- Locations: Bay 1-5, Loading Dock A, Storage Zones
- Statuses: loading, ready_for_pickup, in_transit, delivered, delayed

### Inventory
- 5 sample SKUs (pumps, brackets, motors, safety equipment, batteries)
- Quantities from 8-230 units
- Prices from $12.50 to $2,200

### Equipment
- 4 pieces of equipment (2 forklifts, 1 crane, 1 conveyor)
- Statuses: operational, maintenance
- Maintenance tracking with next service dates

## Customization

Edit `main.py` to:
- Add more loads, inventory items, or equipment
- Change update frequency (default: 30-60 seconds)
- Modify data fields and structure
- Add new endpoints

## Monitoring

```bash
# Fly.io monitoring
fly dashboard

# View real-time logs
fly logs -a jarvis-mock-api

# Check metrics
fly metrics -a jarvis-mock-api
```

## Troubleshooting

### SSE not working
- Ensure `auto_stop_machines = false` in fly.toml
- Check that client supports Server-Sent Events
- Verify CORS headers allow your origin

### Slow responses
- Check Fly.io region (should be `dfw` for Austin, TX)
- Verify machine is running: `fly status`
- Check logs for errors: `fly logs`

## Cost

**Fly.io Free Tier includes:**
- 3 shared-cpu-1x VMs with 256MB RAM each
- 160GB outbound data transfer
- This mock API uses 1 VM = FREE ✅

## Production Notes

This is a **mock API for demos only**. For production:
- Replace with real company API
- Add authentication
- Implement rate limiting
- Add proper logging and monitoring
- Use production database instead of in-memory data

## License

MIT - Part of the Jarvis MVP project
