# Adding New Nodes

This guide provides step-by-step instructions for creating new nodes to extend the workflow system. Follow this guide to add custom functionality to the platform.

## Navigation

- [← Back to Development Documentation](Development.md)
- [← Previous: Post-Processing](08-Post-Processing.md)
- [Next: Development Workflow →](10-Development-Workflow.md)

## Overview

Adding a new node involves:
1. Choosing the appropriate node type
2. Creating the node directory structure
3. Implementing the form
4. Implementing the node class
5. Testing the node

## Step 1: Choose Node Type

Select the appropriate base class based on your node's behavior:

| Node Type | Use When | Example |
|-----------|----------|---------|
| **ProducerNode** | Starts loop iterations | QueueReader, TimerNode |
| **BlockingNode** | Sequential operations | HttpRequestNode, DatabaseQueryNode |
| **NonBlockingNode** | Async boundaries, non-blocking | QueueWriter, NotificationNode |
| **ConditionalNode** | Conditional branching | IfCondition, CompareNode |

## Step 2: Create Node Directory

Create a directory structure in `backend/core/Node/Nodes/`:

```
backend/core/Node/Nodes/
└── YourCategory/
    └── YourNode/
        ├── __init__.py
        ├── form.py
        └── node.py
```

**Example**:
```
backend/core/Node/Nodes/
└── Data/
    └── DataTransformNode/
        ├── __init__.py
        ├── form.py
        └── node.py
```

## Step 3: Create Form

Define the configuration form in `form.py`:

```python
from Node.Core.Form.Core.BaseForm import BaseForm
from django import forms

class YourNodeForm(BaseForm):
    """Form for configuring YourNode."""
    
    # Define form fields
    field_name = forms.CharField(
        label="Field Label",
        required=True,
        help_text="Field description"
    )
    
    # Optional: Cascading dependencies
    def get_field_dependencies(self):
        return {
            'parent_field': ['child_field']
        }
    
    def populate_field(self, field_name, parent_value):
        if field_name == 'child_field':
            return get_choices_for_parent(parent_value)
        return []
```

### Form Field Types

- `CharField`: Text input
- `ChoiceField`: Select dropdown
- `IntegerField`: Number input
- `BooleanField`: Checkbox
- `EmailField`: Email input
- `URLField`: URL input
- `TextField`: Textarea

### Jinja Template Support

Fields can contain Jinja templates for dynamic values:

```python
url = forms.CharField(
    label="URL",
    help_text="Use {{ data.key }} for dynamic values"
)
```

## Step 4: Implement Node Class

Create the node implementation in `node.py`:

```python
from Node.Core.Node.Core.BaseNode import BlockingNode  # or appropriate type
from Node.Core.Node.Core.Data import NodeOutput, PoolType
from typing import Optional
from .form import YourNodeForm

class YourNode(BlockingNode):
    """Your node description."""
    
    @classmethod
    def identifier(cls) -> str:
        """Unique identifier for this node type."""
        return "your-node"  # Use kebab-case
    
    @property
    def execution_pool(self) -> PoolType:
        """Preferred execution pool."""
        return PoolType.ASYNC  # or THREAD, PROCESS
    
    @property
    def label(self) -> str:
        """Display name for UI."""
        return "Your Node"
    
    @property
    def description(self) -> str:
        """Node description."""
        return "What this node does"
    
    def get_form(self) -> Optional[YourNodeForm]:
        """Return the configuration form."""
        return YourNodeForm()
    
    async def setup(self):
        """Initialize resources (connections, clients, etc.)."""
        # Initialize HTTP clients, DB connections, etc.
        pass
    
    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        """Core business logic."""
        # Get form values
        field_value = self.form.get_field_value("field_name")
        
        # Access previous node data
        previous_data = node_data.data.get("key")
        
        # Perform operation
        result = await self._do_work(field_value, previous_data)
        
        # Return output
        return NodeOutput(
            data={
                "result": result,
                "your_key": "your_value"
            }
        )
    
    async def cleanup(self, node_data: Optional[NodeOutput] = None):
        """Clean up resources."""
        # Close connections, release resources
        pass
    
    async def _do_work(self, field_value, previous_data):
        """Helper method for business logic."""
        # Implementation
        pass
```

### Required Methods

| Method | Required | Purpose |
|--------|----------|---------|
| `identifier()` | Yes | Unique node type identifier |
| `execution_pool` | Yes | Preferred execution pool |
| `get_form()` | Optional | Configuration form |
| `setup()` | Optional | Resource initialization |
| `execute()` | Yes | Core business logic |
| `cleanup()` | Optional | Resource cleanup |

### Node Properties

```python
@property
def label(self) -> str:
    """Display name for UI."""
    return "Your Node"

@property
def description(self) -> str:
    """Node description for documentation."""
    return "What this node does"

@property
def icon(self) -> str:
    """Icon identifier for UI."""
    return "icon-name"
```

## Step 5: Export Node

Export the node in `__init__.py`:

```python
from .node import YourNode

__all__ = ['YourNode']
```

## Step 6: Node Registration

Nodes are **automatically discovered** by NodeRegistry. No manual registration needed!

**Requirements**:
- Node must be in `Node.Nodes` package tree
- Node must inherit from ProducerNode, BlockingNode, or NonBlockingNode
- Node must implement `identifier()` classmethod

