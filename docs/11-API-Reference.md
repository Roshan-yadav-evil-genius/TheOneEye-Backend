# API Reference

This document provides comprehensive API endpoint documentation for the Workflow Orchestrator backend system.

## Navigation

- [← Back to Development Documentation](Development.md)
- [← Previous: Development Workflow](10-Development-Workflow.md)

## Overview

The API provides endpoints for:
- Workflow management (create, update, delete)
- Production mode execution
- Development mode execution
- Node discovery and metadata
- Real-time workflow monitoring

## Base URL

```
http://127.0.0.1:7878/api
```

## Authentication

Most endpoints require authentication. Include authentication tokens in request headers:

```
Authorization: Bearer <token>
```

## Production Mode API

### Start Workflow Execution

Start a workflow in Production Mode.

**Endpoint**: `POST /api/workflows/{workflow_id}/start`

**Request**:
```json
{
  "workflow_json": {
    "nodes": [...],
    "edges": [...]
  }
}
```

**Response**: `200 OK`
```json
{
  "status": "started",
  "workflow_id": "workflow_123",
  "runners": 2
}
```

**Description**:
- Loads workflow from JSON
- Creates FlowRunners for each ProducerNode
- Starts all loops concurrently
- Returns immediately (execution continues asynchronously)

### Stop Workflow Execution

Stop a running workflow.

**Endpoint**: `POST /api/workflows/{workflow_id}/stop`

**Response**: `200 OK`
```json
{
  "status": "stopped",
  "workflow_id": "workflow_123"
}
```

**Description**:
- Gracefully stops all FlowRunners
- Waits for current iterations to complete
- Releases resources

### Force Shutdown

Forcefully terminate workflow execution.

**Endpoint**: `POST /api/workflows/{workflow_id}/force-shutdown`

**Response**: `200 OK`
```json
{
  "status": "force_shutdown",
  "workflow_id": "workflow_123"
}
```

**Description**:
- Immediately cancels all running tasks
- Does not wait for completion
- Use only when necessary

## Development Mode API

### Execute Single Node

Execute a single node in Development Mode.

**Endpoint**: `POST /api/dev/execute`

**Request**:
```json
{
  "node_id": "node_1",
  "input_data": {
    "key": "value"
  }
}
```

**Response**: `200 OK`
```json
{
  "node_id": "node_1",
  "output": {
    "result": "processed_data"
  },
  "execution_time": 0.123
}
```

**Description**:
- Executes single node with provided input
- Uses Redis cache for dependency resolution
- Stores output in cache for downstream nodes
- Returns node output immediately

### Get Cached Output

Get cached output from a previously executed node.

**Endpoint**: `GET /api/dev/cache/{node_id}`

**Response**: `200 OK`
```json
{
  "node_id": "node_1",
  "output": {
    "data": "cached_data"
  },
  "cached_at": "2024-01-01T12:00:00Z"
}
```

**Description**:
- Retrieves cached node output
- Used for debugging and inspection
- Returns `404` if not found

### Clear Cache

Clear all cached node outputs.

**Endpoint**: `DELETE /api/dev/cache`

**Response**: `200 OK`
```json
{
  "status": "cleared",
  "cleared_keys": 5
}
```

**Description**:
- Clears all development mode cache entries
- Useful for starting fresh debugging session

## Workflow Management API

### Create Workflow

Create a new workflow.

**Endpoint**: `POST /api/workflows`

**Request**:
```json
{
  "name": "My Workflow",
  "description": "Workflow description",
  "workflow_json": {
    "nodes": [...],
    "edges": [...]
  }
}
```

**Response**: `201 Created`
```json
{
  "id": "workflow_123",
  "name": "My Workflow",
  "created_at": "2024-01-01T12:00:00Z"
}
```

### Get Workflow

Get workflow details.

**Endpoint**: `GET /api/workflows/{workflow_id}`

