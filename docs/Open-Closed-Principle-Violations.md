# Open/Closed Principle Violations

## Table of Contents

1. [Introduction](#introduction)
2. [Violations Catalog](#violations-catalog)
   - [Violation 1: FlowRunner Node Type Handling](#violation-1-flowrunner-node-type-handling)
   - [Violation 2: flow_utils.node_type() Function](#violation-2-flow_utilsnode_type-function)
   - [Violation 3: BranchKeyNormalizer Hard-coded Branches](#violation-3-branchkeynormalizer-hard-coded-branches)
   - [Violation 4: PoolExecutor Pool Type Handling](#violation-4-poolexecutor-pool-type-handling)
   - [Violation 5: GoogleSheets Query Operators](#violation-5-googlesheets-query-operators)
   - [Violation 6: MetadataExtractor Port Generation](#violation-6-metadataextractor-port-generation)
   - [Violation 7: FlowEngine Post-Processors List](#violation-7-flowengine-post-processors-list)
   - [Violation 8: StringIterator Separator Handling](#violation-8-stringiterator-separator-handling)
3. [Implementation Guidelines](#implementation-guidelines)
4. [Priority Ranking](#priority-ranking)
5. [Developer Checklist](#developer-checklist)

---

## Introduction

### What is Open/Closed Principle?

The **Open/Closed Principle (OCP)** is one of the SOLID principles of object-oriented design. It states:

> **Software entities (classes, modules, functions, etc.) should be open for extension, but closed for modification.**

This means:
- **Open for Extension**: You should be able to add new functionality or behavior without modifying existing code
- **Closed for Modification**: Existing code should remain unchanged when adding new features

### Why It Matters

Violating OCP leads to:

- **Fragile Code**: Changes ripple through the codebase when adding new features
- **High Maintenance Cost**: Every new feature requires modifying existing, tested code
- **Increased Bug Risk**: Modifying working code introduces potential bugs
- **Tight Coupling**: Code becomes tightly coupled to specific implementations
- **Testing Burden**: Modified code requires re-testing of existing functionality

### How Violations Impact the Codebase

1. **Extensibility Issues**: Adding new node types, operators, or behaviors requires modifying multiple files
2. **Maintenance Burden**: Changes to existing code risk breaking working features
3. **Code Duplication**: Similar if-elif chains appear in multiple places
4. **Testing Complexity**: Modified code requires comprehensive regression testing

---

## Violations Catalog

### Violation 1: FlowRunner Node Type Handling

**Location**: `core/Workflow/execution/flow_runner.py:110-122, 150-152, 170-171`

#### Current Implementation (Before)

```python
async def _process_next_nodes(
    self, current_flow_node: FlowNode, input_data: NodeOutput
):
    """
    Recursively process downstream nodes.
    Handles branching logic:
    - If LogicalNode: Executes selected branch (if any).
    - Otherwise: Executes default branch or first available branch.
    """
    next_nodes: Optional[Dict[str, List[FlowNode]]] = current_flow_node.next
    if not next_nodes:
        return

    instance = current_flow_node.instance
    nodes_to_run: List[FlowNode] = []
    keys_to_process = set()

    # Determine which branches to follow
    if isinstance(input_data, ExecutionCompleted):
        # If Sentinel Pill, broadcast to ALL downstream nodes regardless of logic
        for key in next_nodes:
            keys_to_process.add(key)

    elif isinstance(instance, ConditionalNode):  # ❌ Type check
        # For LogicalNodes, we follow the selected output branch
        if instance.output:
            keys_to_process.add(instance.output)
    else:
        # For non-LogicalNodes, we follow the default branch
        keys_to_process.add("default")

    # ... later in the same method ...
    
    # Determine route for conditional nodes
    route = None
    if isinstance(next_instance, ConditionalNode):  # ❌ Type check
        route = next_instance.output

    # ... and another check ...
    
    if isinstance(next_instance, NonBlockingNode):  # ❌ Type check
        continue
```

#### Problem

`FlowRunner` uses multiple `isinstance()` checks to determine node behavior. This violates OCP because:

1. **Modification Required**: Adding a new node type requires modifying `_process_next_nodes()` method
2. **Multiple Check Points**: Type checking logic is scattered throughout the method
3. **Tight Coupling**: FlowRunner is tightly coupled to specific node type implementations
4. **Extensibility Issues**: Cannot add new node behaviors without modifying existing code

#### Solution Approach

1. **Strategy Pattern**: Use strategy pattern where each node type defines its own routing behavior
2. **Visitor Pattern**: Alternative approach using visitor pattern for node traversal
3. **Polymorphism**: Leverage polymorphism - nodes handle their own routing logic

#### Refactored Implementation (After)

**Option 1: Strategy Pattern with Node Routing**

```python
from abc import ABC, abstractmethod
from typing import Set, Dict, List

class NodeRoutingStrategy(ABC):
    """Strategy interface for node routing behavior"""
    
    @abstractmethod
    def get_branch_keys(
        self, 
        node: BaseNode, 
        input_data: NodeOutput,
        available_branches: Dict[str, List[FlowNode]]
    ) -> Set[str]:
        """Determine which branch keys to process."""
        pass

class ConditionalNodeRouting(NodeRoutingStrategy):
    """Routing strategy for conditional nodes"""
    
    def get_branch_keys(
        self, 
        node: BaseNode, 
        input_data: NodeOutput,
        available_branches: Dict[str, List[FlowNode]]
    ) -> Set[str]:
        if isinstance(input_data, ExecutionCompleted):
            # Broadcast to all branches
            return set(available_branches.keys())
        
        conditional = node  # Already verified as ConditionalNode
        if conditional.output:
            return {conditional.output}
        return set()

class DefaultNodeRouting(NodeRoutingStrategy):
    """Default routing strategy for non-conditional nodes"""
    
    def get_branch_keys(
        self, 
        node: BaseNode, 
        input_data: NodeOutput,
        available_branches: Dict[str, List[FlowNode]]
    ) -> Set[str]:
        if isinstance(input_data, ExecutionCompleted):
            return set(available_branches.keys())
        return {"default"}

# Add routing strategy to BaseNode
class BaseNode(BaseNodeProperty, BaseNodeMethod, ABC):
    def __init__(self, node_config: NodeConfig):
        # ... existing code ...
        self._routing_strategy = self._create_routing_strategy()
    
    def _create_routing_strategy(self) -> NodeRoutingStrategy:
        """Factory method - subclasses can override"""
        return DefaultNodeRouting()
    
    def get_branch_keys(
        self, 
        input_data: NodeOutput,
        available_branches: Dict[str, List[FlowNode]]
    ) -> Set[str]:
        """Get branch keys to process based on node type and input."""
        return self._routing_strategy.get_branch_keys(
            self, input_data, available_branches
        )
    
    def should_continue_after_execution(self) -> bool:
        """Determine if execution should continue to next nodes."""
        return True  # Default: continue

# Update ConditionalNode
class ConditionalNode(BlockingNode, ABC):
    def _create_routing_strategy(self) -> NodeRoutingStrategy:
        return ConditionalNodeRouting()
    
    def get_route(self) -> Optional[str]:
        """Get the selected route for conditional nodes."""
        return self.output if hasattr(self, 'output') else None

# Update NonBlockingNode
class NonBlockingNode(BaseNode, ABC):
    def should_continue_after_execution(self) -> bool:
        return False  # Don't continue to next nodes

# Refactored FlowRunner
class FlowRunner:
    async def _process_next_nodes(
        self, current_flow_node: FlowNode, input_data: NodeOutput
    ):
        """Recursively process downstream nodes."""
        next_nodes: Optional[Dict[str, List[FlowNode]]] = current_flow_node.next
        if not next_nodes:
            return

        instance = current_flow_node.instance
        
        # Use node's routing strategy - no type checking needed!
        keys_to_process = instance.get_branch_keys(input_data, next_nodes)
        
        # Collect nodes from selected branches
        nodes_to_run: List[FlowNode] = []
        for key in keys_to_process:
            if key in next_nodes:
                nodes_to_run.extend(next_nodes[key])

        # Execute selected nodes
        for next_flow_node in nodes_to_run:
            next_instance = next_flow_node.instance
            
            # ... execution code ...
            
            # Get route using polymorphism
            route = None
            if hasattr(next_instance, 'get_route'):
                route = next_instance.get_route()
            
            # Check if should continue using polymorphism
            if not next_instance.should_continue_after_execution():
                continue
            
            # Recurse
            await self._process_next_nodes(next_flow_node, data)
```

#### Benefits

- ✅ **Extensibility**: New node types can define their own routing without modifying FlowRunner
- ✅ **Single Responsibility**: Each node type handles its own routing logic
- ✅ **No Type Checking**: Eliminates isinstance() checks
- ✅ **Testability**: Can test routing strategies independently
- ✅ **Maintainability**: Changes to one node type don't affect others

---

### Violation 2: flow_utils.node_type() Function

**Location**: `core/Workflow/flow_utils.py:68-87`

#### Current Implementation (Before)

```python
def node_type(base_node_instance: BaseNode) -> Optional[str]:
    """
    Get the type name of a BaseNode instance.
    """
    if isinstance(base_node_instance, ProducerNode):  # ❌ Type check
        return ProducerNode.__name__
    elif isinstance(base_node_instance, NonBlockingNode):  # ❌ Type check
        return NonBlockingNode.__name__
    elif isinstance(base_node_instance, ConditionalNode):  # ❌ Type check
        return ConditionalNode.__name__
    elif isinstance(base_node_instance, BlockingNode):  # ❌ Type check
        return BlockingNode.__name__
    else:
        return None
```

#### Problem

The `node_type()` function uses an if-elif chain with `isinstance()` checks. This violates OCP because:

1. **Modification Required**: Adding a new node type requires modifying this function
2. **Order Dependency**: The order of checks matters (NonBlockingNode must come before BlockingNode)
3. **Tight Coupling**: Function is coupled to specific node type hierarchy
4. **Not Extensible**: Cannot add new node types without modifying this function

#### Solution Approach

1. **Polymorphism**: Add a `type_name` property to BaseNode
2. **Class Attribute**: Use class-level attribute for type name
3. **Method Override**: Subclasses define their own type name

#### Refactored Implementation (After)

```python
class BaseNode(BaseNodeProperty, BaseNodeMethod, ABC):
    """Base node class with type name support."""
    
    # Class-level type name - subclasses can override
    _type_name: Optional[str] = None
    
    def __init__(self, node_config: NodeConfig):
        self.node_config = node_config
        self.form = self.get_form()
        self._populate_form()
        self.execution_count = 0
    
    @property
    def type_name(self) -> str:
        """Get the type name of this node."""
        # Use class attribute or fall back to class name
        if self._type_name:
            return self._type_name
        
        # Determine from class hierarchy
        for cls in self.__class__.__mro__:
            if cls.__name__ in ['ProducerNode', 'BlockingNode', 'NonBlockingNode', 'ConditionalNode']:
                return cls.__name__
        
        return self.__class__.__name__

class ProducerNode(BaseNode, ABC):
    """Producer node type."""
    _type_name = "ProducerNode"

class BlockingNode(BaseNode, ABC):
    """Blocking node type."""
    _type_name = "BlockingNode"

class NonBlockingNode(BaseNode, ABC):
    """Non-blocking node type."""
    _type_name = "NonBlockingNode"

class ConditionalNode(BlockingNode, ABC):
    """Conditional node type."""
    _type_name = "ConditionalNode"

# Simplified utility function
def node_type(base_node_instance: BaseNode) -> Optional[str]:
    """
    Get the type name of a BaseNode instance.
    Uses polymorphism - no type checking needed!
    """
    return base_node_instance.type_name
```

#### Benefits

- ✅ **Extensibility**: New node types automatically work by setting `_type_name`
- ✅ **No Type Checking**: Eliminates isinstance() checks
- ✅ **Polymorphism**: Uses object-oriented principles
- ✅ **Maintainability**: Changes to node hierarchy don't require function modification

---

### Violation 3: BranchKeyNormalizer Hard-coded Branches

**Location**: `core/Workflow/flow_utils.py:33-50`

#### Current Implementation (Before)

```python
class BranchKeyNormalizer:
    @staticmethod
    def normalize_to_capitalized(branch_key: str) -> str:
        """
        Convert lowercase branch key to capitalized format for display.
        """
        if branch_key == "default":  # ❌ Hard-coded
            return None
        elif branch_key == "yes":  # ❌ Hard-coded
            return "Yes"
        elif branch_key == "no":  # ❌ Hard-coded
            return "No"
        else:
            return branch_key
```

#### Problem

The `normalize_to_capitalized()` method uses hard-coded if-elif statements. This violates OCP because:

1. **Modification Required**: Adding new branch types requires modifying this method
2. **Hard-coded Values**: Branch keys are hard-coded in the logic
3. **Not Extensible**: Cannot add custom branch types without code changes
4. **Tight Coupling**: Coupled to specific branch key values

#### Solution Approach

1. **Configuration Map**: Use a dictionary/mapping for branch key normalization
2. **Strategy Pattern**: Use strategy pattern for different normalization rules
3. **Registry Pattern**: Register branch types dynamically

#### Refactored Implementation (After)

```python
from typing import Dict, Optional, Callable

class BranchKeyNormalizer:
    """
    Utility class for normalizing branch keys.
    Supports extensible branch type registration.
    """
    
    # Registry for branch key mappings
    _branch_mappings: Dict[str, str] = {
        "default": None,  # None means use default label
        "yes": "Yes",
        "no": "No",
    }
    
    # Custom formatters for special cases
    _branch_formatters: Dict[str, Callable[[str], str]] = {}
    
    @classmethod
    def register_branch(cls, key: str, display_label: Optional[str] = None):
        """
        Register a new branch type.
        
        Args:
            key: The branch key (e.g., "maybe", "error")
            display_label: Optional display label (defaults to capitalized key)
        """
        if display_label is None:
            display_label = key.capitalize()
        cls._branch_mappings[key.lower()] = display_label
    
    @classmethod
    def register_formatter(cls, key: str, formatter: Callable[[str], str]):
        """
        Register a custom formatter for a branch key.
        
        Args:
            key: The branch key
            formatter: Function that takes key and returns formatted label
        """
        cls._branch_formatters[key.lower()] = formatter
    
    @staticmethod
    def normalize_to_lowercase(source_handle: any) -> str:
        """Normalize edge key from sourceHandle to lowercase format."""
        if source_handle:
            return source_handle.lower()
        return "default"
    
    @classmethod
    def normalize_to_capitalized(cls, branch_key: str) -> Optional[str]:
        """
        Convert lowercase branch key to capitalized format for display.
        Uses registry - extensible without modification!
        """
        key_lower = branch_key.lower()
        
        # Check for custom formatter first
        if key_lower in cls._branch_formatters:
            return cls._branch_formatters[key_lower](branch_key)
        
        # Check registry
        if key_lower in cls._branch_mappings:
            return cls._branch_mappings[key_lower]
        
        # Default: capitalize the key
        return branch_key.capitalize()
    
    @classmethod
    def normalize_for_display(cls, branch_key: str) -> str:
        """Normalize branch key for display purposes."""
        capitalized = cls.normalize_to_capitalized(branch_key)
        return capitalized or "default"

# Usage: Register new branch types without modifying code
BranchKeyNormalizer.register_branch("maybe", "Maybe")
BranchKeyNormalizer.register_branch("error", "Error")
BranchKeyNormalizer.register_branch("retry", "Retry")
```

#### Benefits

- ✅ **Extensibility**: New branch types can be registered without modifying code
- ✅ **Configuration-Based**: Branch mappings are data, not code
- ✅ **Flexibility**: Supports custom formatters for complex cases
- ✅ **Backward Compatible**: Existing code continues to work

---

### Violation 4: PoolExecutor Pool Type Handling

**Location**: `core/Workflow/execution/pool_executor.py:24-31`

#### Current Implementation (Before)

```python
class PoolExecutor:
    async def execute_in_pool(self, pool: PoolType, node: 'BaseNode', node_output: NodeOutput) -> NodeOutput:
        if pool == PoolType.ASYNC:  # ❌ Hard-coded check
            return await node.run(node_output)
        elif pool == PoolType.THREAD:  # ❌ Hard-coded check
            return await self._execute_thread(node, node_output)
        elif pool == PoolType.PROCESS:  # ❌ Hard-coded check
            return await self._execute_process(node, node_output)
        else:
            raise ValueError(f"Unknown execution pool: {pool}")
```

#### Problem

The `execute_in_pool()` method uses if-elif chain for pool types. This violates OCP because:

1. **Modification Required**: Adding new pool types requires modifying this method
2. **Hard-coded Logic**: Pool execution logic is hard-coded in if-elif chain
3. **Not Extensible**: Cannot add custom pool types without code changes
4. **Tight Coupling**: Coupled to specific PoolType enum values

#### Solution Approach

1. **Strategy Pattern**: Create strategy classes for each pool type
2. **Registry Pattern**: Register pool executors dynamically
3. **Factory Pattern**: Use factory to create appropriate executor

#### Refactored Implementation (After)

```python
from abc import ABC, abstractmethod
from typing import Dict
from enum import Enum

class PoolType(Enum):
    ASYNC = "async"
    THREAD = "thread"
    PROCESS = "process"

class PoolExecutorStrategy(ABC):
    """Strategy interface for pool execution."""
    
    @abstractmethod
    async def execute(self, node: 'BaseNode', node_output: NodeOutput) -> NodeOutput:
        """Execute node in this pool type."""
        pass

class AsyncPoolExecutor(PoolExecutorStrategy):
    """Async pool executor - runs directly in current event loop."""
    
    async def execute(self, node: 'BaseNode', node_output: NodeOutput) -> NodeOutput:
        return await node.run(node_output)

class ThreadPoolExecutor(PoolExecutorStrategy):
    """Thread pool executor."""
    
    def __init__(self, max_workers: int = 10):
        self._thread_pool: Optional[ThreadPoolExecutor] = None
        self._max_workers = max_workers
    
    async def execute(self, node: 'BaseNode', node_output: NodeOutput) -> NodeOutput:
        if self._thread_pool is None:
            self._thread_pool = ThreadPoolExecutor(max_workers=self._max_workers)
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._thread_pool, 
            PoolExecutor._run_in_thread, 
            node, 
            node_output
        )

class ProcessPoolExecutor(PoolExecutorStrategy):
    """Process pool executor."""
    
    def __init__(self, max_workers: int = 4):
        self._process_pool: Optional[ProcessPoolExecutor] = None
        self._max_workers = max_workers
    
    async def execute(self, node: 'BaseNode', node_output: NodeOutput) -> NodeOutput:
        if self._process_pool is None:
            self._process_pool = ProcessPoolExecutor(max_workers=self._max_workers)
        
        loop = asyncio.get_event_loop()
        serialized_node = pickle.dumps(node)
        serialized_data = pickle.dumps(node_output)
        result_bytes = await loop.run_in_executor(
            self._process_pool, 
            PoolExecutor._run_in_process, 
            serialized_node, 
            serialized_data
        )
        return pickle.loads(result_bytes)

class PoolExecutor:
    """
    Executes nodes in different execution pools.
    Uses strategy pattern - extensible without modification!
    """
    
    # Registry of pool executors
    _executors: Dict[PoolType, PoolExecutorStrategy] = {}
    
    def __init__(
        self, 
        max_workers_thread: int = 10, 
        max_workers_process: int = 4
    ):
        self._max_workers_thread = max_workers_thread
        self._max_workers_process = max_workers_process
        
        # Initialize default executors
        self._executors = {
            PoolType.ASYNC: AsyncPoolExecutor(),
            PoolType.THREAD: ThreadPoolExecutor(max_workers_thread),
            PoolType.PROCESS: ProcessPoolExecutor(max_workers_process),
        }
    
    @classmethod
    def register_executor(cls, pool_type: PoolType, executor: PoolExecutorStrategy):
        """Register a custom executor for a pool type."""
        cls._executors[pool_type] = executor
    
    async def execute_in_pool(
        self, 
        pool: PoolType, 
        node: 'BaseNode', 
        node_output: NodeOutput
    ) -> NodeOutput:
        """Execute node in specified pool using strategy pattern."""
        if pool not in self._executors:
            raise ValueError(f"Unknown execution pool: {pool}")
        
        executor = self._executors[pool]
        return await executor.execute(node, node_output)
    
    def shutdown(self, wait: bool = True) -> None:
        """Shutdown all pool executors."""
        for executor in self._executors.values():
            if hasattr(executor, 'shutdown'):
                executor.shutdown(wait=wait)
```

#### Benefits

- ✅ **Extensibility**: New pool types can be added by registering new strategies
- ✅ **Separation of Concerns**: Each pool type has its own executor class
- ✅ **Testability**: Can test each executor strategy independently
- ✅ **Flexibility**: Can swap or customize executors per pool type

---

### Violation 5: GoogleSheets Query Operators

**Location**: 
- `core/Node/Nodes/GoogleSheets/_shared/google_sheets_service.py:876-885`
- `core/Node/Nodes/GoogleSheets/GoogleSheetsGetRecordByQuery/_shared.py:103-107`

#### Current Implementation (Before)

```python
# In google_sheets_service.py
# Check condition based on operator
if operator == 'equals':  # ❌ Hard-coded
    if cell_value != query_value:
        all_match = False
        break
elif operator == 'contains':  # ❌ Hard-coded
    if query_value not in cell_value:
        all_match = False
        break
else:
    raise Exception(f"Unsupported operator: {operator}. Use 'equals' or 'contains'")

# In _shared.py validation
if operator not in ['equals', 'contains']:  # ❌ Hard-coded list
    raise Exception(
        f"Condition at index {idx} has invalid operator '{operator}'. "
        f"Must be 'equals' or 'contains'"
    )
```

#### Problem

Query operator handling uses hard-coded if-elif chains and validation lists. This violates OCP because:

1. **Modification Required**: Adding new operators requires modifying multiple files
2. **Code Duplication**: Operator logic appears in validation and execution
3. **Not Extensible**: Cannot add custom operators without code changes
4. **Tight Coupling**: Coupled to specific operator strings

#### Solution Approach

1. **Strategy Pattern**: Create operator strategy classes
2. **Registry Pattern**: Register operators dynamically
3. **Abstract Base Class**: Define operator interface

#### Refactored Implementation (After)

```python
from abc import ABC, abstractmethod
from typing import Dict, List

class QueryOperator(ABC):
    """Abstract base class for query operators."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the operator name (e.g., 'equals', 'contains')."""
        pass
    
    @abstractmethod
    def matches(self, cell_value: str, query_value: str, case_sensitive: bool = True) -> bool:
        """
        Check if cell value matches query value using this operator.
        
        Args:
            cell_value: The cell value to check
            query_value: The query value to match against
            case_sensitive: Whether comparison should be case-sensitive
            
        Returns:
            True if match, False otherwise
        """
        pass

class EqualsOperator(QueryOperator):
    """Equals operator - exact match."""
    
    @property
    def name(self) -> str:
        return "equals"
    
    def matches(self, cell_value: str, query_value: str, case_sensitive: bool = True) -> bool:
        if not case_sensitive:
            cell_value = cell_value.lower()
            query_value = query_value.lower()
        return cell_value == query_value

class ContainsOperator(QueryOperator):
    """Contains operator - substring match."""
    
    @property
    def name(self) -> str:
        return "contains"
    
    def matches(self, cell_value: str, query_value: str, case_sensitive: bool = True) -> bool:
        if not case_sensitive:
            cell_value = cell_value.lower()
            query_value = query_value.lower()
        return query_value in cell_value

class NotEqualsOperator(QueryOperator):
    """Not equals operator - inverse of equals."""
    
    @property
    def name(self) -> str:
        return "not_equals"
    
    def matches(self, cell_value: str, query_value: str, case_sensitive: bool = True) -> bool:
        equals_op = EqualsOperator()
        return not equals_op.matches(cell_value, query_value, case_sensitive)

class StartsWithOperator(QueryOperator):
    """Starts with operator."""
    
    @property
    def name(self) -> str:
        return "starts_with"
    
    def matches(self, cell_value: str, query_value: str, case_sensitive: bool = True) -> bool:
        if not case_sensitive:
            cell_value = cell_value.lower()
            query_value = query_value.lower()
        return cell_value.startswith(query_value)

class QueryOperatorRegistry:
    """Registry for query operators."""
    
    _operators: Dict[str, QueryOperator] = {}
    
    @classmethod
    def register(cls, operator: QueryOperator):
        """Register a query operator."""
        cls._operators[operator.name] = operator
    
    @classmethod
    def get(cls, name: str) -> QueryOperator:
        """Get operator by name."""
        if name not in cls._operators:
            raise ValueError(
                f"Unknown operator: {name}. "
                f"Available operators: {list(cls._operators.keys())}"
            )
        return cls._operators[name]
    
    @classmethod
    def get_all_names(cls) -> List[str]:
        """Get all registered operator names."""
        return list(cls._operators.keys())
    
    @classmethod
    def is_valid(cls, name: str) -> bool:
        """Check if operator name is valid."""
        return name in cls._operators

# Initialize registry with default operators
QueryOperatorRegistry.register(EqualsOperator())
QueryOperatorRegistry.register(ContainsOperator())
QueryOperatorRegistry.register(NotEqualsOperator())
QueryOperatorRegistry.register(StartsWithOperator())

# Refactored google_sheets_service.py
class GoogleSheetsService:
    def _match_row(self, row_values, query_conditions, headers):
        """Match row against query conditions using operator registry."""
        all_match = True
        
        for condition in query_conditions:
            column = condition['column']
            query_value = condition['value']
            operator_name = condition['operator']
            case_sensitive = condition.get('case_sensitive', True)
            
            # Get column index
            if column not in headers:
                all_match = False
                break
            
            col_index = headers[column]
            if col_index >= len(row_values):
                all_match = False
                break
            
            cell_value = str(row_values[col_index])
            
            # Apply case sensitivity
            if not case_sensitive:
                cell_value = cell_value.lower()
                query_value = query_value.lower()
            
            # Get operator from registry - extensible!
            operator = QueryOperatorRegistry.get(operator_name)
            
            # Use operator strategy - no if-elif needed!
            if not operator.matches(cell_value, query_value, case_sensitive):
                all_match = False
                break
        
        return all_match

# Refactored validation in _shared.py
def validate_query_conditions(query_conditions):
    """Validate query conditions using operator registry."""
    if not isinstance(query_conditions, list):
        raise Exception("Query conditions must be a JSON array")
    
    if len(query_conditions) == 0:
        raise Exception("Query conditions array cannot be empty")
    
    for idx, condition in enumerate(query_conditions):
        # ... other validations ...
        
        operator = condition.get('operator')
        if not QueryOperatorRegistry.is_valid(operator):  # Use registry!
            raise Exception(
                f"Condition at index {idx} has invalid operator '{operator}'. "
                f"Must be one of: {', '.join(QueryOperatorRegistry.get_all_names())}"
            )
```

#### Benefits

- ✅ **Extensibility**: New operators can be added by registering new classes
- ✅ **Single Responsibility**: Each operator handles its own logic
- ✅ **No Code Duplication**: Operator logic in one place
- ✅ **Testability**: Can test each operator independently
- ✅ **Type Safety**: Operator interface ensures consistency

---

### Violation 6: MetadataExtractor Port Generation

**Location**: `core/views/scanner/metadata_extractor.py:144-154`

#### Current Implementation (Before)

```python
def _get_ports(self, node_type: str) -> Dict[str, List[Dict]]:
    """
    Get input and output ports for a node type.
    """
    input_ports = [{"id": "default", "label": "In"}]
    output_ports = [{"id": "default", "label": "Out"}]
    
    if node_type == 'ProducerNode':  # ❌ Hard-coded check
        # Producer nodes have no input - they start the flow
        input_ports = []
    elif node_type == 'ConditionalNode':  # ❌ Hard-coded check
        # Conditional nodes have yes/no output branches
        output_ports = [
            {"id": "yes", "label": "Yes"},
            {"id": "no", "label": "No"}
        ]
    
    return {'input_ports': input_ports, 'output_ports': output_ports}
```

#### Problem

Port generation uses hard-coded if-elif checks. This violates OCP because:

1. **Modification Required**: Adding new node types requires modifying this method
2. **Tight Coupling**: Coupled to specific node type names
3. **Not Extensible**: Cannot add custom port configurations without code changes
4. **Duplication**: Port information exists in both node classes and this extractor

#### Solution Approach

1. **Polymorphism**: Nodes define their own ports
2. **Abstract Methods**: BaseNode defines port interface
3. **Default Implementation**: Provide sensible defaults

#### Refactored Implementation (After)

```python
# In BaseNode.py
class BaseNode(BaseNodeProperty, BaseNodeMethod, ABC):
    """Base node with port definition support."""
    
    @property
    def input_ports(self) -> List[Dict[str, str]]:
        """
        Get input ports for this node.
        Subclasses can override for custom ports.
        """
        return [{"id": "default", "label": "In"}]
    
    @property
    def output_ports(self) -> List[Dict[str, str]]:
        """
        Get output ports for this node.
        Subclasses can override for custom ports.
        """
        return [{"id": "default", "label": "Out"}]
    
    def get_ports(self) -> Dict[str, List[Dict[str, str]]]:
        """Get both input and output ports."""
        return {
            'input_ports': self.input_ports,
            'output_ports': self.output_ports
        }

class ProducerNode(BaseNode, ABC):
    """Producer node - no input ports."""
    
    @property
    def input_ports(self) -> List[Dict[str, str]]:
        """Producer nodes have no input - they start the flow."""
        return []

class ConditionalNode(BlockingNode, ABC):
    """Conditional node - yes/no output ports."""
    
    @property
    def output_ports(self) -> List[Dict[str, str]]:
        """Conditional nodes have yes/no output branches."""
        return [
            {"id": "yes", "label": "Yes"},
            {"id": "no", "label": "No"}
        ]

# Refactored MetadataExtractor
class MetadataExtractor:
    def _get_ports(self, node_class: Type[BaseNode]) -> Dict[str, List[Dict]]:
        """
        Get input and output ports for a node class.
        Uses polymorphism - no type checking needed!
        """
        # Create a temporary instance to get ports
        # (or use class-level properties if preferred)
        try:
            # Use class method or create minimal instance
            if hasattr(node_class, 'get_ports'):
                return node_class.get_ports()
            
            # Fallback: create instance (may require minimal config)
            # For metadata extraction, we can use a dummy config
            dummy_config = NodeConfig(id="dummy", type="dummy")
            instance = node_class(dummy_config)
            return instance.get_ports()
        except Exception:
            # Fallback to defaults if instantiation fails
            return {
                'input_ports': [{"id": "default", "label": "In"}],
                'output_ports': [{"id": "default", "label": "Out"}]
            }
    
    # Alternative: Use class-level properties
    def _get_ports_from_class(self, node_class: Type[BaseNode]) -> Dict[str, List[Dict]]:
        """Get ports using class-level properties."""
        input_ports = getattr(node_class, 'input_ports', [{"id": "default", "label": "In"}])
        output_ports = getattr(node_class, 'output_ports', [{"id": "default", "label": "Out"}])
        
        # Handle if they're properties that need instance
        if callable(input_ports):
            input_ports = [{"id": "default", "label": "In"}]  # Default
        if callable(output_ports):
            output_ports = [{"id": "default", "label": "Out"}]  # Default
        
        return {
            'input_ports': input_ports,
            'output_ports': output_ports
        }
```

#### Benefits

- ✅ **Extensibility**: New node types define their own ports
- ✅ **Single Source of Truth**: Port information in node classes
- ✅ **No Type Checking**: Uses polymorphism instead of if-elif
- ✅ **Maintainability**: Port changes only require updating node class

---

### Violation 7: FlowEngine Post-Processors List

**Location**: `core/Workflow/flow_engine.py:26`

#### Current Implementation (Before)

```python
class FlowEngine:
    """
    Central coordination system for flow execution.
    """

    _post_processors: List[Type[PostProcessor]] = [QueueMapper, NodeValidator]  # ❌ Hard-coded

    def load_workflow(self, workflow_json: Dict[str, Any]):
        self.flow_builder.load_workflow(workflow_json)

        for processor_class in self._post_processors:  # ❌ Uses hard-coded list
            processor = processor_class(self.flow_graph)
            processor.execute()
```

#### Problem

Post-processors are hard-coded in a class variable. This violates OCP because:

1. **Modification Required**: Adding new post-processors requires modifying FlowEngine
2. **Hard-coded List**: Processor list is hard-coded in class definition
3. **Not Extensible**: Cannot add custom processors without code changes
4. **Tight Coupling**: FlowEngine is coupled to specific processor classes

#### Solution Approach

1. **Registry Pattern**: Register post-processors dynamically
2. **Plugin System**: Use plugin system for processors
3. **Dependency Injection**: Inject processor list via constructor

#### Refactored Implementation (After)

```python
from typing import List, Type, Dict
from abc import ABC

class PostProcessorRegistry:
    """Registry for post-processors."""
    
    _processors: List[Type[PostProcessor]] = []
    _processor_metadata: Dict[Type[PostProcessor], Dict] = {}
    
    @classmethod
    def register(
        cls, 
        processor_class: Type[PostProcessor],
        priority: int = 100,
        enabled: bool = True
    ):
        """
        Register a post-processor.
        
        Args:
            processor_class: The post-processor class
            priority: Execution priority (lower = earlier)
            enabled: Whether processor is enabled
        """
        cls._processors.append(processor_class)
        cls._processor_metadata[processor_class] = {
            'priority': priority,
            'enabled': enabled
        }
        # Sort by priority
        cls._processors.sort(key=lambda p: cls._processor_metadata[p]['priority'])
    
    @classmethod
    def unregister(cls, processor_class: Type[PostProcessor]):
        """Unregister a post-processor."""
        if processor_class in cls._processors:
            cls._processors.remove(processor_class)
            del cls._processor_metadata[processor_class]
    
    @classmethod
    def get_all(cls) -> List[Type[PostProcessor]]:
        """Get all registered processors, sorted by priority."""
        return [
            p for p in cls._processors 
            if cls._processor_metadata[p]['enabled']
        ]
    
    @classmethod
    def clear(cls):
        """Clear all registered processors."""
        cls._processors.clear()
        cls._processor_metadata.clear()

# Register default processors
PostProcessorRegistry.register(QueueMapper, priority=10)
PostProcessorRegistry.register(NodeValidator, priority=20)

class FlowEngine:
    """
    Central coordination system for flow execution.
    """

    def __init__(
        self, 
        workflow_id: Optional[str] = None,
        post_processors: Optional[List[Type[PostProcessor]]] = None
    ):
        self.workflow_id = workflow_id
        # Use injected processors or registry
        self._post_processors = post_processors or PostProcessorRegistry.get_all()
        # ... rest of initialization ...

    def load_workflow(self, workflow_json: Dict[str, Any]):
        self.flow_builder.load_workflow(workflow_json)

        # Use registered processors - extensible!
        for processor_class in self._post_processors:
            processor = processor_class(self.flow_graph)
            processor.execute()

# Usage: Register new processors without modifying FlowEngine
class CustomPostProcessor(PostProcessor):
    def execute(self) -> None:
        # Custom processing logic
        pass

# Register new processor - no code modification needed!
PostProcessorRegistry.register(CustomPostProcessor, priority=30)
```

#### Benefits

- ✅ **Extensibility**: New processors can be registered without modifying FlowEngine
- ✅ **Configuration**: Processor priority and enablement can be configured
- ✅ **Flexibility**: Can use different processor sets per workflow
- ✅ **Testability**: Can register test processors for testing

---

### Violation 8: StringIterator Separator Handling

**Location**: `core/Node/Nodes/Data/StringIterator/node.py:40-46`

#### Current Implementation (Before)

```python
async def setup(self):
    """
    Parse the data from the form configuration during setup.
    """
    form_data = self.node_config.data.form or {}
    raw_data = form_data.get("data_content", "")
    separator_type = form_data.get("separator_type", "newline")
    custom_separator = form_data.get("custom_separator", "")

    # Determine separator
    if separator_type == "newline":  # ❌ Hard-coded
        delimiter = "\n"
    elif separator_type == "comma":  # ❌ Hard-coded
        delimiter = ","
    elif separator_type == "custom" and custom_separator:  # ❌ Hard-coded
        delimiter = custom_separator
    else:
        delimiter = "\n" # Fallback
```

#### Problem

Separator handling uses hard-coded if-elif chain. This violates OCP because:

1. **Modification Required**: Adding new separator types requires modifying this method
2. **Hard-coded Values**: Separator mappings are hard-coded
3. **Not Extensible**: Cannot add custom separators without code changes
4. **Tight Coupling**: Coupled to specific separator type strings

#### Solution Approach

1. **Strategy Pattern**: Create separator strategy classes
2. **Registry Pattern**: Register separators dynamically
3. **Factory Pattern**: Use factory to create separators

#### Refactored Implementation (After)

```python
from abc import ABC, abstractmethod
from typing import Dict, Optional

class SeparatorStrategy(ABC):
    """Strategy interface for separators."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get separator type name."""
        pass
    
    @abstractmethod
    def get_delimiter(self, config: Dict) -> str:
        """
        Get delimiter string for this separator type.
        
        Args:
            config: Configuration dict with separator settings
            
        Returns:
            Delimiter string
        """
        pass

class NewlineSeparator(SeparatorStrategy):
    """Newline separator strategy."""
    
    @property
    def name(self) -> str:
        return "newline"
    
    def get_delimiter(self, config: Dict) -> str:
        return "\n"

class CommaSeparator(SeparatorStrategy):
    """Comma separator strategy."""
    
    @property
    def name(self) -> str:
        return "comma"
    
    def get_delimiter(self, config: Dict) -> str:
        return ","

class CustomSeparator(SeparatorStrategy):
    """Custom separator strategy."""
    
    @property
    def name(self) -> str:
        return "custom"
    
    def get_delimiter(self, config: Dict) -> str:
        custom_separator = config.get("custom_separator", "")
        if not custom_separator:
            return "\n"  # Fallback
        return custom_separator

class TabSeparator(SeparatorStrategy):
    """Tab separator strategy."""
    
    @property
    def name(self) -> str:
        return "tab"
    
    def get_delimiter(self, config: Dict) -> str:
        return "\t"

class SeparatorRegistry:
    """Registry for separator strategies."""
    
    _separators: Dict[str, SeparatorStrategy] = {}
    
    @classmethod
    def register(cls, separator: SeparatorStrategy):
        """Register a separator strategy."""
        cls._separators[separator.name] = separator
    
    @classmethod
    def get(cls, name: str) -> SeparatorStrategy:
        """Get separator by name."""
        if name not in cls._separators:
            # Fallback to newline
            return cls._separators.get("newline", NewlineSeparator())
        return cls._separators[name]
    
    @classmethod
    def get_delimiter(cls, separator_type: str, config: Dict) -> str:
        """Get delimiter for separator type."""
        separator = cls.get(separator_type)
        return separator.get_delimiter(config)

# Register default separators
SeparatorRegistry.register(NewlineSeparator())
SeparatorRegistry.register(CommaSeparator())
SeparatorRegistry.register(CustomSeparator())
SeparatorRegistry.register(TabSeparator())

# Refactored StringIterator
class StringIterator(ProducerNode):
    async def setup(self):
        """
        Parse the data from the form configuration during setup.
        Uses separator registry - extensible!
        """
        form_data = self.node_config.data.form or {}
        raw_data = form_data.get("data_content", "")
        separator_type = form_data.get("separator_type", "newline")
        
        # Get delimiter from registry - no if-elif needed!
        delimiter = SeparatorRegistry.get_delimiter(separator_type, form_data)
        
        if not raw_data:
            self.items = []
        else:
            self.items = [item.strip() for item in raw_data.split(delimiter) if item.strip()]
        
        self.current_index = 0
        logger.info("Initialized StringIterator", item_count=len(self.items))

# Usage: Register new separator without modifying StringIterator
class SemicolonSeparator(SeparatorStrategy):
    @property
    def name(self) -> str:
        return "semicolon"
    
    def get_delimiter(self, config: Dict) -> str:
        return ";"

SeparatorRegistry.register(SemicolonSeparator())
```

#### Benefits

- ✅ **Extensibility**: New separators can be registered without modifying StringIterator
- ✅ **Single Responsibility**: Each separator handles its own logic
- ✅ **Testability**: Can test each separator independently
- ✅ **Flexibility**: Can add complex separators (e.g., regex, multi-character)

---

## Implementation Guidelines

### Step-by-Step Refactoring Process

1. **Identify Violations**
   - Look for if-elif chains that check types or values
   - Find hard-coded lists or mappings
   - Identify places where adding features requires code modification

2. **Choose Appropriate Pattern**
   - **Strategy Pattern**: When behavior varies by type
   - **Registry Pattern**: When items need to be registered dynamically
   - **Polymorphism**: When objects should handle their own behavior
   - **Factory Pattern**: When object creation logic varies

3. **Define Abstractions**
   - Create interfaces/protocols for strategies
   - Define base classes with abstract methods
   - Establish contracts for extensibility

4. **Implement Strategies**
   - Create concrete strategy implementations
   - Move logic from if-elif chains to strategy classes
   - Ensure each strategy is independently testable

5. **Create Registry (if needed)**
   - Implement registry for dynamic registration
   - Register default implementations
   - Provide registration API

6. **Refactor Existing Code**
   - Replace if-elif chains with strategy calls
   - Use registry to get implementations
   - Leverage polymorphism where possible

7. **Update Tests**
   - Test each strategy independently
   - Test registry registration
   - Test extensibility (adding new strategies)

### Common Patterns to Use

#### 1. Strategy Pattern

Use when behavior varies by type or configuration:

```python
from abc import ABC, abstractmethod

class Strategy(ABC):
    @abstractmethod
    def execute(self, data): pass

class StrategyA(Strategy):
    def execute(self, data):
        # Implementation A
        pass

class StrategyB(Strategy):
    def execute(self, data):
        # Implementation B
        pass

class Context:
    def __init__(self, strategy: Strategy):
        self._strategy = strategy
    
    def do_work(self, data):
        return self._strategy.execute(data)
```

#### 2. Registry Pattern

Use when items need to be registered dynamically:

```python
class Registry:
    _items: Dict[str, Type] = {}
    
    @classmethod
    def register(cls, name: str, item: Type):
        cls._items[name] = item
    
    @classmethod
    def get(cls, name: str) -> Type:
        return cls._items.get(name)
    
    @classmethod
    def get_all(cls) -> List[Type]:
        return list(cls._items.values())
```

#### 3. Polymorphism

Use when objects should handle their own behavior:

```python
class BaseClass(ABC):
    @abstractmethod
    def handle(self, data): pass

class SubClassA(BaseClass):
    def handle(self, data):
        # A-specific logic
        pass

class SubClassB(BaseClass):
    def handle(self, data):
        # B-specific logic
        pass

# Usage - no type checking needed!
def process(obj: BaseClass, data):
    return obj.handle(data)  # Polymorphism!
```

### Testing Considerations

**Before Refactoring:**
```python
# Hard to test - behavior is in if-elif chain
def test_node_type():
    node = SomeNode(config)
    result = node_type(node)  # Uses if-elif internally
    assert result == "BlockingNode"
```

**After Refactoring:**
```python
# Easy to test - behavior is in node class
def test_node_type():
    node = SomeNode(config)
    result = node.type_name  # Uses polymorphism
    assert result == "BlockingNode"

# Can test strategies independently
def test_equals_operator():
    op = EqualsOperator()
    assert op.matches("test", "test")
    assert not op.matches("test", "other")
```

### Migration Strategy

1. **Phase 1: Add Abstractions (Non-Breaking)**
   - Define interfaces/abstract classes
   - Create strategy classes
   - Keep existing code unchanged

2. **Phase 2: Implement Strategies**
   - Move logic from if-elif to strategies
   - Create registry if needed
   - Register default implementations

3. **Phase 3: Refactor Gradually**
   - Update one violation at a time
   - Maintain backward compatibility
   - Add tests for new code

4. **Phase 4: Remove Old Code**
   - Remove if-elif chains
   - Clean up hard-coded lists
   - Update documentation

### Common Anti-Patterns to Avoid

1. **❌ Type Checking with isinstance()**
   ```python
   # Bad
   if isinstance(obj, TypeA):
       # handle TypeA
   elif isinstance(obj, TypeB):
       # handle TypeB
   ```
   
   **✅ Use Polymorphism Instead:**
   ```python
   # Good
   obj.handle()  # Each type handles itself
   ```

2. **❌ Hard-coded if-elif Chains**
   ```python
   # Bad
   if value == "option1":
       # handle option1
   elif value == "option2":
       # handle option2
   ```
   
   **✅ Use Strategy Pattern:**
   ```python
   # Good
   strategy = StrategyRegistry.get(value)
   strategy.execute()
   ```

3. **❌ Hard-coded Lists**
   ```python
   # Bad
   valid_options = ["option1", "option2", "option3"]
   ```
   
   **✅ Use Registry:**
   ```python
   # Good
   valid_options = Registry.get_all_names()
   ```

4. **❌ Modifying Existing Classes for New Features**
   ```python
   # Bad
   class Processor:
       def process(self, data):
           if data.type == "new_type":  # Added for new feature
               # new logic
   ```
   
   **✅ Extend Instead:**
   ```python
   # Good
   class NewTypeProcessor(Processor):
       def process(self, data):
           # new logic
   ```

---

## Priority Ranking

### High Priority (Fix First)

1. **FlowRunner Node Type Handling** ⭐⭐⭐
   - **Impact**: High - Core execution component, affects all workflows
   - **Complexity**: High - Requires significant refactoring
   - **Benefits**: Enables new node types without modifying FlowRunner

2. **flow_utils.node_type() Function** ⭐⭐⭐
   - **Impact**: High - Used throughout codebase for node type identification
   - **Complexity**: Low - Simple property addition
   - **Benefits**: Cleaner code, better extensibility

3. **PoolExecutor Pool Type Handling** ⭐⭐⭐
   - **Impact**: High - Core execution infrastructure
   - **Complexity**: Medium - Requires strategy pattern implementation
   - **Benefits**: Enables custom pool types, better testability

### Medium Priority

4. **GoogleSheets Query Operators** ⭐⭐
   - **Impact**: Medium - Affects GoogleSheets node functionality
   - **Complexity**: Medium - Requires operator strategy classes
   - **Benefits**: Easy to add new operators, better code organization

5. **FlowEngine Post-Processors List** ⭐⭐
   - **Impact**: Medium - Affects workflow post-processing
   - **Complexity**: Low - Simple registry pattern
   - **Benefits**: Plugin-like extensibility

6. **MetadataExtractor Port Generation** ⭐⭐
   - **Impact**: Medium - Affects node metadata scanning
   - **Complexity**: Low - Move to node classes
   - **Benefits**: Single source of truth for ports

### Low Priority (Can Wait)

7. **BranchKeyNormalizer Hard-coded Branches** ⭐
   - **Impact**: Low - Affects display formatting only
   - **Complexity**: Low - Simple registry
   - **Benefits**: Extensible branch types

8. **StringIterator Separator Handling** ⭐
   - **Impact**: Low - Specific to one node
   - **Complexity**: Low - Strategy pattern
   - **Benefits**: Extensible separators

---

## Developer Checklist

Use this checklist when refactoring code to follow OCP:

### Before Refactoring

- [ ] Identify if-elif chains that check types or values
- [ ] Find hard-coded lists or mappings
- [ ] Determine if adding features requires code modification
- [ ] Review existing tests to understand current behavior
- [ ] Identify which pattern (Strategy, Registry, Polymorphism) fits best

### During Refactoring

- [ ] Define abstractions (interfaces/abstract classes)
- [ ] Create strategy classes or use polymorphism
- [ ] Implement registry if needed
- [ ] Register default implementations
- [ ] Replace if-elif chains with strategy calls
- [ ] Update existing code to use new patterns
- [ ] Write unit tests for strategies/implementations

### After Refactoring

- [ ] Verify existing tests still pass
- [ ] Add tests for new strategies/implementations
- [ ] Test extensibility (adding new items without code changes)
- [ ] Update documentation
- [ ] Check for any remaining if-elif chains
- [ ] Review code for other OCP violations

### Verification Questions

- [ ] Can I add new functionality without modifying existing code?
- [ ] Are there any if-elif chains checking types or values?
- [ ] Are hard-coded lists replaced with registries?
- [ ] Do objects handle their own behavior (polymorphism)?
- [ ] Can new strategies be added by registration only?
- [ ] Is the code open for extension but closed for modification?

### Code Review Checklist

When reviewing code for OCP compliance:

- [ ] No if-elif chains for type/value checking
- [ ] No hard-coded lists that need extension
- [ ] Strategies/patterns used for varying behavior
- [ ] Registry pattern for dynamic registration
- [ ] Polymorphism leveraged where appropriate
- [ ] New features can be added without modifying existing code

### Red Flags (Indicators of OCP Violations)

Watch out for these patterns that violate OCP:

1. **Type Checking Chains**
   ```python
   if isinstance(obj, TypeA): ...
   elif isinstance(obj, TypeB): ...
   ```

2. **Value Checking Chains**
   ```python
   if value == "option1": ...
   elif value == "option2": ...
   ```

3. **Hard-coded Lists**
   ```python
   valid_options = ["a", "b", "c"]  # Adding "d" requires code change
   ```

4. **Modification for Extension**
   ```python
   # Adding new feature requires modifying this method
   def process(self, data):
       if data.type == "new_type":  # New code added here
           ...
   ```

---

## Summary

This document identified **8 major Open/Closed Principle violations** in the codebase:

1. FlowRunner uses isinstance() checks for node type handling
2. flow_utils.node_type() uses if-elif chain for type determination
3. BranchKeyNormalizer has hard-coded branch mappings
4. PoolExecutor uses if-elif for pool type handling
5. GoogleSheets query operators use hard-coded if-elif chains
6. MetadataExtractor uses if-elif for port generation
7. FlowEngine has hard-coded post-processor list
8. StringIterator uses if-elif for separator handling

Each violation has been documented with:
- Current problematic code
- Explanation of the problem
- Refactored solution with code examples
- Benefits of the fix

**Next Steps:**
1. Review this document with the team
2. Prioritize violations based on impact
3. Start refactoring high-priority violations
4. Use Strategy, Registry, and Polymorphism patterns
5. Update this document as violations are fixed
6. Use the checklist when writing new code

Remember: **Open/Closed Principle is about being open for extension but closed for modification. Use patterns like Strategy, Registry, and Polymorphism to achieve this.**

---

## References

- [SOLID Principles - Open/Closed Principle](https://en.wikipedia.org/wiki/Open%E2%80%93closed_principle)
- [Strategy Pattern](https://en.wikipedia.org/wiki/Strategy_pattern)
- [Registry Pattern](https://martinfowler.com/eaaCatalog/registry.html)
- Related Documentation:
  - [Dependency-Inversion-Violations.md](Dependency-Inversion-Violations.md)
  - [02-Workflow-Engine.md](02-Workflow-Engine.md)
  - [04-Node-System.md](04-Node-System.md)