## Step 7: Testing

### Manual Testing

1. **Start Development Server**:
   ```bash
   conda activate theoneeye
   cd backend
   python manage.py runserver 7878
   ```

2. **Test Node Discovery**:
   - Check API endpoint for available nodes
   - Verify your node appears in the list

3. **Test Node Execution**:
   - Create a workflow with your node
   - Test in Development Mode
   - Verify output data

### Unit Testing

Create tests in `backend/core/Node/Nodes/YourCategory/YourNode/tests.py`:

```python
import pytest
from Node.Core.Node.Core.Data import NodeConfig, NodeOutput
from .node import YourNode

@pytest.mark.asyncio
async def test_your_node_execution():
    """Test node execution."""
    config = NodeConfig(
        id="test_node",
        type="your-node",
        data={
            "form": {
                "field_name": "test_value"
            },
            "config": {}
        }
    )
    
    node = YourNode(config)
    await node.init()
    
    input_data = NodeOutput(data={"key": "value"})
    output = await node.run(input_data)
    
    assert output.data["result"] == expected_result
```

## Complete Example

### Example: HTTP Request Node

**Directory Structure**:
```
backend/core/Node/Nodes/
└── System/
    └── HttpRequestNode/
        ├── __init__.py
        ├── form.py
        └── node.py
```

**form.py**:
```python
from Node.Core.Form.Core.BaseForm import BaseForm
from django import forms

class HttpRequestForm(BaseForm):
    url = forms.URLField(
        label="URL",
        required=True,
        help_text="The URL to request"
    )
    
    method = forms.ChoiceField(
        label="Method",
        choices=[("GET", "GET"), ("POST", "POST"), ("PUT", "PUT"), ("DELETE", "DELETE")],
        initial="GET"
    )
    
    headers = forms.JSONField(
        label="Headers",
        required=False,
        help_text="JSON object with HTTP headers"
    )
```

**node.py**:
```python
import aiohttp
from Node.Core.Node.Core.BaseNode import BlockingNode
from Node.Core.Node.Core.Data import NodeOutput, PoolType
from typing import Optional
from .form import HttpRequestForm

class HttpRequestNode(BlockingNode):
    @classmethod
    def identifier(cls) -> str:
        return "http-request"
    
    @property
    def execution_pool(self) -> PoolType:
        return PoolType.ASYNC
    
    @property
    def label(self) -> str:
        return "HTTP Request"
    
    @property
    def description(self) -> str:
        return "Makes an HTTP request to a specified URL"
    
    def get_form(self) -> Optional[HttpRequestForm]:
        return HttpRequestForm()
    
    async def setup(self):
        self.client = aiohttp.ClientSession()
    
    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        url = self.form.get_field_value("url")
        method = self.form.get_field_value("method")
        headers = self.form.get_field_value("headers") or {}
        
        async with self.client.request(method, url, headers=headers) as response:
            data = await response.json()
            
            return NodeOutput(
                data={
                    "status": response.status,
                    "response": data,
                    "headers": dict(response.headers)
                }
            )
    
    async def cleanup(self, node_data: Optional[NodeOutput] = None):
        if hasattr(self, 'client'):
            await self.client.close()
```

**__init__.py**:
```python
from .node import HttpRequestNode

__all__ = ['HttpRequestNode']
```

## Best Practices

### Node Design

1. **Single Responsibility**: Each node should do one thing well
2. **Clear Purpose**: Node purpose should be immediately clear
3. **Proper Type**: Choose correct node type (Producer, Blocking, NonBlocking, Conditional)
4. **Error Handling**: Handle errors gracefully, don't crash the loop

### Form Design

1. **Use Dependencies**: Define cascading dependencies for related fields
2. **Support Templates**: Allow Jinja templates for dynamic values
3. **Clear Validation**: Provide clear error messages
4. **Default Values**: Set sensible defaults where possible

### Resource Management

1. **Initialize in setup()**: Don't initialize resources in `__init__()`
2. **Clean up in cleanup()**: Release resources properly
3. **Handle Errors**: Ensure cleanup happens even on errors

### Execution Pool Selection

- **ASYNC**: HTTP requests, database operations, file I/O
- **THREAD**: CPU-bound tasks that can release GIL
- **PROCESS**: CPU-intensive Python code requiring true parallelism

## Troubleshooting

### Node Not Discovered

- Check that node is in `Node.Nodes` package tree
- Verify `identifier()` is implemented
- Check that node inherits from correct base class
- Restart server to refresh registry

### Form Validation Errors

- Check field definitions
- Verify required fields are set
- Check Jinja template syntax
- Review form validation logic

### Execution Errors

- Check resource initialization in `setup()`
- Verify async/await usage
- Check error handling
- Review execution pool selection

## Related Documentation

- [Node System](04-Node-System.md) - Node architecture and lifecycle
- [Form System](07-Form-System.md) - Form architecture and usage
- [Execution System](03-Execution-System.md) - How nodes are executed
- [Development Workflow](10-Development-Workflow.md) - Development practices

---

[← Back to Development Documentation](Development.md) | [← Previous: Post-Processing](08-Post-Processing.md) | [Next: Development Workflow →](10-Development-Workflow.md)

