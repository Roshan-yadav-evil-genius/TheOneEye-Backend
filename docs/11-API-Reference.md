# API Reference

This document provides comprehensive API endpoint documentation for the Workflow Orchestrator backend system.

## Navigation

- [← Back to Development Documentation](Development.md)
- [← Previous: Development Workflow](10-Development-Workflow.md)
- [Next: Webhook Node →](12-Webhook-Node.md)

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

**Endpoint**: `GET /api/workflow/{workflow_id}/start_execution/`

**Response**: `200 OK`
```json
{
  "task_id": "celery-task-id-123",
  "status": "PENDING"
}
```

**Description**:
- Starts workflow execution as a Celery task
- Returns task ID for status tracking
- Execution happens asynchronously via Celery
- Workflow configuration is loaded from database

### Stop Workflow Execution

Stop a running workflow.

**Endpoint**: `GET /api/workflow/{workflow_id}/stop_execution/`

**Response**: `200 OK`
```json
{
  "task_id": "celery-task-id-456",
  "status": "REVOKED"
}
```

**Description**:
- Stops workflow execution via Celery task
- Returns task ID and final status
- Waits for task completion (default 5 seconds timeout)

### Get Task Status

Get the status of a workflow execution task.

**Endpoint**: `GET /api/workflow/{workflow_id}/task_status/`

**Response**: `200 OK`
```json
{
  "task_id": "celery-task-id-123",
  "status": "SUCCESS"
}
```

**Description**:
- Returns current Celery task status
- Status values: PENDING, STARTED, SUCCESS, FAILURE, REVOKED

## Node Execution API

### Execute and Save Node

Execute a single node and save execution data.

**Endpoint**: `POST /api/workflow/{workflow_id}/execute_and_save_node/`

**Request**:
```json
{
  "node_id": "node-uuid",
  "form_values": {
    "field_name": "value"
  },
  "input_data": {
    "key": "value"
  },
  "session_id": "optional-session-id"
}
```

**Response**: `200 OK`
```json
{
  "success": true,
  "node_id": "node-uuid",
  "node_type": "http-request",
  "input_data": {...},
  "form_values": {...},
  "output": {
    "data": {...}
  },
  "session_id": "session-id"
}
```

**Description**:
- Executes a single node with provided form values and input data
- Saves execution data to database (form_values, input_data, output_data)
- Supports session-based stateful execution
- Returns execution result with success status

## Workflow Management API

### Create Workflow

Create a new workflow.

**Endpoint**: `POST /api/workflow/`

**Request**:
```json
{
  "name": "My Workflow",
  "description": "Workflow description"
}
```

**Response**: `201 Created`
```json
{
  "id": "workflow-uuid",
  "name": "My Workflow",
  "created_at": "2024-01-01T12:00:00Z"
}
```

### Get Workflow

Get workflow details.

**Endpoint**: `GET /api/workflow/{workflow_id}/`

