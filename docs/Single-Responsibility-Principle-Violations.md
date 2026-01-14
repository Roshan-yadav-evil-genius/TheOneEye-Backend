# Single Responsibility Principle Violations

## Table of Contents

1. [Introduction](#introduction)
2. [Violations Catalog](#violations-catalog)
   - [Violation 1: BaseNode Multiple Responsibilities](#violation-1-basenode-multiple-responsibilities)
   - [Violation 2: NodeExecutionService Mixed Concerns](#violation-2-nodeexecutionservice-mixed-concerns)
   - [Violation 3: NodeExecutor Overloaded Responsibilities](#violation-3-nodeexecutor-overloaded-responsibilities)
   - [Violation 4: FlowEngine Orchestration and Implementation](#violation-4-flowengine-orchestration-and-implementation)
   - [Violation 5: FlowRunner Execution and Event Management](#violation-5-flowrunner-execution-and-event-management)
   - [Violation 6: VideoStreamConsumer Multiple Concerns](#violation-6-videostreamconsumer-multiple-concerns)
   - [Violation 7: BaseForm Validation and Dependency Management](#violation-7-baseform-validation-and-dependency-management)
   - [Violation 8: BaseManager Validation and Error Handling](#violation-8-basemanager-validation-and-error-handling)
3. [Implementation Guidelines](#implementation-guidelines)
4. [Priority Ranking](#priority-ranking)
5. [Developer Checklist](#developer-checklist)

---

## Introduction

### What is Single Responsibility Principle?

The **Single Responsibility Principle (SRP)** is one of the SOLID principles of object-oriented design. It states:

> **A class should have only one reason to change.**

This means:
- **One Responsibility**: Each class should have one, and only one, reason to change
- **Focused Purpose**: A class should do one thing and do it well
- **Cohesive Behavior**: All methods in a class should be related to a single purpose
- **Clear Boundaries**: Responsibilities should be clearly separated between classes

### Why It Matters

Violating SRP leads to:

- **High Coupling**: Changes to one responsibility affect other responsibilities
- **Low Cohesion**: Unrelated methods are grouped together
- **Difficult Testing**: Hard to test individual responsibilities in isolation
- **Maintenance Burden**: Changes ripple through multiple concerns
- **Code Duplication**: Similar logic appears in multiple places
- **Reduced Reusability**: Classes cannot be reused for single responsibilities

### How Violations Impact the Codebase

1. **Maintenance Challenges**: Changes to one responsibility require understanding and modifying unrelated code
2. **Testing Complexity**: Cannot test responsibilities independently
3. **Bug Propagation**: Bugs in one responsibility can affect others
4. **Code Reusability**: Cannot reuse specific functionality without bringing in unrelated code
5. **Developer Confusion**: Unclear what a class is responsible for

---

## Violations Catalog

### Violation 1: BaseNode Multiple Responsibilities

**Location**: `core/Node/Core/Node/Core/BaseNode.py:35-305`

#### Current Implementation (Before)

```python
class BaseNode(BaseNodeProperty, BaseNodeMethod, ABC):
    """
    Base node class that handles:
    1. Form population and validation
    2. Jinja template rendering
    3. Node execution coordination
    4. Form validation error extraction
    5. Output key generation
    """
    
    def __init__(self, node_config: NodeConfig):
        self.node_config = node_config
        self.form = self.get_form()
        self._populate_form()  # ❌ Form management
        self.execution_count = 0
    
    def _populate_form(self):
        """Populate the form with the data from the config."""  # ❌ Form management
        if self.form is not None:
            for key, value in self.node_config.data.form.items():
                self.form.update_field(key, value)
    
    def is_ready(self) -> bool:
        """Validate that the node has all required config fields."""  # ❌ Validation
        if self.form is None:
            return True
        return self._validate_template_fields()
    
    def _validate_template_fields(self) -> bool:
        """Validate form fields, handling Jinja templates specially."""  # ❌ Validation
        # ... validation logic ...
    
    def _extract_clean_error_messages(self, form) -> str:
        """Extract clean error messages from Django form errors."""  # ❌ Error formatting
        # ... error formatting logic ...
    
    def populate_form_values(self, node_data: NodeOutput) -> None:
        """Render Jinja templates in form fields with runtime data."""  # ❌ Template rendering
        from jinja2 import Template
        # ... Jinja template rendering logic ...
        # ... Form validation after rendering ...
    
    async def run(self, node_data: NodeOutput) -> NodeOutput:
        """Main entry point for node execution."""  # ❌ Execution coordination
        if isinstance(node_data, ExecutionCompleted):
            await self.cleanup(node_data)
            return node_data
        
        self.populate_form_values(node_data)  # ❌ Calls template rendering
        output = await self.execute(node_data)  # ❌ Execution
        self.execution_count += 1
        return output
    
    def get_unique_output_key(self, node_data: NodeOutput, base_key: str) -> str:
        """Generate a unique output key for this node's data."""  # ❌ Data transformation
        # ... key generation logic ...
```

#### Problem

`BaseNode` violates SRP by handling multiple distinct responsibilities:

1. **Form Management**: Populating forms, updating fields, managing form state
2. **Validation**: Validating form fields, checking template fields, validating readiness
3. **Template Rendering**: Rendering Jinja templates in form fields
4. **Execution Coordination**: Orchestrating the execution flow (populate → execute → track)
5. **Error Formatting**: Extracting and formatting error messages
6. **Data Transformation**: Generating unique output keys

Each of these responsibilities can change independently:
- Form management changes don't affect template rendering
- Validation logic changes don't affect execution coordination
- Template rendering changes don't affect error formatting

#### Solution Approach

1. **Extract Form Manager**: Create `NodeFormManager` for form population and updates
2. **Extract Validator**: Create `NodeValidator` for validation logic
3. **Extract Template Renderer**: Create `TemplateRenderer` for Jinja template rendering
4. **Extract Execution Coordinator**: Create `NodeExecutionCoordinator` for execution flow
5. **Extract Error Formatter**: Create `ErrorFormatter` for error message extraction
6. **Extract Data Transformer**: Create `OutputKeyGenerator` for key generation

#### Refactored Implementation (After)

```python
# Form Management - Separate class
class NodeFormManager:
    """Manages form population and field updates for nodes."""
    
    def __init__(self, form: Optional[BaseForm], node_config: NodeConfig):
        self.form = form
        self.node_config = node_config
    
    def populate_from_config(self):
        """Populate form with data from node config."""
        if self.form is None:
            return
        for key, value in self.node_config.data.form.items():
            self.form.update_field(key, value)
    
    def update_field(self, field_name: str, value: Any):
        """Update a form field value."""
        if self.form:
            self.form.update_field(field_name, value)

# Validation - Separate class
class NodeValidator:
    """Validates node configuration and form fields."""
    
    def __init__(self, form: Optional[BaseForm], node_config: NodeConfig):
        self.form = form
        self.node_config = node_config
    
    def is_ready(self) -> bool:
        """Check if node is ready for execution."""
        if self.form is None:
            return True
        return self._validate_template_fields()
    
    def _validate_template_fields(self) -> bool:
        """Validate form fields, handling Jinja templates."""
        # ... validation logic ...
        pass

# Template Rendering - Separate class
class TemplateRenderer:
    """Renders Jinja templates in form fields."""
    
    @staticmethod
    def render_in_form(form: BaseForm, node_data: NodeOutput, node_config: NodeConfig):
        """Render Jinja templates in form fields with runtime data."""
        from jinja2 import Template
        
        form_data = node_config.data.form or {}
        for field_name in form.fields:
            if field_name in form_data:
                raw_value = form_data.get(field_name)
                if raw_value is not None and contains_jinja_template(str(raw_value)):
                    template = Template(str(raw_value))
                    rendered_value = template.render(data=node_data.data)
                    form.update_field(field_name, rendered_value)
                else:
                    form.update_field(field_name, raw_value)

# Error Formatting - Separate class
class ErrorFormatter:
    """Formats error messages from forms."""
    
    @staticmethod
    def extract_clean_error_messages(form: BaseForm) -> str:
        """Extract clean error messages from Django form errors."""
        error_messages = []
        for field_name, errors in form.errors.items():
            for error in errors:
                if field_name == '__all__':
                    error_messages.append(str(error))
                else:
                    error_messages.append(f"{field_name}: {str(error)}")
        return "; ".join(error_messages) if error_messages else "Form validation failed"

# Data Transformation - Separate class
class OutputKeyGenerator:
    """Generates unique output keys for node data."""
    
    @staticmethod
    def get_unique_key(node_data: NodeOutput, base_key: str) -> str:
        """Generate a unique output key."""
        if base_key not in node_data.data:
            return base_key
        
        counter = 2
        while f"{base_key}_{counter}" in node_data.data:
            counter += 1
        
        return f"{base_key}_{counter}"

# Execution Coordination - Separate class
class NodeExecutionCoordinator:
    """Coordinates node execution flow."""
    
    def __init__(
        self,
        form_manager: NodeFormManager,
        validator: NodeValidator,
        template_renderer: TemplateRenderer,
        error_formatter: ErrorFormatter
    ):
        self.form_manager = form_manager
        self.validator = validator
        self.template_renderer = template_renderer
        self.error_formatter = error_formatter
    
    async def prepare_for_execution(self, node_data: NodeOutput) -> None:
        """Prepare node for execution by rendering templates and validating."""
        if self.form_manager.form is None:
            return
        
        # Render templates
        self.template_renderer.render_in_form(
            self.form_manager.form,
            node_data,
            self.form_manager.node_config
        )
        
        # Validate after rendering
        if not self.form_manager.form.is_valid():
            clean_message = self.error_formatter.extract_clean_error_messages(
                self.form_manager.form
            )
            raise FormValidationError(
                self.form_manager.form,
                f"Form validation failed after rendering: {clean_message}"
            )

# Refactored BaseNode - Single Responsibility: Node execution
class BaseNode(BaseNodeProperty, BaseNodeMethod, ABC):
    """Base node class - focuses only on node execution."""
    
    def __init__(self, node_config: NodeConfig):
        self.node_config = node_config
        self.form = self.get_form()
        self.execution_count = 0
        
        # Compose managers (SRP: each handles one concern)
        self._form_manager = NodeFormManager(self.form, node_config)
        self._validator = NodeValidator(self.form, node_config)
        self._template_renderer = TemplateRenderer()
        self._error_formatter = ErrorFormatter()
        self._execution_coordinator = NodeExecutionCoordinator(
            self._form_manager,
            self._validator,
            self._template_renderer,
            self._error_formatter
        )
        
        # Populate form from config
        self._form_manager.populate_from_config()
    
    def is_ready(self) -> bool:
        """Check if node is ready - delegates to validator."""
        return self._validator.is_ready()
    
    def populate_form_values(self, node_data: NodeOutput) -> None:
        """Populate form values - delegates to coordinator."""
        self._execution_coordinator.prepare_for_execution(node_data)
    
    async def run(self, node_data: NodeOutput) -> NodeOutput:
        """Main entry point - coordinates execution."""
        if isinstance(node_data, ExecutionCompleted):
            await self.cleanup(node_data)
            return node_data
        
        self.populate_form_values(node_data)
        output = await self.execute(node_data)
        self.execution_count += 1
        return output
    
    def get_unique_output_key(self, node_data: NodeOutput, base_key: str) -> str:
        """Generate unique key - delegates to generator."""
        return OutputKeyGenerator.get_unique_key(node_data, base_key)
```

#### Benefits

- ✅ **Single Responsibility**: Each class has one clear purpose
- ✅ **Testability**: Can test form management, validation, rendering independently
- ✅ **Reusability**: Form manager, validator, renderer can be reused elsewhere
- ✅ **Maintainability**: Changes to validation don't affect template rendering
- ✅ **Clarity**: Clear separation of concerns makes code easier to understand

---

### Violation 2: NodeExecutionService Mixed Concerns

**Location**: `apps/workflow/services/node_execution_service.py:13-172`

#### Current Implementation (Before)

```python
class NodeExecutionService:
    """Service for executing nodes and managing their input/output data."""
    
    @staticmethod
    def execute_node(
        node: Node,
        form_values: Dict[str, Any],
        input_data: Dict[str, Any],
        session_id: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute a node with given form values and input data.
        Handles:
        1. Database persistence (saving form_values, input_data, output_data)
        2. Node execution orchestration
        3. Error handling and transformation
        4. Result formatting
        """
        # ❌ Database persistence
        node.form_values = form_values
        node.input_data = input_data
        node.save()
        
        try:
            # ❌ Service orchestration
            from apps.nodes.services import get_node_services
            services = get_node_services()
            node_metadata = services.node_registry.find_by_identifier(node.node_type)
            
            # ❌ Error handling
            if node_metadata is None:
                return {
                    'success': False,
                    'error': f'Node type not found: {node.node_type}',
                    'error_type': 'NodeTypeNotFound',
                    # ...
                }
            
            # ❌ Execution orchestration
            result = services.node_executor.execute(
                node_metadata, input_data, form_values, session_id, timeout
            )
            
            # ❌ Database persistence
            if result.get('success'):
                output = result.get('output', {})
                if isinstance(output, dict) and 'data' in output:
                    node.output_data = output.get('data', {})
                else:
                    node.output_data = output
                node.save()
            
            # ❌ Result formatting
            return {
                'success': result.get('success', False),
                'node_id': str(node.id),
                'node_type': node.node_type,
                'input_data': input_data,
                'form_values': form_values,
                'output': result.get('output'),
                'error': result.get('error'),
                'error_type': result.get('error_type'),
                'message': result.get('message'),
                'form': result.get('form'),
                'session_id': session_id,
            }
        except Exception as e:
            # ❌ Error handling and transformation
            return {
                'success': False,
                'error': str(e),
                'error_type': 'ExecutionError',
                'node_id': str(node.id),
                'node_type': node.node_type,
            }
    
    @staticmethod
    def get_node_for_execution(workflow_id: str, node_id: str) -> Node:
        """Get a node instance for execution."""  # ❌ Data access
        try:
            return Node.objects.get(id=node_id, workflow_id=workflow_id)
        except Node.DoesNotExist:
            raise NodeNotFoundError(node_id, workflow_id)
    
    @staticmethod
    def execute_and_save_node(...):
        """Execute a workflow node and save all execution data."""  # ❌ Orchestration + persistence
        # Validate node_id is provided  # ❌ Validation
        if not node_id:
            raise ValidationError('node_id is required')
        
        # Get the node instance  # ❌ Data access
        node = NodeExecutionService.get_node_for_execution(workflow_id, node_id)
        
        # Execute the node  # ❌ Execution orchestration
        result = NodeExecutionService.execute_node(node, form_values, input_data, session_id, timeout)
        
        # Check if execution failed  # ❌ Error handling
        if result.get('error_type') == 'NodeTypeNotFound':
            raise NodeTypeNotFoundError(node.node_type)
        
        return result
```

#### Problem

`NodeExecutionService` violates SRP by mixing multiple concerns:

1. **Database Persistence**: Saving form_values, input_data, output_data to database
2. **Data Access**: Querying database for node instances
3. **Execution Orchestration**: Coordinating node execution with services
4. **Error Handling**: Transforming errors into result dictionaries
5. **Result Formatting**: Formatting execution results into response dictionaries
6. **Validation**: Validating input parameters

Each responsibility can change independently:
- Database schema changes don't affect execution logic
- Error handling changes don't affect data access
- Result formatting changes don't affect execution

#### Solution Approach

1. **Extract Repository**: Create `NodeRepository` for data access and persistence
2. **Extract Executor**: Create `NodeExecutionOrchestrator` for execution coordination
3. **Extract Error Handler**: Create `ExecutionErrorHandler` for error transformation
4. **Extract Result Formatter**: Create `ExecutionResultFormatter` for result formatting
5. **Extract Validator**: Create `NodeExecutionValidator` for input validation

#### Refactored Implementation (After)

```python
# Data Access and Persistence - Separate class
class NodeRepository:
    """Handles database operations for Node model."""
    
    @staticmethod
    def get_node(workflow_id: str, node_id: str) -> Node:
        """Get node by ID and workflow ID."""
        try:
            return Node.objects.get(id=node_id, workflow_id=workflow_id)
        except Node.DoesNotExist:
            raise NodeNotFoundError(node_id, workflow_id)
    
    @staticmethod
    def save_execution_input(node: Node, form_values: Dict, input_data: Dict):
        """Save execution input data to node."""
        node.form_values = form_values
        node.input_data = input_data
        node.save()
    
    @staticmethod
    def save_execution_output(node: Node, output: Any):
        """Save execution output data to node."""
        if isinstance(output, dict) and 'data' in output:
            node.output_data = output.get('data', {})
        else:
            node.output_data = output
        node.save()

# Execution Orchestration - Separate class
class NodeExecutionOrchestrator:
    """Orchestrates node execution with services."""
    
    def __init__(self, node_registry, node_executor):
        self.node_registry = node_registry
        self.node_executor = node_executor
    
    def execute(
        self,
        node: Node,
        form_values: Dict[str, Any],
        input_data: Dict[str, Any],
        session_id: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """Execute node and return raw result."""
        # Find node metadata
        node_metadata = self.node_registry.find_by_identifier(node.node_type)
        
        if node_metadata is None:
            return {
                'success': False,
                'error': f'Node type not found: {node.node_type}',
                'error_type': 'NodeTypeNotFound',
            }
        
        # Execute node
        result = self.node_executor.execute(
            node_metadata, input_data, form_values, session_id, timeout
        )
        
        return result

# Error Handling - Separate class
class ExecutionErrorHandler:
    """Handles execution errors and transforms them."""
    
    @staticmethod
    def handle_error(error: Exception, node: Node) -> Dict[str, Any]:
        """Transform exception into error result dictionary."""
        return {
            'success': False,
            'error': str(error),
            'error_type': 'ExecutionError',
            'node_id': str(node.id),
            'node_type': node.node_type,
        }
    
    @staticmethod
    def check_and_raise_node_type_error(result: Dict, node: Node):
        """Check result for node type error and raise exception."""
        if result.get('error_type') == 'NodeTypeNotFound':
            raise NodeTypeNotFoundError(node.node_type)

# Result Formatting - Separate class
class ExecutionResultFormatter:
    """Formats execution results into response dictionaries."""
    
    @staticmethod
    def format_result(
        result: Dict[str, Any],
        node: Node,
        form_values: Dict,
        input_data: Dict,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Format execution result into response dictionary."""
        return {
            'success': result.get('success', False),
            'node_id': str(node.id),
            'node_type': node.node_type,
            'input_data': input_data,
            'form_values': form_values,
            'output': result.get('output'),
            'error': result.get('error'),
            'error_type': result.get('error_type'),
            'message': result.get('message'),
            'form': result.get('form'),
            'session_id': session_id,
        }

# Validation - Separate class
class NodeExecutionValidator:
    """Validates input for node execution."""
    
    @staticmethod
    def validate_node_id(node_id: Optional[str]):
        """Validate that node_id is provided."""
        if not node_id:
            raise ValidationError('node_id is required')

# Refactored NodeExecutionService - Single Responsibility: Service coordination
class NodeExecutionService:
    """Service for coordinating node execution - orchestrates other components."""
    
    def __init__(
        self,
        repository: Optional[NodeRepository] = None,
        orchestrator: Optional[NodeExecutionOrchestrator] = None,
        error_handler: Optional[ExecutionErrorHandler] = None,
        result_formatter: Optional[ExecutionResultFormatter] = None,
        validator: Optional[NodeExecutionValidator] = None
    ):
        self.repository = repository or NodeRepository()
        self.validator = validator or NodeExecutionValidator()
        
        # Initialize orchestrator with services
        if orchestrator is None:
            from apps.nodes.services import get_node_services
            services = get_node_services()
            self.orchestrator = NodeExecutionOrchestrator(
                services.node_registry,
                services.node_executor
            )
        else:
            self.orchestrator = orchestrator
        
        self.error_handler = error_handler or ExecutionErrorHandler()
        self.result_formatter = result_formatter or ExecutionResultFormatter()
    
    def execute_node(
        self,
        node: Node,
        form_values: Dict[str, Any],
        input_data: Dict[str, Any],
        session_id: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """Execute a node - coordinates all components."""
        # Save input data
        self.repository.save_execution_input(node, form_values, input_data)
        
        try:
            # Execute node
            result = self.orchestrator.execute(
                node, form_values, input_data, session_id, timeout
            )
            
            # Save output data if successful
            if result.get('success'):
                self.repository.save_execution_output(node, result.get('output'))
            
            # Format and return result
            return self.result_formatter.format_result(
                result, node, form_values, input_data, session_id
            )
        except Exception as e:
            # Handle errors
            return self.error_handler.handle_error(e, node)
    
    def get_node_for_execution(self, workflow_id: str, node_id: str) -> Node:
        """Get node for execution - delegates to repository."""
        return self.repository.get_node(workflow_id, node_id)
    
    def execute_and_save_node(
        self,
        workflow_id: str,
        node_id: str,
        form_values: Dict[str, Any],
        input_data: Dict[str, Any],
        session_id: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """Execute and save node - coordinates validation and execution."""
        # Validate input
        self.validator.validate_node_id(node_id)
        
        # Get node
        node = self.get_node_for_execution(workflow_id, node_id)
        
        # Execute node
        result = self.execute_node(node, form_values, input_data, session_id, timeout)
        
        # Check for node type error
        self.error_handler.check_and_raise_node_type_error(result, node)
        
        return result
```

#### Benefits

- ✅ **Single Responsibility**: Each class handles one concern
- ✅ **Testability**: Can test data access, execution, error handling independently
- ✅ **Reusability**: Repository, formatter, error handler can be reused
- ✅ **Maintainability**: Database changes don't affect execution logic
- ✅ **Flexibility**: Can swap implementations (e.g., different repository)

---

### Violation 3: NodeExecutor Overloaded Responsibilities

**Location**: `core/views/services/node_executor.py:15-272`

#### Current Implementation (Before)

```python
class NodeExecutor:
    """
    Executes nodes asynchronously with input and form data.
    
    Handles:
    1. Node class loading
    2. Session management (storing/retrieving node instances)
    3. Async execution coordination
    4. Timeout handling
    5. Browser cleanup
    6. Error transformation (FormValidationError → FormValidationException)
    7. Event loop management
    """
    
    def __init__(self, node_loader: NodeLoader):
        self._node_loader = node_loader
        self._session_store = NodeSessionStore()  # ❌ Session management
    
    def execute(
        self, 
        node_metadata: Dict, 
        input_data: Dict, 
        form_data: Dict,
        session_id: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> Dict:
        """Execute a node - handles loading, execution, error transformation."""
        # ❌ Node loading
        node_class = self._node_loader.load_class(node_metadata)
        
        if node_class is None:
            return {
                'success': False,
                'error': 'Failed to load node class',
                # ...
            }
        
        try:
            # ❌ Execution coordination
            result = self._run_node(
                node_class, node_metadata, input_data, form_data, session_id, timeout
            )
            
            # ❌ Result formatting
            return {
                'success': True,
                'node': {
                    'name': node_metadata.get('name'),
                    'identifier': node_metadata.get('identifier'),
                },
                'input': input_data,
                'form_data': form_data,
                'session_id': session_id,
                'output': result.model_dump() if hasattr(result, 'model_dump') else result
            }
        except asyncio.TimeoutError:
            # ❌ Session cleanup on timeout
            if session_id:
                self._session_store.clear(session_id)
            raise ExecutionTimeoutException(...)
        except Exception as e:
            # ❌ Error transformation
            is_form_validation_error = (
                type(e).__name__ == 'FormValidationError' and
                hasattr(e, 'form') and
                hasattr(e, 'message')
            )
            
            if is_form_validation_error:
                # ❌ Form serialization
                from Node.Core.Form.Core.FormSerializer import FormSerializer
                serializer = FormSerializer(e.form)
                form_state = serializer.to_json()
                
                # ❌ Exception transformation
                raise FormValidationException(
                    message=e.message,
                    form_data=form_state,
                    detail=e.message
                )
            raise
    
    def _run_node(...):
        """Run the node asynchronously - handles session, execution, timeout, cleanup."""
        # ❌ Session management
        # ❌ Node instance creation
        # ❌ Async execution coordination
        # ❌ Browser cleanup
        # ❌ Event loop management
        # ❌ Timeout handling
        # ... complex logic mixing all concerns ...
```

#### Problem

`NodeExecutor` violates SRP by handling multiple distinct responsibilities:

1. **Node Loading**: Loading node classes from metadata
2. **Session Management**: Storing and retrieving node instances by session ID
3. **Node Instance Creation**: Creating and configuring node instances
4. **Async Execution**: Coordinating async execution with event loops
5. **Timeout Handling**: Managing timeouts and task cancellation
6. **Browser Cleanup**: Cleaning up browser resources after execution
7. **Error Transformation**: Transforming exceptions (FormValidationError → FormValidationException)
8. **Event Loop Management**: Creating, managing, and cleaning up event loops
9. **Result Formatting**: Formatting execution results

Each responsibility can change independently:
- Session management changes don't affect timeout handling
- Browser cleanup changes don't affect error transformation
- Event loop management changes don't affect node loading

#### Solution Approach

1. **Extract Session Manager**: Create `NodeSessionManager` for session operations
2. **Extract Node Factory**: Create `NodeInstanceFactory` for creating node instances
3. **Extract Async Executor**: Create `AsyncNodeExecutor` for async execution
4. **Extract Timeout Manager**: Create `ExecutionTimeoutManager` for timeout handling
5. **Extract Resource Cleanup**: Create `ExecutionResourceCleanup` for browser cleanup
6. **Extract Error Transformer**: Create `ExecutionErrorTransformer` for error transformation
7. **Extract Event Loop Manager**: Create `EventLoopManager` for event loop lifecycle
8. **Extract Result Formatter**: Create `NodeExecutionResultFormatter` for result formatting

#### Refactored Implementation (After)

```python
# Session Management - Separate class
class NodeSessionManager:
    """Manages node instance sessions."""
    
    def __init__(self, session_store: NodeSessionStore):
        self._session_store = session_store
    
    def get_instance(self, session_id: str):
        """Get node instance from session."""
        return self._session_store.get(session_id)
    
    def store_instance(self, session_id: str, instance: BaseNode):
        """Store node instance in session."""
        self._session_store.set(session_id, instance)
    
    def clear_session(self, session_id: str) -> bool:
        """Clear session."""
        return self._session_store.clear(session_id)
    
    def update_form_data(self, instance: BaseNode, form_data: Dict):
        """Update form data on existing instance."""
        instance.node_config.data.form = form_data

# Node Instance Creation - Separate class
class NodeInstanceFactory:
    """Creates and configures node instances."""
    
    def __init__(self, node_loader: NodeLoader):
        self._node_loader = node_loader
    
    def load_class(self, node_metadata: Dict):
        """Load node class from metadata."""
        return self._node_loader.load_class(node_metadata)
    
    def create_instance(self, node_metadata: Dict, form_data: Dict) -> BaseNode:
        """Create new node instance."""
        from Node.Core.Node.Core.Data import NodeConfig, NodeConfigData
        
        node_class = self.load_class(node_metadata)
        if node_class is None:
            return None
        
        node_config = NodeConfig(
            id=f"exec_{node_metadata.get('identifier')}",
            type=node_metadata.get('identifier'),
            data=NodeConfigData(form=form_data)
        )
        
        return node_class(node_config)

# Resource Cleanup - Separate class
class ExecutionResourceCleanup:
    """Handles cleanup of execution resources."""
    
    @staticmethod
    async def cleanup_browser():
        """Clean up browser resources after execution."""
        try:
            from Node.Nodes.Browser._shared.BrowserManager import BrowserManager
            browser_manager = BrowserManager()
            if browser_manager._initialized:
                await browser_manager.close()
        except ImportError:
            pass  # BrowserManager not available

# Error Transformation - Separate class
class ExecutionErrorTransformer:
    """Transforms execution errors."""
    
    @staticmethod
    def transform_form_validation_error(error: Exception) -> FormValidationException:
        """Transform FormValidationError to FormValidationException."""
        from Node.Core.Form.Core.FormSerializer import FormSerializer
        
        serializer = FormSerializer(error.form)
        form_state = serializer.to_json()
        
        return FormValidationException(
            message=error.message,
            form_data=form_state,
            detail=error.message
        )
    
    @staticmethod
    def is_form_validation_error(error: Exception) -> bool:
        """Check if error is FormValidationError."""
        return (
            type(error).__name__ == 'FormValidationError' and
            hasattr(error, 'form') and
            hasattr(error, 'message')
        )

# Timeout Management - Separate class
class ExecutionTimeoutManager:
    """Manages execution timeouts."""
    
    @staticmethod
    async def execute_with_timeout(
        coro,
        timeout: Optional[float] = None,
        on_timeout: Optional[Callable] = None
    ) -> Any:
        """Execute coroutine with timeout."""
        if timeout is not None and timeout > 0:
            try:
                return await asyncio.wait_for(coro, timeout=timeout)
            except asyncio.TimeoutError:
                if on_timeout:
                    on_timeout()
                raise
        else:
            return await coro

# Event Loop Management - Separate class
class EventLoopManager:
    """Manages event loop lifecycle."""
    
    @staticmethod
    def create_and_run(coro, timeout: Optional[float] = None) -> Any:
        """Create event loop and run coroutine."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task = None
        
        try:
            if timeout is not None and timeout > 0:
                task = loop.create_task(coro)
                try:
                    result = loop.run_until_complete(
                        asyncio.wait_for(task, timeout=timeout)
                    )
                except asyncio.TimeoutError:
                    if task and not task.done():
                        task.cancel()
                    raise
            else:
                result = loop.run_until_complete(coro)
            
            return result
        finally:
            EventLoopManager._cleanup_loop(loop)
    
    @staticmethod
    def _cleanup_loop(loop: asyncio.AbstractEventLoop):
        """Clean up event loop and cancel pending tasks."""
        try:
            if not loop.is_closed():
                all_tasks = asyncio.all_tasks(loop)
                for pending_task in all_tasks:
                    if not pending_task.done():
                        pending_task.cancel()
                loop.close()
        except Exception:
            pass

# Async Execution - Separate class
class AsyncNodeExecutor:
    """Handles async node execution."""
    
    def __init__(
        self,
        session_manager: NodeSessionManager,
        instance_factory: NodeInstanceFactory,
        resource_cleanup: ExecutionResourceCleanup
    ):
        self.session_manager = session_manager
        self.instance_factory = instance_factory
        self.resource_cleanup = resource_cleanup
    
    async def execute_async(
        self,
        node_metadata: Dict,
        input_data: Dict,
        form_data: Dict,
        session_id: Optional[str] = None
    ) -> Any:
        """Execute node asynchronously."""
        from Node.Core.Node.Core.Data import NodeOutput
        
        # Get or create instance
        node_instance = None
        is_new_instance = False
        
        if session_id:
            node_instance = self.session_manager.get_instance(session_id)
        
        if node_instance is None:
            node_instance = self.instance_factory.create_instance(node_metadata, form_data)
            if node_instance is None:
                raise ValueError('Failed to create node instance')
            is_new_instance = True
            
            if session_id:
                self.session_manager.store_instance(session_id, node_instance)
        else:
            self.session_manager.update_form_data(node_instance, form_data)
        
        # Create input
        node_output = NodeOutput(data=input_data)
        
        # Execute
        if is_new_instance:
            await node_instance.init()
        
        result = await node_instance.run(node_output)
        
        # Cleanup resources
        await self.resource_cleanup.cleanup_browser()
        
        return result

# Result Formatting - Separate class
class NodeExecutionResultFormatter:
    """Formats node execution results."""
    
    @staticmethod
    def format_success_result(
        result: Any,
        node_metadata: Dict,
        input_data: Dict,
        form_data: Dict,
        session_id: Optional[str] = None
    ) -> Dict:
        """Format successful execution result."""
        return {
            'success': True,
            'node': {
                'name': node_metadata.get('name'),
                'identifier': node_metadata.get('identifier'),
            },
            'input': input_data,
            'form_data': form_data,
            'session_id': session_id,
            'output': result.model_dump() if hasattr(result, 'model_dump') else result
        }
    
    @staticmethod
    def format_error_result(error: str, node_metadata: Dict) -> Dict:
        """Format error result."""
        return {
            'success': False,
            'error': error,
            'identifier': node_metadata.get('identifier'),
            'file_path': node_metadata.get('file_path')
        }

# Refactored NodeExecutor - Single Responsibility: Coordination
class NodeExecutor:
    """Coordinates node execution - orchestrates specialized components."""
    
    def __init__(
        self,
        node_loader: NodeLoader,
        session_manager: Optional[NodeSessionManager] = None,
        instance_factory: Optional[NodeInstanceFactory] = None,
        async_executor: Optional[AsyncNodeExecutor] = None,
        timeout_manager: Optional[ExecutionTimeoutManager] = None,
        error_transformer: Optional[ExecutionErrorTransformer] = None,
        event_loop_manager: Optional[EventLoopManager] = None,
        result_formatter: Optional[NodeExecutionResultFormatter] = None
    ):
        # Initialize components
        self._instance_factory = instance_factory or NodeInstanceFactory(node_loader)
        
        session_store = NodeSessionStore()
        self._session_manager = session_manager or NodeSessionManager(session_store)
        
        resource_cleanup = ExecutionResourceCleanup()
        self._async_executor = async_executor or AsyncNodeExecutor(
            self._session_manager,
            self._instance_factory,
            resource_cleanup
        )
        
        self._timeout_manager = timeout_manager or ExecutionTimeoutManager()
        self._error_transformer = error_transformer or ExecutionErrorTransformer()
        self._event_loop_manager = event_loop_manager or EventLoopManager()
        self._result_formatter = result_formatter or NodeExecutionResultFormatter()
    
    def execute(
        self, 
        node_metadata: Dict, 
        input_data: Dict, 
        form_data: Dict,
        session_id: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> Dict:
        """Execute node - coordinates all components."""
        # Check if class can be loaded
        node_class = self._instance_factory.load_class(node_metadata)
        if node_class is None:
            return self._result_formatter.format_error_result(
                'Failed to load node class',
                node_metadata
            )
        
        try:
            # Create async execution coroutine
            async def run():
                return await self._async_executor.execute_async(
                    node_metadata, input_data, form_data, session_id
                )
            
            # Execute with timeout in event loop
            def on_timeout():
                if session_id:
                    self._session_manager.clear_session(session_id)
            
            result = self._event_loop_manager.create_and_run(
                self._timeout_manager.execute_with_timeout(
                    run(),
                    timeout=timeout,
                    on_timeout=on_timeout
                ),
                timeout=timeout
            )
            
            # Format success result
            return self._result_formatter.format_success_result(
                result, node_metadata, input_data, form_data, session_id
            )
            
        except asyncio.TimeoutError:
            if session_id:
                self._session_manager.clear_session(session_id)
            raise ExecutionTimeoutException(
                timeout=timeout or 0,
                detail=f'Node execution exceeded timeout of {timeout} seconds'
            )
        except ExecutionTimeoutException:
            raise
        except Exception as e:
            # Transform FormValidationError
            if self._error_transformer.is_form_validation_error(e):
                raise self._error_transformer.transform_form_validation_error(e)
            raise
    
    def clear_session(self, session_id: str) -> bool:
        """Clear session - delegates to session manager."""
        return self._session_manager.clear_session(session_id)
```

#### Benefits

- ✅ **Single Responsibility**: Each class handles one concern
- ✅ **Testability**: Can test session management, timeout, error transformation independently
- ✅ **Reusability**: Components can be reused in different contexts
- ✅ **Maintainability**: Changes to timeout handling don't affect session management
- ✅ **Flexibility**: Can swap implementations (e.g., different event loop manager)

---

### Violation 4: FlowEngine Orchestration and Implementation

**Location**: `core/Workflow/flow_engine.py:21-162`

#### Current Implementation (Before)

```python
class FlowEngine:
    """
    Central coordination system for flow execution.
    
    Handles:
    1. Workflow loading and graph building
    2. Post-processing orchestration
    3. Event system wiring
    4. State tracking initialization
    5. Production execution coordination
    6. Development node execution
    7. Loop creation and management
    8. Force shutdown
    """
    
    def __init__(self, workflow_id: Optional[str] = None):
        self.workflow_id = workflow_id
        self.data_store = DataStore()  # ❌ Storage initialization
        self.flow_runners: List[FlowRunner] = []
        self.flow_graph = FlowGraph()  # ❌ Graph creation
        self.flow_analyzer = FlowAnalyzer(self.flow_graph)  # ❌ Analyzer creation
        self.flow_builder = FlowBuilder(self.flow_graph, NodeRegistry())  # ❌ Builder creation
        self.events = WorkflowEventEmitter(workflow_id)  # ❌ Event system creation
        self.state_tracker: Optional[ExecutionStateTracker] = None
    
    def load_workflow(self, workflow_json: Dict[str, Any]):
        """Load workflow - handles building, post-processing, loop creation."""  # ❌ Multiple concerns
        # ❌ Graph building
        self.flow_builder.load_workflow(workflow_json)
        
        # ❌ Post-processing
        for processor_class in self._post_processors:
            processor = processor_class(self.flow_graph)
            processor.execute()
        
        # ❌ Graph analysis
        first_node_id = self.flow_analyzer.get_first_node_id()
        if first_node_id:
            first_node = self.flow_graph.node_map[first_node_id]
            logger.info(f"Workflow Loaded Successfully", graph=first_node.to_dict())
        else:
            raise ValueError("No first node found in the workflow")
        
        # ❌ Loop creation
        producer_nodes = self.flow_analyzer.get_producer_nodes()
        for producer_flow_node in producer_nodes:
            try:
                self.create_loop(producer_flow_node)
                logger.info(f"Created Loop", producer_node_id=producer_flow_node.id)
            except ValueError as e:
                logger.warning(f"Failed to create loop", error=str(e))
    
    async def run_production(self):
        """Run production mode - handles state tracking, event wiring, execution."""  # ❌ Multiple concerns
        # ❌ State tracking initialization
        total_nodes = len(self.flow_graph.node_map)
        self.state_tracker = ExecutionStateTracker(self.workflow_id, total_nodes)
        
        # ❌ Event wiring
        self._wire_events_to_state_tracker()
        
        # ❌ Execution coordination
        self.state_tracker.start_workflow()
        for _ in self.flow_runners:
            self.state_tracker.register_runner()
        
        self.tasks = [asyncio.create_task(runner.start()) for runner in self.flow_runners]
        
        try:
            await asyncio.gather(*self.tasks)
        except Exception as e:
            if self.state_tracker:
                self.state_tracker.on_workflow_failed(str(e))
            raise
        finally:
            if self.state_tracker:
                for _ in self.flow_runners:
                    self.state_tracker.unregister_runner()
    
    def _wire_events_to_state_tracker(self):
        """Wire event emitter to state tracker."""  # ❌ Event system configuration
        # ... event subscription logic ...
```

#### Problem

`FlowEngine` violates SRP by mixing orchestration with implementation details:

1. **Component Creation**: Creating FlowGraph, FlowAnalyzer, FlowBuilder, EventEmitter
2. **Workflow Loading**: Building graph, running post-processors, analyzing graph
3. **Event System Configuration**: Wiring events to state tracker
4. **State Tracking**: Initializing and managing execution state
5. **Execution Coordination**: Starting and managing flow runners
6. **Loop Management**: Creating and managing execution loops

#### Solution Approach

1. **Extract Workflow Loader**: Create `WorkflowLoader` for loading and building workflows
2. **Extract Event Coordinator**: Create `EventCoordinator` for event system wiring
3. **Extract State Manager**: Create `ExecutionStateManager` for state tracking
4. **Extract Execution Coordinator**: Create `ProductionExecutionCoordinator` for execution

#### Refactored Implementation (After)

```python
# Workflow Loading - Separate class
class WorkflowLoader:
    """Loads and builds workflows from JSON."""
    
    def __init__(
        self,
        flow_builder: FlowBuilder,
        flow_analyzer: FlowAnalyzer,
        post_processors: List[Type[PostProcessor]]
    ):
        self.flow_builder = flow_builder
        self.flow_analyzer = flow_analyzer
        self.post_processors = post_processors
    
    def load(self, workflow_json: Dict[str, Any], flow_graph: FlowGraph) -> List[FlowNode]:
        """Load workflow and return producer nodes."""
        # Build graph
        self.flow_builder.load_workflow(workflow_json)
        
        # Run post-processors
        for processor_class in self.post_processors:
            processor = processor_class(flow_graph)
            processor.execute()
        
        # Validate workflow
        first_node_id = self.flow_analyzer.get_first_node_id()
        if not first_node_id:
            raise ValueError("No first node found in the workflow")
        
        # Get producer nodes
        return self.flow_analyzer.get_producer_nodes()

# Event Coordination - Separate class
class EventCoordinator:
    """Coordinates event system wiring."""
    
    def __init__(
        self,
        event_emitter: WorkflowEventEmitter,
        state_tracker: ExecutionStateTracker
    ):
        self.event_emitter = event_emitter
        self.state_tracker = state_tracker
    
    def wire_events(self):
        """Wire events to state tracker."""
        self.event_emitter.subscribe(
            WorkflowEventEmitter.NODE_STARTED,
            lambda data: self.state_tracker.on_node_started(
                data.get("node_id"),
                data.get("node_type")
            )
        )
        # ... other subscriptions ...

# Execution Coordination - Separate class
class ProductionExecutionCoordinator:
    """Coordinates production execution."""
    
    def __init__(
        self,
        flow_runners: List[FlowRunner],
        state_tracker: ExecutionStateTracker
    ):
        self.flow_runners = flow_runners
        self.state_tracker = state_tracker
    
    async def execute(self):
        """Execute all flow runners."""
        # Start workflow
        self.state_tracker.start_workflow()
        
        # Register runners
        for _ in self.flow_runners:
            self.state_tracker.register_runner()
        
        # Create and run tasks
        tasks = [asyncio.create_task(runner.start()) for runner in self.flow_runners]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            self.state_tracker.on_workflow_failed(str(e))
            raise
        finally:
            for _ in self.flow_runners:
                self.state_tracker.unregister_runner()

# Refactored FlowEngine - Single Responsibility: High-level orchestration
class FlowEngine:
    """Central coordination system - orchestrates workflow components."""
    
    def __init__(
        self,
        workflow_id: Optional[str] = None,
        workflow_loader: Optional[WorkflowLoader] = None,
        event_coordinator: Optional[EventCoordinator] = None,
        execution_coordinator: Optional[ProductionExecutionCoordinator] = None
    ):
        self.workflow_id = workflow_id
        
        # Initialize components
        self.flow_graph = FlowGraph()
        self.flow_analyzer = FlowAnalyzer(self.flow_graph)
        self.flow_builder = FlowBuilder(self.flow_graph, NodeRegistry())
        self.events = WorkflowEventEmitter(workflow_id)
        
        # Initialize coordinators
        self._workflow_loader = workflow_loader or WorkflowLoader(
            self.flow_builder,
            self.flow_analyzer,
            [QueueMapper, NodeValidator]
        )
        
        self.flow_runners: List[FlowRunner] = []
        self.state_tracker: Optional[ExecutionStateTracker] = None
        self._event_coordinator = event_coordinator
        self._execution_coordinator = execution_coordinator
    
    def load_workflow(self, workflow_json: Dict[str, Any]):
        """Load workflow - delegates to loader."""
        producer_nodes = self._workflow_loader.load(workflow_json, self.flow_graph)
        
        for producer_flow_node in producer_nodes:
            try:
                self.create_loop(producer_flow_node)
            except ValueError as e:
                logger.warning(f"Failed to create loop", error=str(e))
    
    async def run_production(self):
        """Run production mode - delegates to coordinator."""
        # Initialize state tracker
        total_nodes = len(self.flow_graph.node_map)
        self.state_tracker = ExecutionStateTracker(self.workflow_id, total_nodes)
        
        # Wire events
        if self._event_coordinator is None:
            self._event_coordinator = EventCoordinator(self.events, self.state_tracker)
        self._event_coordinator.wire_events()
        
        # Execute
        if self._execution_coordinator is None:
            self._execution_coordinator = ProductionExecutionCoordinator(
                self.flow_runners,
                self.state_tracker
            )
        await self._execution_coordinator.execute()
```

#### Benefits

- ✅ **Single Responsibility**: Each class handles one concern
- ✅ **Testability**: Can test workflow loading, event coordination independently
- ✅ **Reusability**: Components can be reused in different contexts
- ✅ **Maintainability**: Changes to event wiring don't affect workflow loading

---

### Violation 5: FlowRunner Execution and Event Management

**Location**: `core/Workflow/execution/flow_runner.py:18-222`

#### Current Implementation (Before)

```python
class FlowRunner:
    """
    Manages a single flow loop in Production Mode.
    
    Handles:
    1. Node execution coordination
    2. Event emission (node_started, node_completed, node_failed)
    3. Graph traversal and branching logic
    4. Node initialization
    5. Error handling and logging
    6. Loop lifecycle management
    """
    
    async def start(self):
        """Start the flow loop - handles execution, events, errors."""  # ❌ Multiple concerns
        self.running = True
        await self._init_nodes()  # ❌ Initialization
        
        try:
            while self.running:
                # ❌ Event emission
                if self.events:
                    self.events.emit_node_started(self.producer_flow_node.id, producer_type)
                
                # ❌ Execution
                data = await self.executor.execute_in_pool(...)
                
                # ❌ Event emission
                if self.events:
                    self.events.emit_node_completed(...)
                
                # ❌ Graph traversal
                await self._process_next_nodes(self.producer_flow_node, data)
        finally:
            self.shutdown()  # ❌ Lifecycle management
    
    async def _process_next_nodes(self, current_flow_node: FlowNode, input_data: NodeOutput):
        """Process downstream nodes - handles traversal, execution, events."""  # ❌ Multiple concerns
        # ❌ Branching logic
        # ❌ Node execution
        # ❌ Event emission
        # ❌ Error handling
        # ... complex logic mixing all concerns ...
```

#### Problem

`FlowRunner` violates SRP by mixing execution with event management and graph traversal.

#### Solution Approach

1. **Extract Event Emitter**: Create `NodeEventEmitter` for event emission
2. **Extract Graph Traverser**: Create `FlowGraphTraverser` for graph traversal
3. **Extract Node Initializer**: Create `NodeInitializer` for node initialization

#### Refactored Implementation (After)

```python
# Event Emission - Separate class
class NodeEventEmitter:
    """Emits node execution events."""
    
    def __init__(self, events: Optional[WorkflowEventEmitter]):
        self.events = events
    
    def emit_started(self, node_id: str, node_type: str):
        """Emit node started event."""
        if self.events:
            self.events.emit_node_started(node_id, node_type)
    
    def emit_completed(self, node_id: str, node_type: str, output_data: Any, route: Optional[str]):
        """Emit node completed event."""
        if self.events:
            self.events.emit_node_completed(node_id, node_type, output_data, route)
    
    def emit_failed(self, node_id: str, node_type: str, error: str):
        """Emit node failed event."""
        if self.events:
            self.events.emit_node_failed(node_id, node_type, error)

# Graph Traversal - Separate class
class FlowGraphTraverser:
    """Traverses flow graph and determines next nodes."""
    
    def __init__(self, event_emitter: NodeEventEmitter, executor: PoolExecutor):
        self.event_emitter = event_emitter
        self.executor = executor
    
    async def process_next_nodes(
        self,
        current_flow_node: FlowNode,
        input_data: NodeOutput
    ):
        """Process downstream nodes."""
        next_nodes = current_flow_node.next
        if not next_nodes:
            return
        
        # Determine branches (logic extracted)
        keys_to_process = self._determine_branches(current_flow_node, input_data, next_nodes)
        
        # Execute nodes in selected branches
        for key in keys_to_process:
            if key in next_nodes:
                for next_flow_node in next_nodes[key]:
                    await self._execute_node(next_flow_node, input_data)
    
    def _determine_branches(self, current_flow_node, input_data, next_nodes) -> Set[str]:
        """Determine which branches to process."""
        # ... branching logic ...
        pass
    
    async def _execute_node(self, flow_node: FlowNode, input_data: NodeOutput):
        """Execute a single node."""
        instance = flow_node.instance
        node_type = instance.identifier()
        
        # Emit started
        self.event_emitter.emit_started(flow_node.id, node_type)
        
        try:
            # Execute
            data = await self.executor.execute_in_pool(
                instance.execution_pool, instance, input_data
            )
            
            # Emit completed
            route = None
            if isinstance(instance, ConditionalNode) and instance.output:
                route = instance.output
            
            self.event_emitter.emit_completed(flow_node.id, node_type, data.data, route)
            
            # Continue traversal if not non-blocking
            if not isinstance(instance, NonBlockingNode):
                await self.process_next_nodes(flow_node, data)
        except Exception as e:
            self.event_emitter.emit_failed(flow_node.id, node_type, str(e))
            raise

# Node Initialization - Separate class
class NodeInitializer:
    """Initializes nodes in flow graph."""
    
    async def initialize_all(self, producer_flow_node: FlowNode):
        """Initialize all nodes starting from producer."""
        visited = set()
        await self._init_recursive(producer_flow_node, visited)
    
    async def _init_recursive(self, flow_node: FlowNode, visited: set):
        """Recursively initialize node and downstream nodes."""
        if flow_node.id in visited:
            return
        visited.add(flow_node.id)
        
        await flow_node.instance.init()
        
        for branch_nodes in flow_node.next.values():
            for next_node in branch_nodes:
                await self._init_recursive(next_node, visited)

# Refactored FlowRunner - Single Responsibility: Loop coordination
class FlowRunner:
    """Manages a single flow loop - coordinates execution components."""
    
    def __init__(
        self,
        producer_flow_node: FlowNode,
        executor: Optional[PoolExecutor] = None,
        events: Optional[WorkflowEventEmitter] = None,
        event_emitter: Optional[NodeEventEmitter] = None,
        graph_traverser: Optional[FlowGraphTraverser] = None,
        node_initializer: Optional[NodeInitializer] = None
    ):
        self.producer_flow_node = producer_flow_node
        self.producer = producer_flow_node.instance
        self.executor = executor or PoolExecutor()
        self.events = events
        
        # Initialize components
        self._event_emitter = event_emitter or NodeEventEmitter(events)
        self._graph_traverser = graph_traverser or FlowGraphTraverser(
            self._event_emitter,
            self.executor
        )
        self._node_initializer = node_initializer or NodeInitializer()
        
        self.running = False
        self.loop_count = 0
    
    async def start(self):
        """Start the flow loop - coordinates components."""
        self.running = True
        await self._node_initializer.initialize_all(self.producer_flow_node)
        
        try:
            while self.running:
                self.loop_count += 1
                try:
                    producer_type = self.producer.identifier()
                    
                    # Emit started
                    self._event_emitter.emit_started(self.producer_flow_node.id, producer_type)
                    
                    # Execute
                    data = await self.executor.execute_in_pool(
                        self.producer.execution_pool,
                        self.producer,
                        NodeOutput(data={})
                    )
                    
                    # Emit completed
                    route = None
                    if isinstance(self.producer, ConditionalNode) and self.producer.output:
                        route = self.producer.output
                    
                    self._event_emitter.emit_completed(
                        self.producer_flow_node.id,
                        producer_type,
                        data.data if hasattr(data, 'data') else None,
                        route
                    )
                    
                    # Handle completion
                    if isinstance(data, ExecutionCompleted):
                        await self.kill_producer()
                    
                    # Process next nodes
                    await self._graph_traverser.process_next_nodes(
                        self.producer_flow_node,
                        data
                    )
                except Exception as e:
                    logger.exception("Error in loop", error=str(e))
                    await asyncio.sleep(1)
        finally:
            self.shutdown()
```

#### Benefits

- ✅ **Single Responsibility**: Each class handles one concern
- ✅ **Testability**: Can test event emission, graph traversal independently
- ✅ **Reusability**: Components can be reused in different contexts

---

### Violation 6: VideoStreamConsumer Multiple Concerns

**Location**: `apps/browsersession/consumers.py:22-223`

#### Problem

`VideoStreamConsumer` handles WebSocket communication, manager initialization, message routing, streaming coordination, and error handling.

#### Solution Approach

Extract manager initialization, message routing, and streaming coordination into separate classes.

---

### Violation 7: BaseForm Validation and Dependency Management

**Location**: `core/Node/Core/Form/Core/BaseForm.py:40-254`

#### Problem

`BaseForm` handles form validation, field management, dependency handling, and form rebinding.

#### Solution Approach

Already partially separated with `DependencyHandler`, but validation and field management could be further separated.

---

### Violation 8: BaseManager Validation and Error Handling

**Location**: `apps/browsersession/managers/base_manager.py:11-127`

#### Problem

`BaseManager` handles browser validation, page validation, error handling, and execution coordination.

#### Solution Approach

Extract validation helpers and error handling into separate classes (as suggested in ISP violations document).

---

## Implementation Guidelines

### Step-by-Step Refactoring Process

1. **Identify Responsibilities**
   - List all methods in the class
   - Group methods by what they do (not how)
   - Identify distinct reasons for change

2. **Extract Classes**
   - Create new classes for each responsibility
   - Move related methods to new classes
   - Update original class to delegate to new classes

3. **Update Dependencies**
   - Inject extracted classes via constructor
   - Update all callers
   - Maintain backward compatibility where possible

4. **Test Independently**
   - Write tests for each extracted class
   - Test original class with mocked dependencies
   - Ensure all tests pass

### Common Patterns to Use

1. **Composition Over Inheritance**: Use composition to combine responsibilities
2. **Dependency Injection**: Inject dependencies rather than creating them
3. **Facade Pattern**: Use facade to coordinate multiple components
4. **Strategy Pattern**: Extract varying behavior into strategies

---

## Priority Ranking

### High Priority (Fix First)

1. **BaseNode Multiple Responsibilities** ⭐⭐⭐
   - **Impact**: High - Core class used by all nodes
   - **Complexity**: High - Many responsibilities to extract
   - **Benefits**: Better testability, maintainability

2. **NodeExecutionService Mixed Concerns** ⭐⭐⭐
   - **Impact**: High - Used throughout workflow execution
   - **Complexity**: Medium - Clear separation points
   - **Benefits**: Easier testing, better separation

3. **NodeExecutor Overloaded Responsibilities** ⭐⭐⭐
   - **Impact**: High - Critical execution component
   - **Complexity**: High - Complex async logic
   - **Benefits**: Better error handling, timeout management

### Medium Priority

4. **FlowEngine Orchestration and Implementation** ⭐⭐
   - **Impact**: Medium - Core orchestration component
   - **Complexity**: Medium
   - **Benefits**: Clearer workflow loading

5. **FlowRunner Execution and Event Management** ⭐⭐
   - **Impact**: Medium - Execution coordination
   - **Complexity**: Medium
   - **Benefits**: Better event handling

### Low Priority

6. **VideoStreamConsumer Multiple Concerns** ⭐
7. **BaseForm Validation and Dependency Management** ⭐
8. **BaseManager Validation and Error Handling** ⭐

---

## Developer Checklist

### Before Refactoring

- [ ] Identify all responsibilities in the class
- [ ] Group methods by responsibility
- [ ] Determine reasons for change
- [ ] Review existing tests

### During Refactoring

- [ ] Extract classes for each responsibility
- [ ] Use dependency injection
- [ ] Maintain backward compatibility
- [ ] Write tests for extracted classes

### After Refactoring

- [ ] All tests pass
- [ ] No functionality lost
- [ ] Code is more testable
- [ ] Responsibilities are clear

### Verification Questions

- [ ] Does the class have only one reason to change?
- [ ] Can I test each responsibility independently?
- [ ] Are responsibilities clearly separated?
- [ ] Is the class focused on a single purpose?

---

## Summary

This document identified **8 major Single Responsibility Principle violations** in the codebase:

1. BaseNode handles form management, validation, template rendering, execution coordination
2. NodeExecutionService mixes database persistence, execution, error handling, result formatting
3. NodeExecutor handles loading, session management, async execution, timeout, cleanup, error transformation
4. FlowEngine mixes workflow loading, post-processing, event wiring, state tracking, execution
5. FlowRunner mixes execution, event emission, graph traversal, initialization
6. VideoStreamConsumer handles WebSocket, manager initialization, routing, streaming
7. BaseForm mixes validation, dependency management, field management
8. BaseManager mixes validation, error handling, execution coordination

Each violation has been documented with:
- Current problematic code
- Explanation of the problem
- Refactored solution with code examples
- Benefits of the fix

**Next Steps:**
1. Review this document with the team
2. Prioritize violations based on impact
3. Start refactoring high-priority violations
4. Update this document as violations are fixed
5. Use the checklist when writing new code

Remember: **Single Responsibility Principle is about having one reason to change. Each class should do one thing and do it well.**

---

## References

- [SOLID Principles - Single Responsibility](https://en.wikipedia.org/wiki/Single-responsibility_principle)
- [Clean Code by Robert C. Martin](https://www.amazon.com/Clean-Code-Handbook-Software-Craftsmanship/dp/0132350882)
- Related Documentation:
  - [Dependency-Inversion-Violations.md](Dependency-Inversion-Violations.md)
  - [Interface-Segregation-Principle-Violations.md](Interface-Segregation-Principle-Violations.md)
  - [Open-Closed-Principle-Violations.md](Open-Closed-Principle-Violations.md)

---
