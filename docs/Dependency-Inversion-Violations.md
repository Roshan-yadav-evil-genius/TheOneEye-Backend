# Dependency Inversion Principle Violations

## Table of Contents

1. [Introduction](#introduction)
2. [Violations Catalog](#violations-catalog)
   - [Violation 1: FlowEngine Direct Instantiation](#violation-1-flowengine-direct-instantiation)
   - [Violation 2: ServiceContainer Internal Creation](#violation-2-servicecontainer-internal-creation)
   - [Violation 3: InteractionManager Direct Instantiation](#violation-3-interactionmanager-direct-instantiation)
   - [Violation 4: VideoStreamConsumer Manager Creation](#violation-4-videostreamconsumer-manager-creation)
   - [Violation 5: Node Classes DataStore Instantiation](#violation-5-node-classes-datastore-instantiation)
   - [Violation 6: QueueMapper Concrete Type Checks](#violation-6-queuemapper-concrete-type-checks)
   - [Violation 7: FlowRunner Default Executor](#violation-7-flowrunner-default-executor)
   - [Violation 8: Global Service Instances](#violation-8-global-service-instances)
3. [Implementation Guidelines](#implementation-guidelines)
4. [Priority Ranking](#priority-ranking)
5. [Developer Checklist](#developer-checklist)

---

## Introduction

### What is Dependency Inversion Principle?

The **Dependency Inversion Principle (DIP)** is one of the SOLID principles of object-oriented design. It states:

> **High-level modules should not depend on low-level modules. Both should depend on abstractions.**
> 
> **Abstractions should not depend on details. Details should depend on abstractions.**

### Why It Matters

Violating DIP leads to:

- **Tight Coupling**: High-level modules become tightly coupled to specific implementations
- **Reduced Testability**: Difficult to mock dependencies for unit testing
- **Reduced Flexibility**: Hard to swap implementations without modifying high-level code
- **Violation of Open/Closed Principle**: Changes to low-level modules require changes to high-level modules

### How Violations Impact the Codebase

1. **Testing Challenges**: Direct instantiation makes it impossible to inject test doubles
2. **Maintenance Burden**: Changes to concrete classes ripple through dependent code
3. **Scalability Issues**: Hard to introduce new implementations or variants
4. **Code Reusability**: Components cannot be reused in different contexts

---

## Violations Catalog

### Violation 1: FlowEngine Direct Instantiation

**Location**: `core/Workflow/flow_engine.py:28-38, 44, 145`

#### Current Implementation (Before)

```python
class FlowEngine:
    _post_processors: List[Type[PostProcessor]] = [QueueMapper, NodeValidator]

    def __init__(self, workflow_id: Optional[str] = None):
        self.workflow_id = workflow_id
        self.data_store = DataStore()  # ❌ Direct instantiation
        self.flow_runners: List[FlowRunner] = []
        self.flow_graph = FlowGraph()  # ❌ Direct instantiation
        self.flow_analyzer = FlowAnalyzer(self.flow_graph)  # ❌ Direct instantiation
        self.flow_builder = FlowBuilder(self.flow_graph, NodeRegistry())  # ❌ Direct instantiation
        
        # Event system for real-time updates
        self.events = WorkflowEventEmitter(workflow_id)  # ❌ Direct instantiation
        self.state_tracker: Optional[ExecutionStateTracker] = None

    def create_loop(self, producer_flow_node: FlowNode):
        # ...
        runner = FlowRunner(producer_flow_node, events=self.events)  # ❌ Direct instantiation
        self.flow_runners.append(runner)

    def load_workflow(self, workflow_json: Dict[str, Any]):
        # ...
        for processor_class in self._post_processors:
            processor = processor_class(self.flow_graph)  # ❌ Direct instantiation
            processor.execute()
```

#### Problem

`FlowEngine` is a high-level orchestration module that directly creates all its dependencies. This violates DIP because:

1. **Tight Coupling**: `FlowEngine` is bound to specific implementations (`DataStore`, `FlowGraph`, etc.)
2. **Testing Difficulty**: Cannot inject mock objects for unit testing
3. **Inflexibility**: Cannot swap implementations (e.g., use a different storage backend)
4. **Hidden Dependencies**: Dependencies are not visible in the constructor signature

#### Solution Approach

1. **Define Abstractions**: Create protocols/interfaces for key dependencies
2. **Constructor Injection**: Accept dependencies via constructor parameters
3. **Factory Pattern**: Use factories for complex object creation
4. **Optional Dependencies**: Provide sensible defaults while allowing injection

#### Refactored Implementation (After)

```python
from typing import Protocol, Optional
from abc import ABC, abstractmethod

# Define abstractions
class IDataStore(Protocol):
    """Storage abstraction interface"""
    async def get(self, key: str): ...
    async def set(self, key: str, value: Any): ...
    # ... other methods

class IFlowGraph(Protocol):
    """Graph abstraction interface"""
    def add_node(self, node: FlowNode): ...
    def connect_nodes(self, source: str, target: str, key: str): ...
    # ... other methods

class IEventEmitter(Protocol):
    """Event system abstraction"""
    def emit_node_started(self, node_id: str, node_type: str): ...
    def subscribe(self, event: str, callback: Callable): ...
    # ... other methods

class IPostProcessorFactory(Protocol):
    """Factory for creating post-processors"""
    def create_processors(self, graph: IFlowGraph) -> List[PostProcessor]: ...

class FlowEngine:
    _post_processors: List[Type[PostProcessor]] = [QueueMapper, NodeValidator]

    def __init__(
        self,
        workflow_id: Optional[str] = None,
        data_store: Optional[IDataStore] = None,
        flow_graph: Optional[IFlowGraph] = None,
        flow_analyzer: Optional[FlowAnalyzer] = None,
        flow_builder: Optional[FlowBuilder] = None,
        event_emitter: Optional[IEventEmitter] = None,
        node_registry: Optional[NodeRegistry] = None,
        post_processor_factory: Optional[IPostProcessorFactory] = None
    ):
        self.workflow_id = workflow_id
        
        # Use injected dependencies or create defaults
        self.data_store = data_store or DataStore()
        self.flow_graph = flow_graph or FlowGraph()
        self.flow_analyzer = flow_analyzer or FlowAnalyzer(self.flow_graph)
        
        # NodeRegistry should be injected
        registry = node_registry or NodeRegistry()
        self.flow_builder = flow_builder or FlowBuilder(self.flow_graph, registry)
        
        # Event system
        self.events = event_emitter or WorkflowEventEmitter(workflow_id)
        self.state_tracker: Optional[ExecutionStateTracker] = None
        
        # Post-processor factory
        self._post_processor_factory = post_processor_factory or DefaultPostProcessorFactory()

    def create_loop(
        self,
        producer_flow_node: FlowNode,
        runner_factory: Optional[Callable[[FlowNode, IEventEmitter], FlowRunner]] = None
    ):
        producer = producer_flow_node.instance
        if not isinstance(producer, ProducerNode):
            raise ValueError(f"Node {producer_flow_node.id} is not a ProducerNode")
        
        # Use factory or default
        create_runner = runner_factory or (lambda node, events: FlowRunner(node, events=events))
        runner = create_runner(producer_flow_node, self.events)
        self.flow_runners.append(runner)

    def load_workflow(self, workflow_json: Dict[str, Any]):
        self.flow_builder.load_workflow(workflow_json)

        # Use factory to create processors
        processors = self._post_processor_factory.create_processors(self.flow_graph)
        for processor in processors:
            processor.execute()
```

#### Benefits

- ✅ **Testability**: Can inject mocks for all dependencies
- ✅ **Flexibility**: Can swap implementations without changing `FlowEngine`
- ✅ **Explicit Dependencies**: Dependencies are visible in constructor
- ✅ **Single Responsibility**: `FlowEngine` focuses on orchestration, not object creation

---

### Violation 2: ServiceContainer Internal Creation

**Location**: `core/views/services/__init__.py:42-69`

#### Current Implementation (Before)

```python
class ServiceContainer:
    def __init__(self, project_root: Optional[Path] = None):
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent
        
        self._project_root = project_root
        
        # Lazy-initialized services
        self._node_registry: Optional[NodeRegistry] = None
        self._node_loader: Optional[NodeLoader] = None
        self._form_loader: Optional[FormLoader] = None
        self._node_executor: Optional[NodeExecutor] = None
    
    @property
    def node_registry(self) -> NodeRegistry:
        """Get or create NodeRegistry instance."""
        if self._node_registry is None:
            from ..scanner import create_scanner
            scanner = create_scanner()  # ❌ Direct instantiation
            self._node_registry = NodeRegistry(scanner)  # ❌ Direct instantiation
        return self._node_registry
    
    @property
    def node_loader(self) -> NodeLoader:
        """Get or create NodeLoader instance."""
        if self._node_loader is None:
            self._node_loader = NodeLoader(self._project_root)  # ❌ Direct instantiation
        return self._node_loader
    
    @property
    def form_loader(self) -> FormLoader:
        """Get or create FormLoader instance."""
        if self._form_loader is None:
            self._form_loader = FormLoader(self.node_loader)  # ❌ Direct instantiation
        return self._form_loader
    
    @property
    def node_executor(self) -> NodeExecutor:
        """Get or create NodeExecutor instance."""
        if self._node_executor is None:
            self._node_executor = NodeExecutor(self.node_loader)  # ❌ Direct instantiation
        return self._node_executor
```

#### Problem

The `ServiceContainer` creates all dependencies internally, which:

1. **Hides Dependencies**: Dependencies are created inside properties, not visible externally
2. **Hard to Test**: Cannot inject test doubles
3. **Tight Coupling**: Container is bound to specific implementations
4. **Circular Dependencies Risk**: `form_loader` depends on `node_loader`, creating implicit dependency chain

#### Solution Approach

1. **Accept Dependencies in Constructor**: Allow injection of all dependencies
2. **Factory Pattern**: Use factory functions for default creation
3. **Builder Pattern**: Optional builder for complex configurations
4. **Lazy Initialization with Factories**: Use factory functions instead of direct instantiation

#### Refactored Implementation (After)

```python
from typing import Optional, Callable, Protocol
from pathlib import Path

class IScanner(Protocol):
    """Scanner abstraction"""
    def scan(self) -> List[Dict]: ...

class INodeRegistry(Protocol):
    """Node registry abstraction"""
    def get_node(self, node_type: str): ...
    def refresh(self): ...

# Factory type aliases
NodeRegistryFactory = Callable[[IScanner], INodeRegistry]
NodeLoaderFactory = Callable[[Path], NodeLoader]
FormLoaderFactory = Callable[[NodeLoader], FormLoader]
NodeExecutorFactory = Callable[[NodeLoader], NodeExecutor]

class ServiceContainer:
    def __init__(
        self,
        project_root: Optional[Path] = None,
        # Factories for creating services
        scanner_factory: Optional[Callable[[], IScanner]] = None,
        node_registry_factory: Optional[NodeRegistryFactory] = None,
        node_loader_factory: Optional[NodeLoaderFactory] = None,
        form_loader_factory: Optional[FormLoaderFactory] = None,
        node_executor_factory: Optional[NodeExecutorFactory] = None,
        # Or inject services directly
        node_registry: Optional[INodeRegistry] = None,
        node_loader: Optional[NodeLoader] = None,
        form_loader: Optional[FormLoader] = None,
        node_executor: Optional[NodeExecutor] = None
    ):
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent
        
        self._project_root = project_root
        
        # Use factories or defaults
        self._scanner_factory = scanner_factory or (lambda: create_scanner())
        self._node_registry_factory = node_registry_factory or NodeRegistry
        self._node_loader_factory = node_loader_factory or NodeLoader
        self._form_loader_factory = form_loader_factory or FormLoader
        self._node_executor_factory = node_executor_factory or NodeExecutor
        
        # Store injected services or None for lazy creation
        self._node_registry = node_registry
        self._node_loader = node_loader
        self._form_loader = form_loader
        self._node_executor = node_executor
    
    @property
    def node_registry(self) -> INodeRegistry:
        """Get or create NodeRegistry instance."""
        if self._node_registry is None:
            scanner = self._scanner_factory()
            self._node_registry = self._node_registry_factory(scanner)
        return self._node_registry
    
    @property
    def node_loader(self) -> NodeLoader:
        """Get or create NodeLoader instance."""
        if self._node_loader is None:
            self._node_loader = self._node_loader_factory(self._project_root)
        return self._node_loader
    
    @property
    def form_loader(self) -> FormLoader:
        """Get or create FormLoader instance."""
        if self._form_loader is None:
            self._form_loader = self._form_loader_factory(self.node_loader)
        return self._form_loader
    
    @property
    def node_executor(self) -> NodeExecutor:
        """Get or create NodeExecutor instance."""
        if self._node_executor is None:
            self._node_executor = self._node_executor_factory(self.node_loader)
        return self._node_executor

# Factory function with sensible defaults
def create_services(
    project_root: Optional[Path] = None,
    **kwargs  # Allow overriding any factory or service
) -> ServiceContainer:
    """Factory function to create a service container."""
    return ServiceContainer(project_root=project_root, **kwargs)
```

#### Benefits

- ✅ **Testability**: Can inject mocks or test implementations
- ✅ **Flexibility**: Can override any factory or service
- ✅ **Explicit Dependencies**: Dependencies are visible in constructor
- ✅ **Backward Compatible**: Default factories maintain existing behavior

---

### Violation 3: InteractionManager Direct Instantiation

**Location**: `apps/browsersession/managers/interaction_manager.py:13-28`

#### Current Implementation (Before)

```python
class InteractionManager:
    """Manages all user interaction components for a single page."""
    
    def __init__(self, fps: float = None, quality: int = None):
        """
        Initialize interaction manager.
        Creates all internal components (streamer, controllers) internally.
        """
        # Create components internally
        self.screenshot_streamer = ScreenshotStreamer(  # ❌ Direct instantiation
            fps=fps if fps is not None else StreamConfig.STREAMING_FPS,
            quality=quality if quality is not None else StreamConfig.STREAMING_QUALITY
        )
        self.mouse_controller = MouseController()  # ❌ Direct instantiation
        self.keyboard_controller = KeyboardController()  # ❌ Direct instantiation
        self._page: Optional[Page] = None
```

#### Problem

`InteractionManager` creates all its dependencies internally, making it:

1. **Hard to Test**: Cannot inject mock controllers for testing
2. **Inflexible**: Cannot use different controller implementations
3. **Tight Coupling**: Bound to specific `ScreenshotStreamer`, `MouseController`, `KeyboardController` classes

#### Solution Approach

1. **Constructor Injection**: Accept dependencies via constructor
2. **Optional Parameters**: Provide defaults while allowing injection
3. **Factory Pattern**: Use factory for complex initialization

#### Refactored Implementation (After)

```python
from typing import Optional, Protocol
from playwright.async_api import Page

class IScreenshotStreamer(Protocol):
    """Screenshot streaming abstraction"""
    def set_page(self, page: Optional[Page]) -> None: ...
    def stop(self) -> None: ...
    async def stream(self, send_callback: Callable) -> None: ...

class IMouseController(Protocol):
    """Mouse control abstraction"""
    page: Optional[Page]
    async def click(self, x: int, y: int) -> None: ...
    # ... other methods

class IKeyboardController(Protocol):
    """Keyboard control abstraction"""
    page: Optional[Page]
    async def type(self, text: str) -> None: ...
    # ... other methods

class InteractionManager:
    """Manages all user interaction components for a single page."""
    
    def __init__(
        self,
        fps: float = None,
        quality: int = None,
        screenshot_streamer: Optional[IScreenshotStreamer] = None,
        mouse_controller: Optional[IMouseController] = None,
        keyboard_controller: Optional[IKeyboardController] = None
    ):
        """
        Initialize interaction manager.
        
        Args:
            fps: Frames per second for streaming (defaults to StreamConfig.STREAMING_FPS)
            quality: JPEG quality for screenshots (defaults to StreamConfig.STREAMING_QUALITY)
            screenshot_streamer: Optional streamer instance (creates default if not provided)
            mouse_controller: Optional mouse controller (creates default if not provided)
            keyboard_controller: Optional keyboard controller (creates default if not provided)
        """
        # Use injected dependencies or create defaults
        self.screenshot_streamer = screenshot_streamer or ScreenshotStreamer(
            fps=fps if fps is not None else StreamConfig.STREAMING_FPS,
            quality=quality if quality is not None else StreamConfig.STREAMING_QUALITY
        )
        self.mouse_controller = mouse_controller or MouseController()
        self.keyboard_controller = keyboard_controller or KeyboardController()
        self._page: Optional[Page] = None
```

#### Benefits

- ✅ **Testability**: Can inject mock controllers for unit testing
- ✅ **Flexibility**: Can use different implementations (e.g., different streaming backends)
- ✅ **Explicit Dependencies**: Dependencies are visible in constructor
- ✅ **Backward Compatible**: Defaults maintain existing behavior

---

### Violation 4: VideoStreamConsumer Manager Creation

**Location**: `apps/browsersession/consumers.py:40-56, 161-181`

#### Current Implementation (Before)

```python
class VideoStreamConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.streaming = False
        self.browser_manager: BrowserManager = None
        self.streaming_task = None
        
        # Initialize WebSocket message sender
        self.message_sender = WebSocketMessageSender(self.send)  # ❌ Direct instantiation
        
        # Initialize interaction manager (creates components internally)
        self.interaction_manager = InteractionManager()  # ❌ Direct instantiation
        
        # Initialize message router with handlers from interaction manager
        self.message_router = MessageRouter(  # ❌ Direct instantiation
            mouse_handler=MouseHandler(self.interaction_manager.mouse_controller),
            keyboard_handler=KeyboardHandler(self.interaction_manager.keyboard_controller),
            start_callback=None
        )

    async def start_streaming(self, session_id: str = None):
        # ...
        # Initialize browser manager first (without callbacks yet)
        self.browser_manager = BrowserManager(  # ❌ Direct instantiation
            viewport_width=StreamConfig.CANVAS_WIDTH,
            viewport_height=StreamConfig.CANVAS_HEIGHT
        )
        
        # Initialize managers that depend on browser_manager
        self.page_manager = PageManager(  # ❌ Direct instantiation
            browser_manager=self.browser_manager,
            interaction_manager=self.interaction_manager,
            message_sender=self.message_sender
        )
        
        self.navigation_manager = NavigationManager(  # ❌ Direct instantiation
            browser_manager=self.browser_manager,
            message_sender=self.message_sender
        )
        
        self.page_event_coordinator = PageEventCoordinator(  # ❌ Direct instantiation
            page_manager=self.page_manager,
            message_sender=self.message_sender
        )
```

#### Problem

`VideoStreamConsumer` directly creates all managers, which:

1. **Complex Initialization**: Consumer handles too many responsibilities
2. **Hard to Test**: Cannot inject mock managers
3. **Tight Coupling**: Bound to specific manager implementations
4. **Difficult to Reuse**: Cannot reuse consumer with different manager configurations

#### Solution Approach

1. **Dependency Injection Container**: Use a container to manage dependencies
2. **Factory Pattern**: Create a factory for consumer initialization
3. **Builder Pattern**: Use builder for complex manager setup
4. **Service Locator**: Alternative pattern for dependency resolution

#### Refactored Implementation (After)

```python
from typing import Optional, Protocol, Dict, Any

class IManagerFactory(Protocol):
    """Factory for creating managers"""
    def create_browser_manager(self, viewport_width: int, viewport_height: int) -> BrowserManager: ...
    def create_page_manager(self, browser_manager: BrowserManager, **kwargs) -> PageManager: ...
    def create_navigation_manager(self, browser_manager: BrowserManager, **kwargs) -> NavigationManager: ...
    def create_interaction_manager(self, **kwargs) -> InteractionManager: ...
    def create_message_sender(self, send_func: Callable) -> WebSocketMessageSender: ...
    def create_message_router(self, **kwargs) -> MessageRouter: ...

class ManagerFactory:
    """Default factory implementation"""
    def create_browser_manager(self, viewport_width: int, viewport_height: int) -> BrowserManager:
        return BrowserManager(viewport_width=viewport_width, viewport_height=viewport_height)
    
    def create_page_manager(self, browser_manager: BrowserManager, **kwargs) -> PageManager:
        return PageManager(browser_manager=browser_manager, **kwargs)
    
    # ... other factory methods

class VideoStreamConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, manager_factory: Optional[IManagerFactory] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._manager_factory = manager_factory or ManagerFactory()
    
    async def connect(self):
        await self.accept()
        self.streaming = False
        self.browser_manager: BrowserManager = None
        self.streaming_task = None
        
        # Use factory to create managers
        self.message_sender = self._manager_factory.create_message_sender(self.send)
        self.interaction_manager = self._manager_factory.create_interaction_manager()
        
        self.message_router = self._manager_factory.create_message_router(
            mouse_handler=MouseHandler(self.interaction_manager.mouse_controller),
            keyboard_handler=KeyboardHandler(self.interaction_manager.keyboard_controller),
            start_callback=None
        )
        
        # Managers created in start_streaming
        self.page_manager: PageManager = None
        self.navigation_manager: NavigationManager = None
        self.page_event_coordinator: PageEventCoordinator = None

    async def start_streaming(self, session_id: str = None):
        if self.streaming:
            return
        
        self.streaming = True
        
        try:
            # Use factory to create managers
            self.browser_manager = self._manager_factory.create_browser_manager(
                viewport_width=StreamConfig.CANVAS_WIDTH,
                viewport_height=StreamConfig.CANVAS_HEIGHT
            )
            
            self.page_manager = self._manager_factory.create_page_manager(
                browser_manager=self.browser_manager,
                interaction_manager=self.interaction_manager,
                message_sender=self.message_sender
            )
            
            self.navigation_manager = self._manager_factory.create_navigation_manager(
                browser_manager=self.browser_manager,
                message_sender=self.message_sender
            )
            
            self.page_event_coordinator = self._manager_factory.create_page_event_coordinator(
                page_manager=self.page_manager,
                message_sender=self.message_sender
            )
            
            # ... rest of initialization
```

#### Benefits

- ✅ **Testability**: Can inject factory with mock managers
- ✅ **Separation of Concerns**: Consumer doesn't know how managers are created
- ✅ **Flexibility**: Can use different factory implementations
- ✅ **Reusability**: Consumer can be reused with different manager configurations

---

### Violation 5: Node Classes DataStore Instantiation

**Location**: 
- `core/Node/Nodes/System/QueueReader/node.py:26-28`
- `core/Node/Nodes/System/QueueWriter/node.py:24-26`
- `core/Node/Nodes/Delay/DynamicDelay/node.py:71-73`

#### Current Implementation (Before)

```python
# QueueReader
class QueueReader(ProducerNode):
    async def setup(self):
        """Initialize the DataStore connection once during node setup."""
        self.data_store = DataStore()  # ❌ Direct instantiation

# QueueWriter
class QueueWriter(NonBlockingNode):
    async def setup(self):
        """Initialize the DataStore connection once during node setup."""
        self.data_store = DataStore()  # ❌ Direct instantiation

# DynamicDelayNode
class DynamicDelayNode(BlockingNode):
    async def setup(self):
        """Initialize DataStore for storing delay list."""
        self.data_store = DataStore()  # ❌ Direct instantiation
        self._cache_key = f"delay_node:{self.node_config.id}:delays"
```

#### Problem

Node classes directly instantiate `DataStore`, which:

1. **Tight Coupling**: Nodes are bound to specific `DataStore` implementation
2. **Testing Difficulty**: Cannot inject mock storage for testing
3. **Configuration Issues**: Cannot use different storage backends per node
4. **Resource Management**: Each node creates its own connection (inefficient)

#### Solution Approach

1. **Storage Context Injection**: Inject storage via node context or configuration
2. **Abstract Storage Interface**: Define storage protocol/interface
3. **Shared Storage Instance**: Use shared storage instance from workflow context
4. **Factory Pattern**: Use factory to create storage instances

#### Refactored Implementation (After)

```python
from typing import Protocol, Optional
from abc import ABC

# Define storage abstraction
class IStorage(Protocol):
    """Storage abstraction for nodes"""
    async def get(self, key: str) -> Any: ...
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None: ...
    async def push(self, queue_name: str, data: Dict) -> None: ...
    async def pop(self, queue_name: str, timeout: int = 0) -> Dict: ...
    async def close(self) -> None: ...

# BaseNode modification (conceptual)
class BaseNode(ABC):
    """Base node with storage injection support"""
    
    def __init__(self, node_config: NodeConfig, storage: Optional[IStorage] = None):
        self.node_config = node_config
        self._storage = storage  # Injected storage
    
    @property
    def storage(self) -> IStorage:
        """Get storage instance, create default if not injected"""
        if self._storage is None:
            # Fallback to default (for backward compatibility)
            self._storage = DataStore()
        return self._storage

# Refactored QueueReader
class QueueReader(ProducerNode):
    async def setup(self):
        """Initialize storage connection if needed."""
        # Storage is injected via BaseNode.__init__ or available via self.storage
        # No need to create it here
        pass
    
    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        queue_name = self.node_config.data.config["queue_name"]
        
        # Use injected storage
        result = await self.storage.pop(queue_name, timeout=0)
        
        if result.get("metadata", {}).get("__execution_completed__"):
            return ExecutionCompleted(**result)
        
        return NodeOutput(**result)

# Refactored QueueWriter
class QueueWriter(NonBlockingNode):
    async def setup(self):
        """Storage is injected, no initialization needed."""
        pass
    
    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        queue_name = self.node_config.data.config["queue_name"]
        
        # Use injected storage
        await self.storage.push(queue_name, node_data.to_dict())
        return node_data
    
    async def cleanup(self, node_data: NodeOutput = None):
        await self.execute(node_data)
        await self.storage.close()

# Refactored DynamicDelayNode
class DynamicDelayNode(BlockingNode):
    async def setup(self):
        """Storage is injected, just set cache key."""
        self._cache_key = f"delay_node:{self.node_config.id}:delays"
    
    async def _get_or_create_delay_list(self) -> List[float]:
        """Get existing delay list from cache or create new one."""
        delays = await self.storage.get(self._cache_key)  # Use injected storage
        
        if not delays or len(delays) == 0:
            delays = self._generate_delay_list()
            await self._save_delay_list(delays)
        
        return delays
    
    async def _save_delay_list(self, delays: List[float]):
        """Save delay list to cache."""
        total_time = self.form.cleaned_data.get('total_time', 1)
        unit = self.form.cleaned_data.get('unit', 'hours')
        ttl = int(total_time * TIME_UNIT_TO_SECONDS.get(unit, 3600) * 1.5)
        await self.storage.set(self._cache_key, delays, ttl=ttl)  # Use injected storage
```

**NodeRegistry modification needed:**

```python
class NodeRegistry:
    def __init__(self, scanner, storage_factory: Optional[Callable[[], IStorage]] = None):
        self._scanner = scanner
        self._storage_factory = storage_factory or (lambda: DataStore())
    
    def create_node(self, node_config: NodeConfig, storage: Optional[IStorage] = None) -> BaseNode:
        """Create node instance with optional storage injection."""
        node_class = self._get_node_class(node_config.type)
        
        # Use provided storage or create default
        node_storage = storage or self._storage_factory()
        
        # Create node with storage
        node = node_class(node_config, storage=node_storage)
        return node
```

#### Benefits

- ✅ **Testability**: Can inject mock storage for testing
- ✅ **Resource Efficiency**: Can share storage instance across nodes
- ✅ **Flexibility**: Can use different storage backends per workflow
- ✅ **Configuration**: Storage can be configured at workflow level

---

### Violation 6: QueueMapper Concrete Type Checks

**Location**: `core/Workflow/PostProcessing/queue_mapper.py:4-6, 54-76`

#### Current Implementation (Before)

```python
from Node.Nodes.System.QueueWriter import QueueWriter
from Node.Nodes.System.QueueReader import QueueReader

class QueueMapper(PostProcessor):
    def _is_queue_node(self, node_instance: BaseNode) -> bool:
        """
        Check if node is QueueWriter or a subclass.
        """
        return isinstance(node_instance, QueueWriter)  # ❌ Concrete type check
    
    def _is_queue_reader(self, node_instance: BaseNode) -> bool:
        """
        Check if node is QueueReader or a subclass.
        """
        return isinstance(node_instance, QueueReader)  # ❌ Concrete type check
```

#### Problem

Using `isinstance()` checks on concrete classes violates DIP because:

1. **Tight Coupling**: Post-processor depends on specific node implementations
2. **Inflexibility**: Cannot work with alternative queue node implementations
3. **Violates Open/Closed Principle**: Must modify code to support new queue node types

#### Solution Approach

1. **Abstract Base Classes**: Define `IQueueWriter` and `IQueueReader` interfaces
2. **Protocol-Based Checking**: Use Python protocols for structural typing
3. **Duck Typing**: Check for required methods/attributes instead of types
4. **Registration Pattern**: Register queue node types dynamically

#### Refactored Implementation (After)

**Option 1: Using Abstract Base Classes**

```python
from abc import ABC, abstractmethod
from typing import Protocol

# Define interfaces
class IQueueWriter(ABC):
    """Interface for queue writer nodes"""
    
    @abstractmethod
    def get_queue_name(self) -> str:
        """Get the queue name for this writer."""
        pass
    
    @abstractmethod
    async def push_to_queue(self, data: Dict) -> None:
        """Push data to queue."""
        pass

class IQueueReader(ABC):
    """Interface for queue reader nodes"""
    
    @abstractmethod
    def get_queue_name(self) -> str:
        """Get the queue name for this reader."""
        pass
    
    @abstractmethod
    async def pop_from_queue(self, timeout: int = 0) -> Dict:
        """Pop data from queue."""
        pass

# Update concrete classes to implement interfaces
class QueueWriter(NonBlockingNode, IQueueWriter):
    def get_queue_name(self) -> str:
        return self.node_config.data.config.get("queue_name", "default")
    
    async def push_to_queue(self, data: Dict) -> None:
        await self.storage.push(self.get_queue_name(), data)

class QueueReader(ProducerNode, IQueueReader):
    def get_queue_name(self) -> str:
        return self.node_config.data.config.get("queue_name", "default")
    
    async def pop_from_queue(self, timeout: int = 0) -> Dict:
        return await self.storage.pop(self.get_queue_name(), timeout=timeout)

# Refactored QueueMapper
class QueueMapper(PostProcessor):
    def _is_queue_writer(self, node_instance: BaseNode) -> bool:
        """Check if node implements IQueueWriter interface."""
        return isinstance(node_instance, IQueueWriter)
    
    def _is_queue_reader(self, node_instance: BaseNode) -> bool:
        """Check if node implements IQueueReader interface."""
        return isinstance(node_instance, IQueueReader)
```

**Option 2: Using Protocols (Structural Typing)**

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class QueueWriterProtocol(Protocol):
    """Protocol for queue writer nodes"""
    def get_queue_name(self) -> str: ...
    async def push_to_queue(self, data: Dict) -> None: ...

@runtime_checkable
class QueueReaderProtocol(Protocol):
    """Protocol for queue reader nodes"""
    def get_queue_name(self) -> str: ...
    async def pop_from_queue(self, timeout: int = 0) -> Dict: ...

class QueueMapper(PostProcessor):
    def _is_queue_writer(self, node_instance: BaseNode) -> bool:
        """Check if node conforms to QueueWriterProtocol."""
        return isinstance(node_instance, QueueWriterProtocol)
    
    def _is_queue_reader(self, node_instance: BaseNode) -> bool:
        """Check if node conforms to QueueReaderProtocol."""
        return isinstance(node_instance, QueueReaderProtocol)
```

**Option 3: Duck Typing (Attribute/Method Checking)**

```python
class QueueMapper(PostProcessor):
    def _is_queue_writer(self, node_instance: BaseNode) -> bool:
        """Check if node has queue writer capabilities."""
        return (
            hasattr(node_instance, 'get_queue_name') and
            callable(getattr(node_instance, 'get_queue_name', None)) and
            hasattr(node_instance, 'push_to_queue') and
            callable(getattr(node_instance, 'push_to_queue', None))
        )
    
    def _is_queue_reader(self, node_instance: BaseNode) -> bool:
        """Check if node has queue reader capabilities."""
        return (
            hasattr(node_instance, 'get_queue_name') and
            callable(getattr(node_instance, 'get_queue_name', None)) and
            hasattr(node_instance, 'pop_from_queue') and
            callable(getattr(node_instance, 'pop_from_queue', None))
        )
```

#### Benefits

- ✅ **Flexibility**: Can work with any implementation that conforms to interface
- ✅ **Extensibility**: New queue node types work automatically if they implement interface
- ✅ **Testability**: Can create mock implementations for testing
- ✅ **Loose Coupling**: Post-processor doesn't depend on concrete classes

---

### Violation 7: FlowRunner Default Executor

**Location**: `core/Workflow/execution/flow_runner.py:23-31`

#### Current Implementation (Before)

```python
class FlowRunner:
    def __init__(
        self, 
        producer_flow_node: FlowNode, 
        executor: Optional[PoolExecutor] = None,
        events: Optional["WorkflowEventEmitter"] = None
    ):
        self.producer_flow_node = producer_flow_node
        self.producer = producer_flow_node.instance
        self.executor = executor or PoolExecutor()  # ❌ Default concrete instantiation
        self.events = events
        self.running = False
        self.loop_count = 0
```

#### Problem

Defaulting to concrete `PoolExecutor` instance:

1. **Hidden Dependency**: Dependency creation is not explicit
2. **Testing Difficulty**: Hard to inject mock executor
3. **Inflexibility**: Cannot use different executor implementations

#### Solution Approach

1. **Require Injection**: Make executor a required parameter
2. **Factory Pattern**: Use factory function for default creation
3. **Abstract Interface**: Define executor protocol/interface

#### Refactored Implementation (After)

```python
from typing import Protocol, Optional

class IExecutor(Protocol):
    """Executor abstraction"""
    async def execute_in_pool(
        self, 
        pool_type: PoolType, 
        node: BaseNode, 
        input_data: NodeOutput
    ) -> NodeOutput: ...
    
    def shutdown(self, wait: bool = True) -> None: ...

class FlowRunner:
    def __init__(
        self, 
        producer_flow_node: FlowNode,
        executor: IExecutor,  # Required, no default
        events: Optional["WorkflowEventEmitter"] = None
    ):
        self.producer_flow_node = producer_flow_node
        self.producer = producer_flow_node.instance
        self.executor = executor  # Required injection
        self.events = events
        self.running = False
        self.loop_count = 0

# Factory function for convenience
def create_flow_runner(
    producer_flow_node: FlowNode,
    executor: Optional[IExecutor] = None,
    events: Optional["WorkflowEventEmitter"] = None
) -> FlowRunner:
    """Factory function to create FlowRunner with default executor if needed."""
    default_executor = executor or PoolExecutor()
    return FlowRunner(producer_flow_node, default_executor, events)
```

**Update FlowEngine:**

```python
class FlowEngine:
    def create_loop(
        self,
        producer_flow_node: FlowNode,
        executor: Optional[IExecutor] = None
    ):
        producer = producer_flow_node.instance
        if not isinstance(producer, ProducerNode):
            raise ValueError(f"Node {producer_flow_node.id} is not a ProducerNode")
        
        # Use provided executor or create default
        runner_executor = executor or PoolExecutor()
        runner = FlowRunner(producer_flow_node, runner_executor, events=self.events)
        self.flow_runners.append(runner)
```

#### Benefits

- ✅ **Explicit Dependencies**: Executor is clearly required
- ✅ **Testability**: Can inject mock executor easily
- ✅ **Flexibility**: Can use different executor implementations
- ✅ **Factory Pattern**: Factory function provides convenience while maintaining flexibility

---

### Violation 8: Global Service Instances

**Location**: 
- `apps/workflow/services/workflow_execution_service.py:105-106`
- `apps/workflow/services/dependency_service.py:113-114`

#### Current Implementation (Before)

```python
# workflow_execution_service.py
class WorkflowExecutionService:
    # ... methods ...
    
# Global instance for convenience
workflow_execution_service = WorkflowExecutionService()  # ❌ Global singleton

# dependency_service.py
class DependencyService:
    # ... methods ...

# Global instance for backward compatibility
dependency_service = DependencyService()  # ❌ Global singleton
```

#### Problem

Global singleton instances create:

1. **Tight Coupling**: Code depends on global state
2. **Testing Difficulty**: Cannot replace with mocks in tests
3. **Hidden Dependencies**: Dependencies are not explicit
4. **Thread Safety Issues**: Shared state can cause concurrency problems
5. **Configuration Problems**: Cannot have different configurations per context

#### Solution Approach

1. **Dependency Injection**: Inject services where needed
2. **Service Locator Pattern**: Use service locator (better than global, but still not ideal)
3. **Factory Functions**: Use factory functions instead of global instances
4. **Dependency Injection Container**: Use DI container for service management

#### Refactored Implementation (After)

**Option 1: Remove Globals, Use Factory Functions**

```python
# workflow_execution_service.py
class WorkflowExecutionService:
    """Service for managing workflow execution via Celery tasks."""
    
    @staticmethod
    def start_execution(workflow: WorkFlow, workflow_config: Dict[str, Any]) -> Dict[str, Any]:
        # ... implementation ...
        pass
    
    # ... other methods ...

# Remove global instance
# workflow_execution_service = WorkflowExecutionService()  # ❌ REMOVED

# Factory function instead
def create_workflow_execution_service() -> WorkflowExecutionService:
    """Factory function to create workflow execution service."""
    return WorkflowExecutionService()

# dependency_service.py
class DependencyService:
    # ... methods ...

# Remove global instance
# dependency_service = DependencyService()  # ❌ REMOVED

# Factory function instead
def create_dependency_service() -> DependencyService:
    """Factory function to create dependency service."""
    return DependencyService()
```

**Option 2: Dependency Injection in Views**

```python
# apps/workflow/Views/WorkFlow.py
class WorkFlowViewSet(ModelViewSet):
    queryset = WorkFlow.objects.all()
    serializer_class = WorkFlowSerializer
    
    def __init__(self, *args, execution_service: Optional[WorkflowExecutionService] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._execution_service = execution_service or WorkflowExecutionService()
    
    @action(detail=True, methods=["get"])
    def start_execution(self, request, pk=None):
        """Start workflow execution"""
        workflow = self.get_object()
        workflow_config = RawWorkFlawSerializer(workflow).data
        
        # Use injected service
        result = self._execution_service.start_execution(workflow, workflow_config)
        return Response(result)
```

**Option 3: Service Locator Pattern (Transitional)**

```python
class ServiceLocator:
    """Service locator for dependency resolution."""
    _services: Dict[Type, Any] = {}
    
    @classmethod
    def register(cls, service_type: Type, instance: Any):
        """Register a service instance."""
        cls._services[service_type] = instance
    
    @classmethod
    def get(cls, service_type: Type) -> Any:
        """Get a service instance."""
        if service_type not in cls._services:
            raise ValueError(f"Service {service_type} not registered")
        return cls._services[service_type]
    
    @classmethod
    def clear(cls):
        """Clear all registered services (useful for testing)."""
        cls._services.clear()

# Usage
class WorkFlowViewSet(ModelViewSet):
    @action(detail=True, methods=["get"])
    def start_execution(self, request, pk=None):
        workflow = self.get_object()
        workflow_config = RawWorkFlawSerializer(workflow).data
        
        # Get service from locator
        execution_service = ServiceLocator.get(WorkflowExecutionService)
        result = execution_service.start_execution(workflow, workflow_config)
        return Response(result)
```

#### Benefits

- ✅ **Testability**: Can inject test doubles
- ✅ **Explicit Dependencies**: Dependencies are visible
- ✅ **Flexibility**: Can use different service instances per context
- ✅ **No Global State**: Eliminates shared mutable state

---

## Implementation Guidelines

### Step-by-Step Refactoring Process

1. **Identify Dependencies**
   - List all dependencies created within the class
   - Determine which are high-level vs low-level modules

2. **Define Abstractions**
   - Create protocols/interfaces for key dependencies
   - Use `typing.Protocol` for structural typing
   - Or use `abc.ABC` for explicit interfaces

3. **Refactor Constructor**
   - Add dependency parameters to constructor
   - Provide sensible defaults for backward compatibility
   - Document required vs optional dependencies

4. **Update Callers**
   - Update all code that instantiates the class
   - Use factory functions for complex initialization
   - Consider dependency injection container

5. **Write Tests**
   - Add unit tests with mock dependencies
   - Verify behavior with different implementations
   - Test backward compatibility

### Testing Considerations

**Before Refactoring:**
```python
# Hard to test - cannot mock DataStore
def test_flow_engine():
    engine = FlowEngine(workflow_id="test")
    # Must use real DataStore, FlowGraph, etc.
    engine.load_workflow(workflow_json)
```

**After Refactoring:**
```python
# Easy to test - can inject mocks
def test_flow_engine():
    mock_data_store = Mock(spec=IDataStore)
    mock_flow_graph = Mock(spec=IFlowGraph)
    
    engine = FlowEngine(
        workflow_id="test",
        data_store=mock_data_store,
        flow_graph=mock_flow_graph
    )
    
    # Test with mocks
    engine.load_workflow(workflow_json)
    mock_flow_graph.add_node.assert_called()
```

### Migration Strategy

1. **Phase 1: Add Abstractions (Non-Breaking)**
   - Define protocols/interfaces
   - Keep existing code unchanged
   - Add new constructor parameters with defaults

2. **Phase 2: Update High-Priority Classes**
   - Refactor `FlowEngine` first (high impact)
   - Update `ServiceContainer` (used widely)
   - Refactor node classes (many instances)

3. **Phase 3: Update Callers**
   - Update code that creates refactored classes
   - Use factory functions for convenience
   - Gradually remove default instantiations

4. **Phase 4: Remove Globals**
   - Replace global instances with factories
   - Update all imports
   - Add deprecation warnings if needed

### Common Patterns to Use

1. **Protocol-Based Abstractions**
   ```python
   from typing import Protocol
   
   class IStorage(Protocol):
       async def get(self, key: str) -> Any: ...
       async def set(self, key: str, value: Any) -> None: ...
   ```

2. **Factory Functions**
   ```python
   def create_service(overrides: Optional[Dict] = None) -> Service:
       defaults = {...}
       config = {**defaults, **(overrides or {})}
       return Service(**config)
   ```

3. **Builder Pattern (for Complex Objects)**
   ```python
   class ServiceBuilder:
       def with_storage(self, storage: IStorage) -> 'ServiceBuilder': ...
       def with_logger(self, logger: ILogger) -> 'ServiceBuilder': ...
       def build(self) -> Service: ...
   ```

4. **Dependency Injection Container**
   ```python
   class Container:
       def register(self, interface: Type, implementation: Type): ...
       def resolve(self, interface: Type) -> Any: ...
   ```

---

## Priority Ranking

### High Priority (Fix First)

1. **FlowEngine Direct Instantiation** ⭐⭐⭐
   - **Impact**: High - Core orchestration component
   - **Complexity**: Medium
   - **Benefits**: Enables testing, allows different implementations

2. **Node Classes DataStore Instantiation** ⭐⭐⭐
   - **Impact**: High - Many node instances
   - **Complexity**: Medium
   - **Benefits**: Resource efficiency, testability, flexibility

3. **Global Service Instances** ⭐⭐⭐
   - **Impact**: High - Used throughout codebase
   - **Complexity**: Low
   - **Benefits**: Testability, explicit dependencies

### Medium Priority

4. **ServiceContainer Internal Creation** ⭐⭐
   - **Impact**: Medium - Used in views/services
   - **Complexity**: Medium
   - **Benefits**: Testability, flexibility

5. **QueueMapper Concrete Type Checks** ⭐⭐
   - **Impact**: Medium - Post-processing component
   - **Complexity**: Low
   - **Benefits**: Extensibility, loose coupling

6. **FlowRunner Default Executor** ⭐⭐
   - **Impact**: Medium - Execution component
   - **Complexity**: Low
   - **Benefits**: Testability, flexibility

### Low Priority (Can Wait)

7. **InteractionManager Direct Instantiation** ⭐
   - **Impact**: Low - Specific to browser session
   - **Complexity**: Low
   - **Benefits**: Testability

8. **VideoStreamConsumer Manager Creation** ⭐
   - **Impact**: Low - WebSocket consumer
   - **Complexity**: Medium
   - **Benefits**: Testability, separation of concerns

---

## Developer Checklist

Use this checklist when refactoring code to follow DIP:

### Before Refactoring

- [ ] Identify all dependencies created within the class
- [ ] Determine which dependencies should be abstracted
- [ ] Check if abstractions already exist
- [ ] Review existing tests to understand current behavior

### During Refactoring

- [ ] Define protocols/interfaces for key dependencies
- [ ] Add dependency parameters to constructor
- [ ] Provide sensible defaults for backward compatibility
- [ ] Update class documentation with dependency requirements
- [ ] Write unit tests with mock dependencies

### After Refactoring

- [ ] Update all callers to use new constructor
- [ ] Verify existing tests still pass
- [ ] Add new tests with mock dependencies
- [ ] Update documentation/examples
- [ ] Check for any remaining direct instantiations
- [ ] Review code for other DIP violations

### Verification Questions

- [ ] Can I inject a mock/test double for each dependency?
- [ ] Are dependencies visible in the constructor signature?
- [ ] Can I swap implementations without changing the class?
- [ ] Are there any global instances or singletons?
- [ ] Do I use `isinstance()` checks on concrete classes?
- [ ] Are factory functions used for complex initialization?

### Code Review Checklist

When reviewing code for DIP compliance:

- [ ] No direct instantiation of concrete classes in high-level modules
- [ ] Dependencies are injected via constructor
- [ ] Abstractions (protocols/interfaces) are used instead of concrete types
- [ ] No global singleton instances
- [ ] Factory patterns used for complex object creation
- [ ] Type checking uses interfaces/protocols, not concrete classes

---

## References

- [SOLID Principles - Dependency Inversion](https://en.wikipedia.org/wiki/Dependency_inversion_principle)
- [Python Protocols (PEP 544)](https://www.python.org/dev/peps/pep-0544/)
- [Dependency Injection in Python](https://python-dependency-injector.ets-labs.org/)
- Related Documentation:
  - [02-Workflow-Engine.md](02-Workflow-Engine.md)
  - [03-Execution-System.md](03-Execution-System.md)
  - [04-Node-System.md](04-Node-System.md)

---

## Summary

This document identified **8 major Dependency Inversion Principle violations** in the codebase:

1. FlowEngine directly instantiates 6+ dependencies
2. ServiceContainer creates dependencies internally
3. InteractionManager creates controllers internally
4. VideoStreamConsumer creates managers directly
5. Node classes instantiate DataStore directly
6. QueueMapper uses concrete type checks
7. FlowRunner defaults to concrete executor
8. Global service instances create tight coupling

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

Remember: **Dependency Inversion Principle is about depending on abstractions, not concrete implementations.**