**Response**: `200 OK`
```json
{
  "id": "workflow_123",
  "name": "My Workflow",
  "workflow_json": {...},
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

### Update Workflow

Update an existing workflow.

**Endpoint**: `PUT /api/workflows/{workflow_id}`

**Request**:
```json
{
  "name": "Updated Workflow",
  "workflow_json": {...}
}
```

**Response**: `200 OK`
```json
{
  "id": "workflow_123",
  "name": "Updated Workflow",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

### Delete Workflow

Delete a workflow.

**Endpoint**: `DELETE /api/workflows/{workflow_id}`

**Response**: `204 No Content`

### List Workflows

Get list of all workflows.

**Endpoint**: `GET /api/workflows`

**Response**: `200 OK`
```json
{
  "workflows": [
    {
      "id": "workflow_123",
      "name": "My Workflow",
      "created_at": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 10
}
```

## Node Discovery API

### Get Available Nodes

Get list of all available node types.

**Endpoint**: `GET /api/nodes`

**Response**: `200 OK`
```json
{
  "nodes": [
    {
      "identifier": "http-request",
      "label": "HTTP Request",
      "description": "Makes an HTTP request",
      "type": "BlockingNode",
      "execution_pool": "ASYNC",
      "form_schema": {...}
    }
  ]
}
```

### Get Node Details

Get detailed information about a specific node type.

**Endpoint**: `GET /api/nodes/{node_identifier}`

**Response**: `200 OK`
```json
{
  "identifier": "http-request",
  "label": "HTTP Request",
  "description": "Makes an HTTP request to a specified URL",
  "type": "BlockingNode",
  "execution_pool": "ASYNC",
  "form_schema": {
    "fields": [...]
  },
  "examples": [...]
}
```

## WebSocket Events

Real-time workflow execution updates via WebSocket.

### Connection

**Endpoint**: `ws://127.0.0.1:7878/ws/workflow/{workflow_id}`

### Event Types

#### Node Started

```json
{
  "type": "node_started",
  "workflow_id": "workflow_123",
  "node_id": "node_1",
  "node_type": "http-request",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### Node Completed

```json
{
  "type": "node_completed",
  "workflow_id": "workflow_123",
  "node_id": "node_1",
  "node_type": "http-request",
  "route": "default",
  "output_data": {...},
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### Node Failed

```json
{
  "type": "node_failed",
  "workflow_id": "workflow_123",
  "node_id": "node_1",
  "node_type": "http-request",
  "error": "Connection timeout",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### Workflow Started

```json
{
  "type": "workflow_started",
  "workflow_id": "workflow_123",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### Workflow Completed

```json
{
  "type": "workflow_completed",
  "workflow_id": "workflow_123",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### Workflow Failed

```json
{
  "type": "workflow_failed",
  "workflow_id": "workflow_123",
  "error": "Workflow execution failed",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## Error Responses

### Standard Error Format

```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": {...}
}
```

### Common Error Codes

| Status Code | Error Code | Description |
|-------------|------------|-------------|
| 400 | `INVALID_REQUEST` | Invalid request format |
| 404 | `NOT_FOUND` | Resource not found |
| 422 | `VALIDATION_ERROR` | Validation failed |
| 500 | `INTERNAL_ERROR` | Internal server error |

### Validation Error Example

```json
{
  "error": "Workflow validation failed",
  "code": "VALIDATION_ERROR",
  "details": {
    "node_1": {
      "field_name": ["This field is required."]
    }
  }
}
```

## Request/Response Examples

### Complete Workflow Execution

**1. Create Workflow**:
```bash
curl -X POST http://127.0.0.1:7878/api/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Workflow",
    "workflow_json": {
      "nodes": [
        {"id": "node_1", "type": "queue-reader", "data": {...}},
        {"id": "node_2", "type": "http-request", "data": {...}}
      ],
      "edges": [
        {"source": "node_1", "target": "node_2"}
      ]
    }
  }'
```

**2. Start Execution**:
```bash
curl -X POST http://127.0.0.1:7878/api/workflows/workflow_123/start \
  -H "Content-Type: application/json"
```

**3. Monitor via WebSocket**:
```javascript
const ws = new WebSocket('ws://127.0.0.1:7878/ws/workflow/workflow_123');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.type, data);
};
```

### Development Mode Execution

**1. Execute Node**:
```bash
curl -X POST http://127.0.0.1:7878/api/dev/execute \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "node_1",
    "input_data": {
      "key": "value"
    }
  }'
```

**2. Check Cache**:
```bash
curl http://127.0.0.1:7878/api/dev/cache/node_1
```

**3. Clear Cache**:
```bash
curl -X DELETE http://127.0.0.1:7878/api/dev/cache
```

## Rate Limiting

API endpoints may be rate-limited. Check response headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1609459200
```

## Related Documentation

- [Workflow Engine](02-Workflow-Engine.md) - Core orchestration
- [Execution System](03-Execution-System.md) - Execution details
- [Development Workflow](10-Development-Workflow.md) - Development practices

---

[← Back to Development Documentation](Development.md) | [← Previous: Development Workflow](10-Development-Workflow.md)

