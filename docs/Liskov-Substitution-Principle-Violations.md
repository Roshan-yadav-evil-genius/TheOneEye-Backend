# Liskov Substitution Principle Violations

## Table of Contents

1. [Introduction](#introduction)
2. [Violations Catalog](#violations-catalog)
   - [Violation 1: cleanup() Method Signature Mismatch](#violation-1-cleanup-method-signature-mismatch)
   - [Violation 2: __init__ Parameter Name Inconsistency](#violation-2-__init__-parameter-name-inconsistency)
   - [Violation 3: input_ports Property Contract Violation](#violation-3-input_ports-property-contract-violation)
   - [Violation 4: get_form() Return Type Narrowing](#violation-4-get_form-return-type-narrowing)
   - [Violation 5: ConditionalNode Additional State Requirements](#violation-5-conditionalnode-additional-state-requirements)
3. [Implementation Guidelines](#implementation-guidelines)
4. [Priority Ranking](#priority-ranking)
5. [Developer Checklist](#developer-checklist)

---

## Introduction

### What is Liskov Substitution Principle?

The **Liskov Substitution Principle (LSP)** is one of the SOLID principles of object-oriented design. It states:

> **Objects of a superclass should be replaceable with objects of its subclasses without breaking the application.**
> 
> **In other words: Subtypes must be substitutable for their base types without altering the correctness of the program.**

### Why It Matters

Violating LSP leads to:

- **Unexpected Behavior**: Code that works with base classes fails when using subclasses
- **Runtime Errors**: Type mismatches and attribute errors at runtime
- **Testing Difficulties**: Cannot reliably test base class behavior with subclass instances
- **Maintenance Burden**: Changes to subclasses can break code expecting base class behavior
- **Violation of Polymorphism**: Breaks the fundamental promise of inheritance

### How Violations Impact the Codebase

1. **Method Signature Mismatches**: Subclasses with different method signatures cannot be used where base classes are expected
2. **Contract Violations**: Subclasses that don't honor base class contracts break client code
3. **Precondition Strengthening**: Subclasses that require stronger preconditions than base classes
4. **Postcondition Weakening**: Subclasses that provide weaker guarantees than base classes
5. **Invariant Violations**: Subclasses that break base class invariants

---

## Violations Catalog

### Violation 1: cleanup() Method Signature Mismatch

**Location**: 
- `core/Node/Core/Node/Core/BaseNodeMethod.py:32`
- `core/Node/Core/Node/Core/BaseNode.py:219`
- `core/Node/Nodes/System/QueueWriter/node.py:28`
- `core/Node/Nodes/System/WebhookProducer/node.py:145`
- `core/Node/Nodes/Counter/CounterNode/node.py:175`

#### Current Implementation (Before)

```python
# BaseNodeMethod - Base class definition
class BaseNodeMethod(ABC):
    async def cleanup(self):  # ❌ No parameters
        """
        After the Loop Manager finishes the loop, the cleanup method is called.
        This method is used to clean up any necessary resources.
        Default implementation does nothing.
        """
        pass

# BaseNode - Overrides with different signature
class BaseNode(BaseNodeProperty, BaseNodeMethod, ABC):
    async def cleanup(self, node_data: Optional[NodeOutput] = None):  # ❌ Different signature
        """
        Cleanup the node resources.
        Called when the node receives an ExecutionCompleted input.
        
        Args:
            node_data: The sentinel signal data, if available.
        """
        pass

# QueueWriter - Uses the new signature
class QueueWriter(NonBlockingNode):
    async def cleanup(self, node_data: NodeOutput = None):  # ❌ Inconsistent default
        """
        Push Sentinel Pill to the queue during cleanup to propagate termination.
        """
        await self.execute(node_data)
        await self.data_store.close()

# WebhookProducerNode - Uses the new signature
class WebhookProducerNode(ProducerNode):
    async def cleanup(self, node_data: Optional[NodeOutput] = None):  # ✅ Matches BaseNode
        """Clean up subscription connection."""
        if self._subscriber_connection is not None:
            try:
                self._subscriber_connection.close()
                self._subscriber_connection = None
            except Exception as e:
                logger.warning("Error closing webhook subscription connection", ...)
```

#### Problem

The `cleanup()` method has **three different signatures** across the inheritance hierarchy:

1. **BaseNodeMethod**: `async def cleanup(self)` - No parameters
2. **BaseNode**: `async def cleanup(self, node_data: Optional[NodeOutput] = None)` - One optional parameter
3. **QueueWriter**: `async def cleanup(self, node_data: NodeOutput = None)` - Inconsistent default (should be Optional)

This violates LSP because:

1. **Signature Mismatch**: Code expecting `BaseNodeMethod.cleanup()` signature cannot call `BaseNode.cleanup(node_data)`
2. **Type Inconsistency**: `QueueWriter` uses `NodeOutput = None` instead of `Optional[NodeOutput] = None`
3. **Contract Violation**: Base class contract says "no parameters", but subclasses require parameters
4. **Polymorphism Broken**: Cannot substitute `BaseNodeMethod` instances with `BaseNode` instances in all contexts

#### Solution Approach

1. **Standardize Signature**: Make all `cleanup()` methods use the same signature
2. **Update Base Class**: Change `BaseNodeMethod.cleanup()` to match `BaseNode.cleanup()`
3. **Fix Type Annotations**: Use consistent `Optional[NodeOutput]` type hints
4. **Document Contract**: Clearly document that `node_data` is optional and may be None

#### Refactored Implementation (After)

```python
# BaseNodeMethod - Updated to match BaseNode signature
class BaseNodeMethod(ABC):
    async def cleanup(self, node_data: Optional[NodeOutput] = None):  # ✅ Matches BaseNode
        """
        After the Loop Manager finishes the loop, the cleanup method is called.
        This method is used to clean up any necessary resources.
        
        Args:
            node_data: Optional sentinel signal data, if available.
        
        Default implementation does nothing.
        """
        pass

# BaseNode - No change needed (already correct)
class BaseNode(BaseNodeProperty, BaseNodeMethod, ABC):
    async def cleanup(self, node_data: Optional[NodeOutput] = None):  # ✅ Consistent
        """
        Cleanup the node resources.
        Called when the node receives an ExecutionCompleted input.
        
        Args:
            node_data: The sentinel signal data, if available.
        """
        pass

# QueueWriter - Fixed type annotation
class QueueWriter(NonBlockingNode):
    async def cleanup(self, node_data: Optional[NodeOutput] = None):  # ✅ Fixed type
        """
        Push Sentinel Pill to the queue during cleanup to propagate termination.
        """
        await self.execute(node_data)
        await self.data_store.close()

# WebhookProducerNode - Already correct, no change needed
class WebhookProducerNode(ProducerNode):
    async def cleanup(self, node_data: Optional[NodeOutput] = None):  # ✅ Already correct
        """Clean up subscription connection."""
        if self._subscriber_connection is not None:
            try:
                self._subscriber_connection.close()
                self._subscriber_connection = None
            except Exception as e:
                logger.warning("Error closing webhook subscription connection", ...)
```

#### Benefits

- ✅ **LSP Compliance**: All subclasses can be substituted for base classes
- ✅ **Type Safety**: Consistent type annotations prevent runtime errors
- ✅ **Polymorphism**: Methods can be called polymorphically without signature mismatches
- ✅ **Backward Compatible**: Optional parameter maintains backward compatibility
- ✅ **Clear Contract**: Signature clearly indicates optional parameter

---

### Violation 2: __init__ Parameter Name Inconsistency

**Location**: 
- `core/Node/Core/Node/Core/BaseNode.py:42`
- `core/Node/Core/Node/Core/BaseNode.py:288` (ConditionalNode)
- `core/Node/Nodes/Counter/CounterNode/node.py:39`
- `core/Node/Nodes/System/WebhookProducer/node.py:39`

#### Current Implementation (Before)

```python
# BaseNode - Base class definition
class BaseNode(BaseNodeProperty, BaseNodeMethod, ABC):
    def __init__(self, node_config: NodeConfig):  # ✅ Uses 'node_config'
        self.node_config = node_config
        self.form = self.get_form()
        self._populate_form()
        self.execution_count = 0

# ConditionalNode - Uses different parameter name
class ConditionalNode(BlockingNode, ABC):
    def __init__(self, config: NodeConfig):  # ❌ Uses 'config' instead of 'node_config'
        super().__init__(config)  # ❌ Passes 'config' to super().__init__(node_config=...)
        self.output: Optional[str] = None
        self.test_result = False

# CounterNode - Uses different parameter name
class CounterNode(ProducerNode):
    def __init__(self, config):  # ❌ Uses 'config' instead of 'node_config'
        super().__init__(config)  # ❌ Passes 'config' to super().__init__(node_config=...)
        self.current_value: Optional[int] = None

# WebhookProducerNode - Uses different parameter name
class WebhookProducerNode(ProducerNode):
    def __init__(self, config):  # ❌ Uses 'config' instead of 'node_config'
        super().__init__(config)  # ❌ Passes 'config' to super().__init__(node_config=...)
        self._subscriber_connection = None
```

#### Problem

Subclasses use **different parameter names** (`config`) than the base class (`node_config`), which violates LSP because:

1. **Parameter Name Mismatch**: Base class expects `node_config`, but subclasses use `config`
2. **Positional Argument Issues**: When calling `super().__init__(config)`, Python uses positional arguments, which works but is inconsistent
3. **Keyword Argument Problems**: Code using keyword arguments like `BaseNode(node_config=...)` cannot be substituted with `CounterNode(config=...)`
4. **Type Hints Missing**: Some subclasses don't include type hints, making the contract unclear
5. **Inconsistent API**: Different parameter names across the hierarchy break the substitution principle

#### Solution Approach

1. **Standardize Parameter Name**: Use `node_config` consistently across all classes
2. **Add Type Hints**: Include proper type annotations in all `__init__` methods
3. **Use Keyword Arguments**: Explicitly use keyword arguments in `super().__init__()` calls
4. **Document Contract**: Clearly document the expected parameter name and type

#### Refactored Implementation (After)

```python
# BaseNode - No change needed (already correct)
class BaseNode(BaseNodeProperty, BaseNodeMethod, ABC):
    def __init__(self, node_config: NodeConfig):  # ✅ Standard parameter name
        self.node_config = node_config
        self.form = self.get_form()
        self._populate_form()
        self.execution_count = 0

# ConditionalNode - Fixed parameter name
class ConditionalNode(BlockingNode, ABC):
    def __init__(self, node_config: NodeConfig):  # ✅ Matches base class
        super().__init__(node_config=node_config)  # ✅ Explicit keyword argument
        self.output: Optional[str] = None
        self.test_result = False

# CounterNode - Fixed parameter name and type hint
class CounterNode(ProducerNode):
    def __init__(self, node_config: NodeConfig):  # ✅ Matches base class, added type hint
        super().__init__(node_config=node_config)  # ✅ Explicit keyword argument
        self.current_value: Optional[int] = None

# WebhookProducerNode - Fixed parameter name and type hint
class WebhookProducerNode(ProducerNode):
    def __init__(self, node_config: NodeConfig):  # ✅ Matches base class, added type hint
        super().__init__(node_config=node_config)  # ✅ Explicit keyword argument
        self._subscriber_connection = None
```

#### Benefits

- ✅ **LSP Compliance**: All subclasses can be substituted with consistent parameter names
- ✅ **Type Safety**: Type hints ensure correct types are passed
- ✅ **API Consistency**: Same parameter name across entire hierarchy
- ✅ **Keyword Arguments**: Explicit keyword arguments make calls clearer
- ✅ **Polymorphism**: Can create instances using same parameter name regardless of class

---

### Violation 3: input_ports Property Contract Violation

**Location**: 
- `core/Node/Core/Node/Core/BaseNodeProperty.py:66`
- `core/Node/Core/Node/Core/BaseNode.py:270` (ProducerNode)

#### Current Implementation (Before)

```python
# BaseNodeProperty - Base class definition
class BaseNodeProperty(ABC):
    @property
    def input_ports(self) -> list:
        """
        Define input ports for this node.
        Default is one 'default' input port.
        
        Returns:
            list: List of port definitions [{"id": "default", "label": "In"}]
        """
        return [{"id": "default", "label": "In"}]  # ✅ Returns list with one port

# ProducerNode - Overrides to return empty list
class ProducerNode(BaseNode, ABC):
    """
    Marks loop start. Called first each iteration.
    Starts and controls the loop. Controls timing and triggers downstream nodes.
    """
    
    @property
    def input_ports(self) -> list:
        """Producer nodes have no input ports - they start the flow."""
        return []  # ❌ Returns empty list, breaking contract
```

#### Problem

The `input_ports` property has **different return values** that violate the base class contract:

1. **Base Class Contract**: `BaseNodeProperty.input_ports` returns a list with at least one port `[{"id": "default", "label": "In"}]`
2. **Subclass Behavior**: `ProducerNode.input_ports` returns an empty list `[]`
3. **Contract Violation**: Code expecting at least one input port will fail with `ProducerNode`
4. **Type Safety**: While both return `list`, the semantic meaning is different (non-empty vs empty)
5. **Breaking Assumptions**: Client code that assumes `len(input_ports) > 0` will break

**Example of Breaking Code:**

```python
# This code works with BaseNode but breaks with ProducerNode
def process_node(node: BaseNode):
    # Assumes at least one input port exists
    first_input_port = node.input_ports[0]  # ❌ IndexError with ProducerNode
    port_id = first_input_port["id"]
    # ... process port
```

#### Solution Approach

1. **Document Contract Clearly**: Explicitly state that `input_ports` can return an empty list
2. **Use Type Hints**: Consider using `List[Dict[str, str]]` for better type safety
3. **Add Validation**: Client code should check for empty lists before accessing ports
4. **Alternative**: Create a separate property or method to check if node has input ports

#### Refactored Implementation (After)

**Option 1: Document and Accept Empty Lists (Recommended)**

```python
# BaseNodeProperty - Updated documentation
class BaseNodeProperty(ABC):
    @property
    def input_ports(self) -> List[Dict[str, str]]:  # ✅ Better type hint
        """
        Define input ports for this node.
        
        Returns:
            List[Dict[str, str]]: List of port definitions.
                Each port is a dict with "id" and "label" keys.
                Returns [{"id": "default", "label": "In"}] by default.
                Subclasses may return empty list [] if they have no input ports.
        """
        return [{"id": "default", "label": "In"}]

# ProducerNode - Documented behavior
class ProducerNode(BaseNode, ABC):
    """
    Marks loop start. Called first each iteration.
    Starts and controls the loop. Controls timing and triggers downstream nodes.
    
    Note: Producer nodes have no input ports as they start the workflow flow.
    """
    
    @property
    def input_ports(self) -> List[Dict[str, str]]:  # ✅ Consistent type hint
        """
        Producer nodes have no input ports - they start the flow.
        
        Returns:
            List[Dict[str, str]]: Empty list, as producer nodes don't receive input.
        """
        return []  # ✅ Documented and acceptable behavior
```

**Option 2: Add Helper Method (Alternative)**

```python
# BaseNodeProperty - Add helper method
class BaseNodeProperty(ABC):
    @property
    def input_ports(self) -> List[Dict[str, str]]:
        """Define input ports for this node."""
        return [{"id": "default", "label": "In"}]
    
    def has_input_ports(self) -> bool:  # ✅ Helper method
        """Check if node has input ports."""
        return len(self.input_ports) > 0

# ProducerNode - Override helper method
class ProducerNode(BaseNode, ABC):
    @property
    def input_ports(self) -> List[Dict[str, str]]:
        return []
    
    def has_input_ports(self) -> bool:  # ✅ Explicit override
        return False
```

**Updated Client Code:**

```python
# Safe code that works with all node types
def process_node(node: BaseNode):
    # Check for input ports before accessing
    if len(node.input_ports) > 0:  # ✅ Safe check
        first_input_port = node.input_ports[0]
        port_id = first_input_port["id"]
        # ... process port
    else:
        # Handle nodes without input ports (e.g., ProducerNode)
        logger.info("Node has no input ports", node_id=node.node_config.id)
```

#### Benefits

- ✅ **LSP Compliance**: Empty list is a valid list, maintaining substitutability
- ✅ **Type Safety**: Better type hints with `List[Dict[str, str]]`
- ✅ **Clear Documentation**: Explicitly documents that empty lists are valid
- ✅ **Defensive Programming**: Client code should check for empty lists
- ✅ **Semantic Correctness**: Empty list correctly represents "no input ports"

---

### Violation 4: get_form() Return Type Narrowing

**Location**: 
- `core/Node/Core/Node/Core/BaseNodeMethod.py:40`
- `core/Node/Nodes/Logical/IfCondition/node.py:21`

#### Current Implementation (Before)

```python
# BaseNodeMethod - Base class definition
class BaseNodeMethod(ABC):
    def get_form(self) -> Optional[BaseForm]:  # ✅ Returns Optional[BaseForm]
        """
        Get the associated form for this node.
        Default implementation returns None.

        Returns:
            BaseForm: An instance of the form corresponding to this node, or None.
        """
        return None

# IfCondition - Overrides with narrower return type
class IfCondition(ConditionalNode):
    def get_form(self) -> BaseForm:  # ❌ Returns BaseForm (not Optional)
        return IfConditionForm()  # Always returns a form, never None
```

#### Problem

The `get_form()` method has **inconsistent return types** across the hierarchy:

1. **Base Class Contract**: `BaseNodeMethod.get_form()` returns `Optional[BaseForm]` (can be None)
2. **Subclass Behavior**: `IfCondition.get_form()` returns `BaseForm` (never None)
3. **Type Narrowing**: While returning a non-None value is acceptable, the type hint suggests it can never be None
4. **Contract Violation**: Code expecting `Optional[BaseForm]` should handle None, but `IfCondition` guarantees it won't be None
5. **Inconsistent Behavior**: Some nodes return None, others always return a form

**Note**: This is actually a **covariant return type** which is generally acceptable in LSP, but the inconsistency can cause issues:

```python
# This code works but type checker may complain
def process_form(node: BaseNode):
    form = node.get_form()  # Type: Optional[BaseForm]
    if form is None:  # ✅ Must check for None
        return
    
    # Use form
    form.validate()  # ✅ Safe after None check

# But with IfCondition, the None check is unnecessary
def process_if_condition(node: IfCondition):
    form = node.get_form()  # Type: BaseForm (not Optional)
    # No None check needed, but inconsistent with base class contract
    form.validate()  # ✅ Always safe
```

#### Solution Approach

1. **Standardize Return Type**: Keep `Optional[BaseForm]` for consistency
2. **Document Behavior**: Clearly document which nodes always return forms
3. **Type Guards**: Use type guards or assertions for nodes that guarantee non-None forms
4. **Alternative**: Accept the narrowing as valid (covariant return types are allowed in Python)

#### Refactored Implementation (After)

**Option 1: Keep Optional Type (Recommended for Consistency)**

```python
# BaseNodeMethod - No change needed
class BaseNodeMethod(ABC):
    def get_form(self) -> Optional[BaseForm]:
        """
        Get the associated form for this node.
        Default implementation returns None.

        Returns:
            Optional[BaseForm]: An instance of the form corresponding to this node, or None.
        """
        return None

# IfCondition - Keep Optional type for consistency
class IfCondition(ConditionalNode):
    def get_form(self) -> Optional[BaseForm]:  # ✅ Consistent with base class
        """
        Get the form for this conditional node.
        
        Returns:
            Optional[BaseForm]: Always returns IfConditionForm instance (never None).
        """
        return IfConditionForm()  # ✅ Still returns Optional[BaseForm] type
```

**Option 2: Use Type Guard (Alternative)**

```python
# BaseNodeMethod - No change
class BaseNodeMethod(ABC):
    def get_form(self) -> Optional[BaseForm]:
        return None

# IfCondition - Use type guard pattern
class IfCondition(ConditionalNode):
    def get_form(self) -> Optional[BaseForm]:  # ✅ Keep Optional
        return IfConditionForm()
    
    def has_form(self) -> bool:  # ✅ Helper method
        """Check if node has a form (always True for IfCondition)."""
        return True

# Usage with type guard
def process_if_condition(node: IfCondition):
    if node.has_form():  # ✅ Type guard
        form = node.get_form()
        assert form is not None  # ✅ Type checker knows form is not None
        form.validate()
```

**Option 3: Accept Covariant Return (Also Valid)**

```python
# IfCondition - Narrower return type is acceptable (covariant)
class IfCondition(ConditionalNode):
    def get_form(self) -> BaseForm:  # ✅ Covariant return type (allowed in Python)
        """
        Get the form for this conditional node.
        
        Returns:
            BaseForm: Always returns IfConditionForm instance (never None).
        
        Note: This is a covariant return type. The subclass guarantees
        a non-None return value, which is more specific than the base class.
        """
        return IfConditionForm()
```

#### Benefits

- ✅ **LSP Compliance**: Covariant return types are acceptable in LSP
- ✅ **Type Safety**: Type hints accurately reflect actual behavior
- ✅ **Consistency**: Option 1 maintains consistent API across hierarchy
- ✅ **Flexibility**: Option 3 allows more specific return types when appropriate
- ✅ **Clear Contracts**: Documentation clarifies which nodes always return forms

**Recommendation**: Use **Option 1** (keep `Optional[BaseForm]`) for maximum consistency and to avoid breaking client code that checks for None.

---

### Violation 5: ConditionalNode Additional State Requirements

**Location**: 
- `core/Node/Core/Node/Core/BaseNode.py:283-303`

#### Current Implementation (Before)

```python
# BaseNode - Base class with minimal state
class BaseNode(BaseNodeProperty, BaseNodeMethod, ABC):
    def __init__(self, node_config: NodeConfig):
        self.node_config = node_config
        self.form = self.get_form()
        self._populate_form()
        self.execution_count = 0
        # ✅ Base class has: node_config, form, execution_count

# ConditionalNode - Adds additional required state
class ConditionalNode(BlockingNode, ABC):
    def __init__(self, config: NodeConfig):  # ❌ Different parameter name
        super().__init__(config)
        self.output: Optional[str] = None  # ❌ Additional required state
        self.test_result = False  # ❌ Additional required state
        # ❌ Subclass requires: output, test_result (in addition to base state)
```

#### Problem

`ConditionalNode` introduces **additional state requirements** that are not part of the base class contract:

1. **Additional Attributes**: `ConditionalNode` requires `output` and `test_result` attributes that don't exist in `BaseNode`
2. **State Dependencies**: Methods like `set_output()` depend on these additional attributes
3. **Contract Violation**: Code expecting only base class state may fail when accessing subclass-specific attributes
4. **Precondition Strengthening**: Subclass requires more state to be valid than base class
5. **Breaking Substitution**: Code that works with `BlockingNode` may not work with `ConditionalNode` if it assumes only base state

**Example of Potential Issues:**

```python
# Code that works with BlockingNode
def process_blocking_node(node: BlockingNode):
    # Only accesses base class attributes
    config = node.node_config  # ✅ Works
    form = node.form  # ✅ Works
    count = node.execution_count  # ✅ Works
    
    # But if node is ConditionalNode, additional state exists
    # Code doesn't know about output/test_result, but they're required

# Code that might break
def clone_node_state(node: BlockingNode):
    # Tries to copy all attributes
    state = {
        'node_config': node.node_config,
        'form': node.form,
        'execution_count': node.execution_count
    }
    # ❌ Missing output and test_result if node is ConditionalNode
    return state
```

#### Solution Approach

1. **Document Additional State**: Clearly document that `ConditionalNode` has additional state
2. **Use Properties with Defaults**: Make additional state optional with default values
3. **Lazy Initialization**: Initialize additional state only when needed
4. **Composition Over Inheritance**: Consider using composition for conditional behavior

#### Refactored Implementation (After)

**Option 1: Document and Accept Additional State (Recommended)**

```python
# BaseNode - No change needed
class BaseNode(BaseNodeProperty, BaseNodeMethod, ABC):
    def __init__(self, node_config: NodeConfig):
        self.node_config = node_config
        self.form = self.get_form()
        self._populate_form()
        self.execution_count = 0

# ConditionalNode - Documented additional state
class ConditionalNode(BlockingNode, ABC):
    """
    Base class for logical/conditional nodes that perform decision-making operations.
    Inherits from BlockingNode, ensuring logical operations complete before continuation.
    
    Additional State (beyond BaseNode):
    - output: The selected output branch ("yes" or "no")
    - test_result: Boolean result of the condition evaluation
    """
    def __init__(self, node_config: NodeConfig):  # ✅ Fixed parameter name
        super().__init__(node_config=node_config)
        # ✅ Documented additional state
        self.output: Optional[str] = None  # Set by set_output() method
        self.test_result = False  # Set by set_output() method

    @property
    def output_ports(self) -> List[Dict[str, str]]:
        """Conditional nodes have 'yes' and 'no' output branches."""
        return [
            {"id": "yes", "label": "Yes"},
            {"id": "no", "label": "No"}
        ]

    def set_output(self, output: bool):
        """
        Set the output branch based on condition result.
        
        Args:
            output: True for "yes" branch, False for "no" branch
        """
        self.test_result = output
        self.output = "yes" if output else "no"
```

**Option 2: Lazy Initialization (Alternative)**

```python
# ConditionalNode - Lazy initialization
class ConditionalNode(BlockingNode, ABC):
    def __init__(self, node_config: NodeConfig):
        super().__init__(node_config=node_config)
        self._output: Optional[str] = None  # Private, lazy-initialized
        self._test_result: Optional[bool] = None  # Private, lazy-initialized
    
    @property
    def output(self) -> Optional[str]:
        """Get output branch, initializing if needed."""
        if self._output is None:
            self._output = None  # Default to None until set_output() is called
        return self._output
    
    @property
    def test_result(self) -> bool:
        """Get test result, initializing if needed."""
        if self._test_result is None:
            self._test_result = False  # Default to False
        return self._test_result
    
    def set_output(self, output: bool):
        """Set the output branch."""
        self._test_result = output
        self._output = "yes" if output else "no"
```

**Option 3: Composition Pattern (Most Flexible)**

```python
# Separate conditional behavior
class ConditionalState:
    """Encapsulates conditional node state."""
    def __init__(self):
        self.output: Optional[str] = None
        self.test_result = False
    
    def set_output(self, output: bool):
        self.test_result = output
        self.output = "yes" if output else "no"

# ConditionalNode - Uses composition
class ConditionalNode(BlockingNode, ABC):
    def __init__(self, node_config: NodeConfig):
        super().__init__(node_config=node_config)
        self._conditional_state = ConditionalState()  # ✅ Composed state
    
    @property
    def output(self) -> Optional[str]:
        """Get output branch from conditional state."""
        return self._conditional_state.output
    
    @property
    def test_result(self) -> bool:
        """Get test result from conditional state."""
        return self._conditional_state.test_result
    
    def set_output(self, output: bool):
        """Set the output branch."""
        self._conditional_state.set_output(output)
```

#### Benefits

- ✅ **LSP Compliance**: Additional state is documented and doesn't break base class contract
- ✅ **Clear Documentation**: Explicitly states what additional state exists
- ✅ **Backward Compatible**: Base class behavior unchanged
- ✅ **Flexibility**: Options 2 and 3 provide more flexible initialization
- ✅ **Separation of Concerns**: Option 3 separates conditional logic from node logic

**Recommendation**: Use **Option 1** (document additional state) as it's the simplest and maintains current behavior while making the contract explicit.

---

## Implementation Guidelines

### Step-by-Step Refactoring Process

1. **Identify Violations**
   - Look for method signature mismatches between base and subclasses
   - Check for parameter name inconsistencies in `__init__` methods
   - Verify return type consistency (especially Optional types)
   - Review property contracts and their return values
   - Identify additional state requirements in subclasses

2. **Analyze Impact**
   - Determine which violations break existing code
   - Identify client code that depends on current behavior
   - Assess backward compatibility requirements
   - Check test coverage for affected classes

3. **Design Solution**
   - Choose refactoring approach (standardize vs. document)
   - Consider backward compatibility
   - Plan migration strategy
   - Document new contracts clearly

4. **Implement Changes**
   - Update base classes first (if needed)
   - Fix subclasses to match base class contracts
   - Update type hints for consistency
   - Add comprehensive documentation

5. **Update Client Code**
   - Fix code that depends on old behavior
   - Add defensive checks where needed
   - Update tests to reflect new contracts
   - Verify all tests pass

6. **Verify LSP Compliance**
   - Test that subclasses can be substituted for base classes
   - Verify polymorphic calls work correctly
   - Check that contracts are honored
   - Run integration tests

### Testing Considerations

**Before Refactoring:**
```python
# Test may pass but violates LSP
def test_cleanup():
    node = QueueWriter(node_config)
    # This works but signature doesn't match base class
    await node.cleanup(node_data)  # ✅ Works
    # But BaseNodeMethod.cleanup() has no parameters
    # Cannot substitute BaseNodeMethod instance
```

**After Refactoring:**
```python
# Test verifies LSP compliance
def test_cleanup_polymorphism():
    # Can use base class type
    nodes: List[BaseNodeMethod] = [
        QueueWriter(node_config),
        WebhookProducerNode(node_config),
        BaseNode(node_config)  # Any subclass
    ]
    
    for node in nodes:
        # All can be called with same signature
        await node.cleanup(node_data=None)  # ✅ LSP compliant
        assert node is not None
```

### Migration Strategy

1. **Phase 1: Document Current Behavior (Non-Breaking)**
   - Add documentation explaining current behavior
   - Document any LSP violations as known issues
   - Add type hints where missing
   - Create migration plan

2. **Phase 2: Fix High-Priority Violations**
   - Fix `cleanup()` method signature mismatch (high impact)
   - Standardize `__init__` parameter names (medium impact)
   - Update type hints for consistency

3. **Phase 3: Update Client Code**
   - Update code that creates nodes with inconsistent parameters
   - Fix code that assumes specific return types
   - Add defensive checks for optional values

4. **Phase 4: Verify and Test**
   - Run full test suite
   - Verify polymorphic behavior works
   - Check that all substitutions are valid
   - Update documentation

### Common Patterns to Use

1. **Consistent Method Signatures**
   ```python
   # Base class
   class BaseClass:
       def method(self, param: Optional[Type] = None) -> ReturnType:
           pass
   
   # Subclass - Must match signature
   class SubClass(BaseClass):
       def method(self, param: Optional[Type] = None) -> ReturnType:  # ✅ Same signature
           # Implementation
           pass
   ```

2. **Consistent Parameter Names**
   ```python
   # Base class
   class BaseClass:
       def __init__(self, base_param: Type):
           self.base_param = base_param
   
   # Subclass - Use same parameter name
   class SubClass(BaseClass):
       def __init__(self, base_param: Type):  # ✅ Same name
           super().__init__(base_param=base_param)  # ✅ Explicit keyword
   ```

3. **Covariant Return Types (When Appropriate)**
   ```python
   # Base class
   class BaseClass:
       def get_item(self) -> Optional[Item]:
           return None
   
   # Subclass - Can narrow return type (covariant)
   class SubClass(BaseClass):
       def get_item(self) -> Item:  # ✅ More specific (never None)
           return ConcreteItem()  # Always returns Item
   ```

4. **Documented Additional State**
   ```python
   class SubClass(BaseClass):
       """
       Extends BaseClass with additional state.
       
       Additional Attributes:
       - extra_attr: Additional attribute not in base class
       """
       def __init__(self, base_param: Type):
           super().__init__(base_param=base_param)
           self.extra_attr = None  # ✅ Documented additional state
   ```

---

## Priority Ranking

### High Priority (Fix First)

1. **cleanup() Method Signature Mismatch** ⭐⭐⭐
   - **Impact**: High - Affects all node cleanup operations
   - **Complexity**: Low - Simple signature standardization
   - **Benefits**: Enables polymorphic cleanup calls, fixes type safety issues
   - **Risk**: Low - Optional parameter maintains backward compatibility

2. **__init__ Parameter Name Inconsistency** ⭐⭐⭐
   - **Impact**: High - Affects all node instantiation
   - **Complexity**: Low - Simple parameter name standardization
   - **Benefits**: Consistent API, better type safety, prevents keyword argument issues
   - **Risk**: Medium - May require updating node creation code

### Medium Priority

3. **input_ports Property Contract Violation** ⭐⭐
   - **Impact**: Medium - Affects code that processes node ports
   - **Complexity**: Low - Documentation and defensive programming
   - **Benefits**: Clear contract, prevents IndexError exceptions
   - **Risk**: Low - Empty list is valid, just needs documentation

4. **get_form() Return Type Narrowing** ⭐⭐
   - **Impact**: Medium - Affects form handling code
   - **Complexity**: Low - Type hint consistency
   - **Benefits**: Consistent API, better type checking
   - **Risk**: Low - Covariant return types are acceptable

### Low Priority (Can Wait)

5. **ConditionalNode Additional State Requirements** ⭐
   - **Impact**: Low - Specific to conditional nodes
   - **Complexity**: Low - Documentation only
   - **Benefits**: Clear documentation of additional state
   - **Risk**: None - Additional state doesn't break base class contract

---

## Developer Checklist

Use this checklist when refactoring code to follow LSP:

### Before Refactoring

- [ ] Identify all method signatures in base classes
- [ ] Check for parameter name inconsistencies in `__init__` methods
- [ ] Review return types for consistency (especially Optional types)
- [ ] Identify properties that may return different values
- [ ] Check for additional state requirements in subclasses
- [ ] Review existing tests to understand current behavior
- [ ] Identify client code that depends on current behavior

### During Refactoring

- [ ] Standardize method signatures across inheritance hierarchy
- [ ] Use consistent parameter names in `__init__` methods
- [ ] Add proper type hints to all methods
- [ ] Document any additional state in subclasses
- [ ] Update base class documentation with clear contracts
- [ ] Write tests that verify polymorphic behavior
- [ ] Ensure backward compatibility where possible

### After Refactoring

- [ ] Update all client code to use new signatures
- [ ] Verify existing tests still pass
- [ ] Add new tests for polymorphic behavior
- [ ] Update documentation/examples
- [ ] Check for any remaining signature mismatches
- [ ] Verify type hints are consistent
- [ ] Review code for other LSP violations

### Verification Questions

- [ ] Can I substitute any subclass for its base class without breaking code?
- [ ] Do all methods have consistent signatures across the hierarchy?
- [ ] Are parameter names consistent in `__init__` methods?
- [ ] Do return types follow the contract (or are they properly covariant)?
- [ ] Are properties documented when they return different values?
- [ ] Is additional state in subclasses clearly documented?
- [ ] Can polymorphic calls work correctly with all subclasses?

### Code Review Checklist

When reviewing code for LSP compliance:

- [ ] Method signatures match between base and subclasses
- [ ] Parameter names are consistent in `__init__` methods
- [ ] Return types are consistent (or properly covariant)
- [ ] Properties honor base class contracts
- [ ] Additional state is documented
- [ ] Type hints are accurate and consistent
- [ ] Documentation clearly explains any deviations from base class

### Red Flags (LSP Violations)

Watch out for these patterns that indicate LSP violations:

- ❌ **Method signature changes**: Subclass method has different parameters than base class
- ❌ **Parameter name mismatches**: `__init__` uses different parameter names
- ❌ **Return type inconsistencies**: Subclass returns different type without proper covariance
- ❌ **Contract violations**: Subclass doesn't honor base class contract
- ❌ **Precondition strengthening**: Subclass requires stronger preconditions
- ❌ **Postcondition weakening**: Subclass provides weaker guarantees
- ❌ **Invariant breaking**: Subclass breaks base class invariants
- ❌ **Additional required state**: Subclass requires state not in base class (without documentation)

---

## References

- [SOLID Principles - Liskov Substitution Principle](https://en.wikipedia.org/wiki/Liskov_substitution_principle)
- [Python Type Hints (PEP 484)](https://www.python.org/dev/peps/pep-0484/)
- [Covariant Return Types in Python](https://docs.python.org/3/library/typing.html#typing.overload)
- Related Documentation:
  - [Dependency-Inversion-Violations.md](Dependency-Inversion-Violations.md)
  - [Open-Closed-Principle-Violations.md](Open-Closed-Principle-Violations.md)
  - [Interface-Segregation-Principle-Violations.md](Interface-Segregation-Principle-Violations.md)
  - [04-Node-System.md](04-Node-System.md)

---

## Summary

This document identified **5 major Liskov Substitution Principle violations** in the codebase:

1. **cleanup() Method Signature Mismatch**: Three different signatures across inheritance hierarchy
2. **__init__ Parameter Name Inconsistency**: Subclasses use `config` instead of `node_config`
3. **input_ports Property Contract Violation**: ProducerNode returns empty list vs. base class default
4. **get_form() Return Type Narrowing**: IfCondition returns `BaseForm` instead of `Optional[BaseForm]`
5. **ConditionalNode Additional State Requirements**: Additional state not documented in base class

Each violation has been documented with:
- Current problematic code
- Explanation of the LSP violation
- Refactored solution with code examples
- Benefits of the fix

**Next Steps:**
1. Review this document with the team
2. Prioritize violations based on impact (start with cleanup() and __init__)
3. Begin refactoring high-priority violations
4. Update this document as violations are fixed
5. Use the checklist when writing new code

Remember: **Liskov Substitution Principle ensures that subclasses can be used anywhere their base classes are expected without breaking the program.**