**Response**: `200 OK`
```json
{
  "id": "workflow-uuid",
  "name": "My Workflow",
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

### Update Workflow

Update an existing workflow.

**Endpoint**: `PUT /api/workflow/{workflow_id}/` or `PATCH /api/workflow/{workflow_id}/`

**Request**:
```json
{
  "name": "Updated Workflow"
}
```

**Response**: `200 OK`
```json
{
  "id": "workflow-uuid",
  "name": "Updated Workflow",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

### Delete Workflow

Delete a workflow.

**Endpoint**: `DELETE /api/workflow/{workflow_id}/`

**Response**: `204 No Content`

### List Workflows

Get list of all workflows.

**Endpoint**: `GET /api/workflow/`

**Response**: `200 OK`
```json
[
  {
    "id": "workflow-uuid",
    "name": "My Workflow",
    "created_at": "2024-01-01T12:00:00Z"
  }
]
```

### Get Canvas Data

Get workflow canvas data with full node information.

**Endpoint**: `GET /api/workflow/{workflow_id}/canvas_data/`

**Response**: `200 OK`
```json
{
  "id": "workflow-uuid",
  "nodes": [...],
  "edges": [...]
}
```

## Node Management API

### Add Node to Workflow

Add a node to the workflow canvas.

**Endpoint**: `POST /api/workflow/{workflow_id}/nodes/add/`

**Request**:
```json
{
  "nodeTemplate": "http-request",
  "position": {"x": 100, "y": 200},
  "form_values": {}
}
```

**Response**: `201 Created`
```json
{
  "id": "node-uuid",
  "node_type": "http-request",
  "position": {"x": 100, "y": 200}
}
```

### Get Node Input

Get aggregated input data from all connected source nodes.

**Endpoint**: `GET /api/workflow/{workflow_id}/nodes/{node_id}/input/`

**Response**: `200 OK`
```json
{
  "input_data": {...}
}
```

### Get Node Output

Get the output data for a node.

**Endpoint**: `GET /api/workflow/{workflow_id}/nodes/{node_id}/output/`

**Response**: `200 OK`
```json
{
  "output_data": {...}
}
```

### Update Node Position

Update node position in the workflow canvas.

**Endpoint**: `PATCH /api/workflow/{workflow_id}/nodes/{node_id}/position/`

**Request**:
```json
{
  "position": {"x": 150, "y": 250}
}
```

**Response**: `200 OK`
```json
{
  "id": "node-uuid",
  "position": {"x": 150, "y": 250}
}
```

### Remove Node

Remove a node from the workflow.

**Endpoint**: `DELETE /api/workflow/{workflow_id}/nodes/{node_id}/remove/`

**Response**: `200 OK`
```json
{
  "message": "Node removed successfully"
}
```

## WebSocket Events

Real-time workflow execution updates via WebSocket.

### Connection

**Endpoint**: `ws://127.0.0.1:7878/ws/workflow/{workflow_id}/`

**Connection Flow**:
1. Client connects to WebSocket endpoint
2. Server sends current workflow state on connection
3. Server broadcasts events as workflow executes
4. Client can send messages to request state updates

### Event Types

#### State Sync (On Connect)

Sent automatically when client connects or requests state.

```json
{
  "type": "state_sync",
  "state": {
    "workflow_id": "workflow-uuid",
    "status": "running",
    "executing_nodes": {
      "node_1": {
        "node_id": "node_1",
        "node_type": "http-request",
        "started_at": "2024-01-01T12:00:00Z",
        "duration_seconds": 1.5
      }
    },
    "completed_nodes": [
      {
        "node_id": "node_0",
        "node_type": "queue-reader",
        "completed_at": "2024-01-01T12:00:00Z",
        "duration_seconds": 0.5
      }
    ],
    "completed_count": 1
  }
}
```

#### Node Started

```json
{
  "type": "node_started",
  "workflow_id": "workflow-uuid",
  "node_id": "node_1",
  "node_type": "http-request"
}
```

#### Node Completed

```json
{
  "type": "node_completed",
  "workflow_id": "workflow-uuid",
  "node_id": "node_1",
  "node_type": "http-request",
  "route": "default"
}
```

#### Node Failed

```json
{
  "type": "node_failed",
  "workflow_id": "workflow-uuid",
  "node_id": "node_1",
  "node_type": "http-request",
  "error": "Connection timeout"
}
```

#### Workflow Completed

```json
{
  "type": "workflow_completed",
  "workflow_id": "workflow-uuid"
}
```

#### Workflow Failed

```json
{
  "type": "workflow_failed",
  "workflow_id": "workflow-uuid",
  "error": "Workflow execution failed"
}
```

### Client Messages

Clients can send messages to the WebSocket:

**Ping**:
```json
{"type": "ping"}
```

**Request State**:
```json
{"type": "request_state"}
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
curl -X POST http://127.0.0.1:7878/api/workflow/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Workflow"
  }'
```

**2. Add Nodes** (via frontend or API):
```bash
curl -X POST http://127.0.0.1:7878/api/workflow/{workflow_id}/nodes/add/ \
  -H "Content-Type: application/json" \
  -d '{
    "nodeTemplate": "http-request",
    "position": {"x": 100, "y": 200}
  }'
```

**3. Start Execution**:
```bash
curl -X GET http://127.0.0.1:7878/api/workflow/{workflow_id}/start_execution/
```

**4. Monitor via WebSocket**:
```javascript
const ws = new WebSocket('ws://127.0.0.1:7878/ws/workflow/{workflow_id}/');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.type, data);
};
```

### Node Execution

**Execute Single Node**:
```bash
curl -X POST http://127.0.0.1:7878/api/workflow/{workflow_id}/execute_and_save_node/ \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "node-uuid",
    "form_values": {"url": "https://api.example.com"},
    "input_data": {"key": "value"}
  }'
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

[← Back to Development Documentation](Development.md) | [← Previous: Development Workflow](10-Development-Workflow.md) | [Next: Webhook Node →](12-Webhook-Node.md)

