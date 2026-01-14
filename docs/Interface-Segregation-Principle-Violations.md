# Interface Segregation Principle Violations

## Table of Contents

1. [Introduction](#introduction)
2. [Violations Catalog](#violations-catalog)
   - [Violation 1: BaseForm Forcing DependencyInjector Implementation](#violation-1-baseform-forcing-dependencyinjector-implementation)
   - [Violation 2: BaseNodeProperty Requiring All Metadata Methods](#violation-2-basenodeproperty-requiring-all-metadata-methods)
   - [Violation 3: BaseNodeMethod Lifecycle Methods](#violation-3-basenodemethod-lifecycle-methods)
   - [Violation 4: BaseManager Helper Methods](#violation-4-basemanager-helper-methods)
3. [Implementation Guidelines](#implementation-guidelines)
4. [Priority Ranking](#priority-ranking)
5. [Developer Checklist](#developer-checklist)

---

## Introduction

### What is Interface Segregation Principle?

The **Interface Segregation Principle (ISP)** is one of the SOLID principles of object-oriented design. It states:

> **Clients should not be forced to depend upon interfaces that they do not use.**

This means:
- **No Fat Interfaces**: Interfaces should be small and focused, not large and bloated
- **Client-Specific Interfaces**: Different clients should have different interfaces tailored to their needs
- **No Forced Implementation**: Classes should not be forced to implement methods they don't need

### Why It Matters

Violating ISP leads to:

- **Unnecessary Coupling**: Classes depend on methods they never use
- **Code Bloat**: Implementations must provide empty or default implementations for unused methods
- **Maintenance Burden**: Changes to unused interface methods affect all implementers
- **Confusion**: Developers must understand methods they don't need
- **Testing Overhead**: Must test or mock methods that aren't actually used

### How Violations Impact the Codebase

1. **Forced Empty Implementations**: Forms must implement dependency methods even when they don't need cascading fields
2. **Unused Method Overhead**: Nodes inherit lifecycle methods they may never use
3. **Interface Pollution**: Base classes expose methods that only some subclasses need
4. **Reduced Flexibility**: Cannot create lightweight implementations without inheriting unnecessary methods

---

## Violations Catalog

### Violation 1: BaseForm Forcing DependencyInjector Implementation

**Location**: `core/Node/Core/Form/Core/BaseForm.py:40`

#### Current Implementation (Before)

```python
class DependencyInjector(ABC):
    """Abstract mixin class that defines the interface for field dependency injection."""
    
    @abstractmethod
    def get_field_dependencies(self) -> Dict[str, List[str]]:
        """REQUIRED: Define field dependencies."""
        pass
    
    @abstractmethod
    def populate_field(
        self, 
        field_name: str, 
        parent_value: Any, 
        form_values: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, str]]:
        """REQUIRED: Populate choices for a dependent field based on parent value."""
        pass

class BaseForm(DependencyInjector, forms.Form, metaclass=FormABCMeta):
    """Base form class that provides cascading field dependency functionality."""
    
    def get_field_dependencies(self):
        """REQUIRED: Define which fields depend on which parent fields."""
        pass  # ❌ Empty implementation forced on all forms

    def populate_field(self, field_name, parent_value, form_values=None):
        """REQUIRED: Provide choices for dependent fields based on parent value."""
        return []  # ❌ Empty implementation forced on all forms
```

**Example Forms That Don't Need Dependencies:**

```python
# CounterForm - No cascading dependencies needed
class CounterForm(BaseForm):
    min_value = forms.IntegerField(required=True)
    max_value = forms.IntegerField(required=True)
    direction = forms.ChoiceField(choices=[...])
    step = forms.IntegerField(required=True)
    
    # ❌ Must implement these even though not needed:
    def get_field_dependencies(self):
        return {}  # Empty - not used
    
    def populate_field(self, field_name, parent_value, form_values=None):
        return []  # Empty - not used

# StaticDelayForm - No cascading dependencies needed
class StaticDelayForm(BaseForm):
    interval = forms.IntegerField(required=True)
    unit = forms.ChoiceField(choices=UNIT_CHOICES)
    
    # ❌ Must implement these even though not needed:
    def get_field_dependencies(self):
        return {}  # Empty - not used
    
    def populate_field(self, field_name, parent_value, form_values=None):
        return []  # Empty - not used
```

**Example Form That Actually Uses Dependencies:**

```python
# GoogleSheetsGetRecordByQueryForm - Actually needs dependencies
class GoogleSheetsGetRecordByQueryForm(BaseForm):
    google_account = forms.ChoiceField(...)
    spreadsheet = DynamicChoiceField(...)
    sheet = DynamicChoiceField(...)
    
    def get_field_dependencies(self):
        return {
            'google_account': ['spreadsheet'],
            'spreadsheet': ['sheet']
        }  # ✅ Actually uses dependencies
    
    async def populate_field(self, field_name, parent_value, form_values=None):
        if field_name == 'spreadsheet':
            return await populate_spreadsheet_choices(parent_value)
        elif field_name == 'sheet':
            return await populate_sheet_choices(parent_value, form_values)
        return []  # ✅ Actually uses dependencies
```

#### Problem

`BaseForm` inherits from `DependencyInjector`, which requires all forms to implement `get_field_dependencies()` and `populate_field()` even when they don't need cascading field dependencies. This violates ISP because:

1. **Forced Implementation**: All forms must implement dependency methods, even simple forms like `CounterForm` and `StaticDelayForm`
2. **Empty Implementations**: Forms without dependencies must provide empty implementations (`return {}` and `return []`)
3. **Unnecessary Coupling**: Forms are coupled to dependency injection functionality they don't use
4. **Code Pollution**: Every form class includes methods that are never called
5. **Maintenance Overhead**: Changes to `DependencyInjector` affect all forms, even those that don't use it

#### Solution Approach

1. **Separate Interfaces**: Create separate interfaces for forms with and without dependencies
2. **Optional Mixin**: Make `DependencyInjector` an optional mixin, not a base class requirement
3. **Composition Over Inheritance**: Use composition to add dependency handling only when needed
4. **Default Implementation**: Provide default implementations that can be overridden

#### Refactored Implementation (After)

**Option 1: Separate Base Classes**

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Tuple, Any

# Base form without dependencies
class BaseForm(forms.Form, metaclass=FormABCMeta):
    """
    Base form class for all forms.
    Provides core form functionality without dependency injection.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._incremental_data = {}
        # No dependency handler - only added if needed
    
    # ... core form methods (update_field, get_field_value, etc.) ...

# Optional mixin for dependency injection
class DependencyInjectorMixin(ABC):
    """
    Optional mixin for forms that need cascading field dependencies.
    Only inherit this if your form has dependent fields.
    """
    
    @abstractmethod
    def get_field_dependencies(self) -> Dict[str, List[str]]:
        """Define field dependencies."""
        pass
    
    @abstractmethod
    def populate_field(
        self, 
        field_name: str, 
        parent_value: Any, 
        form_values: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, str]]:
        """Populate choices for dependent fields."""
        pass

# Form with dependencies
class FormWithDependencies(BaseForm, DependencyInjectorMixin):
    """
    Base class for forms that need cascading field dependencies.
    Automatically initializes dependency handler.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize dependency handler only for forms that need it
        self._dependency_handler = DependencyHandler(self)
        self._dependency_handler.initialize_dependencies()

# Usage: Simple forms don't need dependency methods
class CounterForm(BaseForm):  # ✅ No dependency methods needed
    min_value = forms.IntegerField(required=True)
    max_value = forms.IntegerField(required=True)
    direction = forms.ChoiceField(choices=[...])
    step = forms.IntegerField(required=True)
    # No get_field_dependencies() or populate_field() needed!

# Usage: Forms with dependencies explicitly inherit from FormWithDependencies
class GoogleSheetsGetRecordByQueryForm(FormWithDependencies):  # ✅ Explicitly needs dependencies
    google_account = forms.ChoiceField(...)
    spreadsheet = DynamicChoiceField(...)
    sheet = DynamicChoiceField(...)
    
    def get_field_dependencies(self):
        return {
            'google_account': ['spreadsheet'],
            'spreadsheet': ['sheet']
        }
    
    async def populate_field(self, field_name, parent_value, form_values=None):
        if field_name == 'spreadsheet':
            return await populate_spreadsheet_choices(parent_value)
        elif field_name == 'sheet':
            return await populate_sheet_choices(parent_value, form_values)
        return []
```

**Option 2: Optional Dependency Handler (Composition)**

```python
class BaseForm(forms.Form, metaclass=FormABCMeta):
    """
    Base form class. Dependency injection is optional.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._incremental_data = {}
        self._dependency_handler: Optional[DependencyHandler] = None
    
    def _enable_dependencies(self):
        """Enable dependency injection for this form."""
        if self._dependency_handler is None:
            self._dependency_handler = DependencyHandler(self)
            self._dependency_handler.initialize_dependencies()
    
    def get_field_dependencies(self) -> Dict[str, List[str]]:
        """
        Get field dependencies. Override in subclasses that need dependencies.
        Returns empty dict by default.
        """
        return {}
    
    def populate_field(
        self, 
        field_name: str, 
        parent_value: Any, 
        form_values: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, str]]:
        """
        Populate dependent field choices. Override in subclasses that need dependencies.
        Returns empty list by default.
        """
        return []
    
    def update_field(self, field_name, value):
        """Update field and handle dependencies if enabled."""
        # ... update logic ...
        
        # Only handle dependencies if dependency handler is enabled
        if self._dependency_handler and value_changed:
            self._dependency_handler.handle_field_change(field_name, value)

# Usage: Simple forms - no dependency methods needed
class CounterForm(BaseForm):
    min_value = forms.IntegerField(required=True)
    max_value = forms.IntegerField(required=True)
    # No need to override get_field_dependencies() or populate_field()

# Usage: Forms with dependencies - override methods and enable handler
class GoogleSheetsGetRecordByQueryForm(BaseForm):
    google_account = forms.ChoiceField(...)
    spreadsheet = DynamicChoiceField(...)
    sheet = DynamicChoiceField(...)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._enable_dependencies()  # Enable dependency handling
    
    def get_field_dependencies(self):
        return {
            'google_account': ['spreadsheet'],
            'spreadsheet': ['sheet']
        }
    
    async def populate_field(self, field_name, parent_value, form_values=None):
        if field_name == 'spreadsheet':
            return await populate_spreadsheet_choices(parent_value)
        elif field_name == 'sheet':
            return await populate_sheet_choices(parent_value, form_values)
        return []
```

#### Benefits

- ✅ **No Forced Implementation**: Simple forms don't need to implement dependency methods
- ✅ **Clear Intent**: Forms that need dependencies explicitly inherit from `FormWithDependencies` or enable dependencies
- ✅ **Reduced Coupling**: Forms without dependencies aren't coupled to dependency injection
- ✅ **Cleaner Code**: No empty method implementations cluttering simple forms
- ✅ **Better Performance**: Dependency handler only initialized when needed
- ✅ **Easier Testing**: Simple forms have fewer methods to test

---

### Violation 2: BaseNodeProperty Requiring All Metadata Methods

**Location**: `core/Node/Core/Node/Core/BaseNodeProperty.py:6-85`

#### Current Implementation (Before)

```python
class BaseNodeProperty(ABC):
    """
    Abstract base class for node metadata properties.
    Subclasses must implement execution_pool and identifier.
    Other properties have default implementations for backward compatibility.
    """
    
    @property
    @abstractmethod
    def execution_pool(self) -> PoolType:
        """The preferred execution pool for this node."""
        pass
    
    @classmethod
    @abstractmethod
    def identifier(cls) -> str:
        """Return the node type identifier (kebab-case string)."""
        pass
    
    @property
    def label(self) -> str:
        """Get the display label for this node."""
        return self.__class__.__name__  # ❌ All nodes inherit this
    
    @property
    def description(self) -> str:
        """Get the description for this node."""
        return ""  # ❌ All nodes inherit this
    
    @property
    def icon(self) -> str:
        """Get the icon identifier for this node."""
        return ""  # ❌ All nodes inherit this
    
    @property
    def input_ports(self) -> list:
        """Define input ports for this node."""
        return [{"id": "default", "label": "In"}]  # ❌ All nodes inherit this
    
    @property
    def output_ports(self) -> list:
        """Define output ports for this node."""
        return [{"id": "default", "label": "Out"}]  # ❌ All nodes inherit this
```

**Example: Nodes That Don't Need All Properties**

```python
# QueueReader - Simple node, doesn't need label, description, icon
class QueueReader(ProducerNode):
    @classmethod
    def identifier(cls) -> str:
        return "queue-reader-dummy"
    
    @property
    def execution_pool(self) -> PoolType:
        return PoolType.ASYNC
    
    # ❌ Inherits label, description, icon, input_ports, output_ports
    # but doesn't use or override them
```

**Example: Nodes That Override Properties**

```python
# CounterNode - Overrides some properties but not all
class CounterNode(ProducerNode):
    @classmethod
    def identifier(cls) -> str:
        return "counter"
    
    @property
    def execution_pool(self) -> PoolType:
        return PoolType.ASYNC
    
    @property
    def label(self) -> str:
        return "Counter"  # ✅ Overrides label
    
    @property
    def description(self) -> str:
        return "Iterates between min and max values"  # ✅ Overrides description
    
    @property
    def icon(self) -> str:
        return "counter"  # ✅ Overrides icon
    
    # ❌ Still inherits input_ports and output_ports even if not customized
```

#### Problem

`BaseNodeProperty` defines multiple metadata properties that all nodes inherit, even when they don't need them. While these have default implementations, this violates ISP because:

1. **Interface Bloat**: All nodes are exposed to 5+ metadata properties they may not need
2. **Unnecessary Inheritance**: Simple nodes inherit complex property logic they never use
3. **Forced Awareness**: Developers must understand properties they don't need
4. **Default Behavior**: Default implementations may not be appropriate for all node types
5. **Testing Overhead**: Must consider all properties even when testing simple nodes

#### Solution Approach

1. **Separate Interfaces**: Split metadata properties into separate interfaces
2. **Optional Mixins**: Make metadata properties optional mixins
3. **Composition**: Use composition for metadata instead of inheritance
4. **Lazy Properties**: Only compute properties when accessed

#### Refactored Implementation (After)

**Option 1: Separate Metadata Interfaces**

```python
from abc import ABC, abstractmethod
from typing import Protocol

# Core required properties
class INodeIdentifier(Protocol):
    """Interface for node identification - required for all nodes."""
    
    @classmethod
    @abstractmethod
    def identifier(cls) -> str:
        """Return the node type identifier."""
        pass
    
    @property
    @abstractmethod
    def execution_pool(self) -> PoolType:
        """Preferred execution pool."""
        pass

# Optional metadata interfaces
class IHasLabel(Protocol):
    """Optional interface for nodes with custom labels."""
    
    @property
    def label(self) -> str:
        """Get display label."""
        return self.__class__.__name__

class IHasDescription(Protocol):
    """Optional interface for nodes with descriptions."""
    
    @property
    def description(self) -> str:
        """Get node description."""
        return ""

class IHasIcon(Protocol):
    """Optional interface for nodes with icons."""
    
    @property
    def icon(self) -> str:
        """Get icon identifier."""
        return ""

class IHasPorts(Protocol):
    """Optional interface for nodes with custom ports."""
    
    @property
    def input_ports(self) -> list:
        """Get input ports."""
        return [{"id": "default", "label": "In"}]
    
    @property
    def output_ports(self) -> list:
        """Get output ports."""
        return [{"id": "default", "label": "Out"}]

# Base class with only required properties
class BaseNodeProperty(ABC):
    """Base class with only required node properties."""
    
    @property
    @abstractmethod
    def execution_pool(self) -> PoolType:
        pass
    
    @classmethod
    @abstractmethod
    def identifier(cls) -> str:
        pass

# Optional mixins for metadata
class NodeMetadataMixin:
    """Mixin for nodes that want metadata properties."""
    
    @property
    def label(self) -> str:
        return self.__class__.__name__
    
    @property
    def description(self) -> str:
        return ""
    
    @property
    def icon(self) -> str:
        return ""

class NodePortsMixin:
    """Mixin for nodes that want custom ports."""
    
    @property
    def input_ports(self) -> list:
        return [{"id": "default", "label": "In"}]
    
    @property
    def output_ports(self) -> list:
        return [{"id": "default", "label": "Out"}]

# Usage: Simple nodes - only required properties
class QueueReader(ProducerNode):  # ✅ Only inherits required properties
    @classmethod
    def identifier(cls) -> str:
        return "queue-reader-dummy"
    
    @property
    def execution_pool(self) -> PoolType:
        return PoolType.ASYNC
    # No label, description, icon, ports needed

# Usage: Nodes with metadata - explicitly use mixins
class CounterNode(ProducerNode, NodeMetadataMixin):  # ✅ Explicitly wants metadata
    @classmethod
    def identifier(cls) -> str:
        return "counter"
    
    @property
    def execution_pool(self) -> PoolType:
        return PoolType.ASYNC
    
    @property
    def label(self) -> str:
        return "Counter"  # Override from mixin
    
    @property
    def description(self) -> str:
        return "Iterates between min and max values"
    
    @property
    def icon(self) -> str:
        return "counter"
```

**Option 2: Lazy Property Access**

```python
class BaseNodeProperty(ABC):
    """Base class with lazy property access."""
    
    @property
    @abstractmethod
    def execution_pool(self) -> PoolType:
        pass
    
    @classmethod
    @abstractmethod
    def identifier(cls) -> str:
        pass
    
    def get_label(self) -> str:
        """Get label - only called when needed."""
        if hasattr(self, '_label'):
            return self._label
        return self.__class__.__name__
    
    def get_description(self) -> str:
        """Get description - only called when needed."""
        if hasattr(self, '_description'):
            return self._description
        return ""
    
    def get_icon(self) -> str:
        """Get icon - only called when needed."""
        if hasattr(self, '_icon'):
            return self._icon
        return ""
    
    def get_input_ports(self) -> list:
        """Get input ports - only called when needed."""
        if hasattr(self, '_input_ports'):
            return self._input_ports
        return [{"id": "default", "label": "In"}]
    
    def get_output_ports(self) -> list:
        """Get output ports - only called when needed."""
        if hasattr(self, '_output_ports'):
            return self._output_ports
        return [{"id": "default", "label": "Out"}]

# Usage: Simple nodes don't set metadata
class QueueReader(ProducerNode):
    # Only required properties
    pass

# Usage: Nodes with metadata set it explicitly
class CounterNode(ProducerNode):
    def __init__(self, config):
        super().__init__(config)
        self._label = "Counter"
        self._description = "Iterates between min and max values"
        self._icon = "counter"
```

#### Benefits

- ✅ **Minimal Interface**: Simple nodes only see properties they need
- ✅ **Explicit Intent**: Nodes that want metadata explicitly use mixins
- ✅ **No Forced Properties**: Nodes aren't forced to inherit unused properties
- ✅ **Better Performance**: Properties only computed when needed
- ✅ **Clearer Code**: Intent is clear from class inheritance
- ✅ **Easier Testing**: Test only properties that are actually used

---

### Violation 3: BaseNodeMethod Lifecycle Methods

**Location**: `core/Node/Core/Node/Core/BaseNodeMethod.py:9-48`

#### Current Implementation (Before)

```python
class BaseNodeMethod(ABC):
    """Base class for node execution methods."""
    
    async def setup(self):
        """Setup method - default does nothing."""
        pass  # ❌ All nodes inherit this
    
    async def init(self):
        """Init method - default does nothing."""
        pass  # ❌ All nodes inherit this
    
    @abstractmethod
    async def execute(self, previous_node_output: NodeOutput) -> NodeOutput:
        """Execute the node logic."""
        pass
    
    async def cleanup(self):
        """Cleanup method - default does nothing."""
        pass  # ❌ All nodes inherit this
    
    def get_form(self) -> Optional[BaseForm]:
        """Get form - default returns None."""
        return None  # ❌ All nodes inherit this
```

**Example: Nodes That Don't Need All Lifecycle Methods**

```python
# CounterNode - Only needs execute(), doesn't need setup() or cleanup()
class CounterNode(ProducerNode):
    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        # Core logic
        return NodeOutput(...)
    
    # ❌ Inherits setup(), init(), cleanup(), get_form() but doesn't use them
    # (Actually overrides cleanup() but many nodes don't)

# IfCondition - Simple node, only needs execute()
class IfCondition(BlockingNode):
    def get_form(self) -> BaseForm:
        return IfConditionForm()
    
    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        # Core logic
        return NodeOutput(...)
    
    # ❌ Inherits setup(), init(), cleanup() but doesn't use them
```

**Example: Nodes That Use Lifecycle Methods**

```python
# QueueReader - Needs setup() for DataStore initialization
class QueueReader(ProducerNode):
    async def setup(self):
        """Initialize the DataStore connection."""
        self.data_store = DataStore()  # ✅ Actually uses setup()
    
    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        # Uses self.data_store
        return NodeOutput(...)

# QueueWriter - Needs setup() and cleanup()
class QueueWriter(NonBlockingNode):
    async def setup(self):
        """Initialize the DataStore connection."""
        self.data_store = DataStore()  # ✅ Actually uses setup()
    
    async def cleanup(self, node_data: NodeOutput = None):
        """Close DataStore connection."""
        await self.data_store.close()  # ✅ Actually uses cleanup()
    
    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        # Uses self.data_store
        return NodeOutput(...)
```

#### Problem

`BaseNodeMethod` defines multiple lifecycle methods that all nodes inherit, even when they don't need them. While these have default implementations, this violates ISP because:

1. **Lifecycle Overhead**: All nodes inherit 4+ lifecycle methods they may never use
2. **Unnecessary Methods**: Simple nodes are exposed to complex lifecycle management
3. **Default Behavior**: Default implementations (empty pass) don't provide value but add complexity
4. **Forced Awareness**: Developers must understand lifecycle methods even for simple nodes
5. **Testing Complexity**: Must consider all lifecycle methods when testing

#### Solution Approach

1. **Separate Lifecycle Interfaces**: Create separate interfaces for different lifecycle needs
2. **Optional Mixins**: Make lifecycle methods optional mixins
3. **Hook Pattern**: Use hook pattern where methods are only called if they exist
4. **Composition**: Use composition for lifecycle management

#### Refactored Implementation (After)

**Option 1: Separate Lifecycle Interfaces**

```python
from abc import ABC, abstractmethod
from typing import Optional, Protocol

# Core execution interface - required
class IExecutable(Protocol):
    """Interface for node execution - required for all nodes."""
    
    @abstractmethod
    async def execute(self, previous_node_output: NodeOutput) -> NodeOutput:
        """Execute the node logic."""
        pass

# Optional lifecycle interfaces
class IHasSetup(Protocol):
    """Optional interface for nodes that need setup."""
    
    async def setup(self) -> None:
        """Initialize resources."""
        pass

class IHasCleanup(Protocol):
    """Optional interface for nodes that need cleanup."""
    
    async def cleanup(self, node_data: Optional[NodeOutput] = None) -> None:
        """Clean up resources."""
        pass

class IHasForm(Protocol):
    """Optional interface for nodes that have forms."""
    
    def get_form(self) -> Optional[BaseForm]:
        """Get configuration form."""
        return None

# Base class with only required method
class BaseNodeMethod(ABC):
    """Base class with only required execution method."""
    
    @abstractmethod
    async def execute(self, previous_node_output: NodeOutput) -> NodeOutput:
        """Execute the node logic."""
        pass

# Optional mixins for lifecycle
class SetupMixin:
    """Mixin for nodes that need setup."""
    
    async def setup(self) -> None:
        """Initialize resources - override in subclasses."""
        pass

class CleanupMixin:
    """Mixin for nodes that need cleanup."""
    
    async def cleanup(self, node_data: Optional[NodeOutput] = None) -> None:
        """Clean up resources - override in subclasses."""
        pass

class FormMixin:
    """Mixin for nodes that have forms."""
    
    def get_form(self) -> Optional[BaseForm]:
        """Get configuration form - override in subclasses."""
        return None

# Update BaseNode to handle optional lifecycle
class BaseNode(BaseNodeProperty, BaseNodeMethod, ABC):
    async def init(self):
        """Initialize node - calls setup if it exists."""
        if not self.is_ready():
            raise ValueError(f"Node {self.node_config.id} is not ready")
        
        # Only call setup if node implements it
        if hasattr(self, 'setup'):
            await self.setup()
    
    async def run(self, node_data: NodeOutput) -> NodeOutput:
        """Main entry point - calls cleanup if it exists."""
        if isinstance(node_data, ExecutionCompleted):
            # Only call cleanup if node implements it
            if hasattr(self, 'cleanup'):
                await self.cleanup(node_data)
            return node_data
        
        self.populate_form_values(node_data)
        output = await self.execute(node_data)
        self.execution_count += 1
        return output

# Usage: Simple nodes - only required method
class IfCondition(BlockingNode):  # ✅ Only implements execute()
    def get_form(self) -> BaseForm:
        return IfConditionForm()
    
    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        # Core logic
        return NodeOutput(...)
    # No setup() or cleanup() needed

# Usage: Nodes with lifecycle - explicitly use mixins
class QueueReader(ProducerNode, SetupMixin):  # ✅ Explicitly needs setup
    async def setup(self):
        """Initialize the DataStore connection."""
        self.data_store = DataStore()
    
    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        # Uses self.data_store
        return NodeOutput(...)

class QueueWriter(NonBlockingNode, SetupMixin, CleanupMixin):  # ✅ Needs both
    async def setup(self):
        """Initialize the DataStore connection."""
        self.data_store = DataStore()
    
    async def cleanup(self, node_data: Optional[NodeOutput] = None):
        """Close DataStore connection."""
        await self.data_store.close()
    
    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        # Uses self.data_store
        return NodeOutput(...)
```

**Option 2: Hook Pattern**

```python
class BaseNodeMethod(ABC):
    """Base class with hook pattern for lifecycle methods."""
    
    @abstractmethod
    async def execute(self, previous_node_output: NodeOutput) -> NodeOutput:
        """Execute the node logic - required."""
        pass
    
    # Lifecycle hooks - only called if implemented
    # No default implementations - nodes only implement what they need

class BaseNode(BaseNodeProperty, BaseNodeMethod, ABC):
    async def init(self):
        """Initialize node - calls setup hook if it exists."""
        if not self.is_ready():
            raise ValueError(f"Node {self.node_config.id} is not ready")
        
        # Hook: call setup if implemented
        if hasattr(self, 'setup') and callable(getattr(self, 'setup')):
            await self.setup()
    
    async def run(self, node_data: NodeOutput) -> NodeOutput:
        """Main entry point - calls cleanup hook if it exists."""
        if isinstance(node_data, ExecutionCompleted):
            # Hook: call cleanup if implemented
            if hasattr(self, 'cleanup') and callable(getattr(self, 'cleanup')):
                await self.cleanup(node_data)
            return node_data
        
        self.populate_form_values(node_data)
        output = await self.execute(node_data)
        self.execution_count += 1
        return output
    
    def get_form(self) -> Optional[BaseForm]:
        """Get form - calls hook if it exists."""
        if hasattr(self, 'get_form') and callable(getattr(self, 'get_form')):
            # Check if it's the base method or overridden
            method = getattr(self, 'get_form')
            if method.__func__ != BaseNodeMethod.get_form:
                return method()
        return None

# Usage: Simple nodes - only implement what they need
class IfCondition(BlockingNode):
    def get_form(self) -> BaseForm:
        return IfConditionForm()
    
    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        return NodeOutput(...)
    # No setup() or cleanup() - hooks won't be called

# Usage: Nodes with lifecycle - implement hooks
class QueueReader(ProducerNode):
    async def setup(self):  # ✅ Hook - will be called
        self.data_store = DataStore()
    
    async def execute(self, node_data: NodeOutput) -> NodeOutput:
        return NodeOutput(...)
    # No cleanup() - hook won't be called
```

#### Benefits

- ✅ **Minimal Interface**: Nodes only see lifecycle methods they need
- ✅ **Explicit Lifecycle**: Nodes that need lifecycle explicitly implement hooks or use mixins
- ✅ **No Forced Methods**: Nodes aren't forced to inherit unused lifecycle methods
- ✅ **Clearer Intent**: Intent is clear from which methods are implemented
- ✅ **Better Performance**: Lifecycle methods only called when they exist
- ✅ **Easier Testing**: Test only lifecycle methods that are actually used

---

### Violation 4: BaseManager Helper Methods

**Location**: `apps/browsersession/managers/base_manager.py:11-129`

#### Current Implementation (Before)

```python
class BaseManager:
    """Base class for managers with common error handling and validation."""
    
    def __init__(
        self,
        browser_manager: Optional[BrowserManager] = None,
        message_sender: Optional[WebSocketMessageSender] = None
    ):
        self.browser_manager = browser_manager
        self.message_sender = message_sender
    
    async def _ensure_browser_initialized(self) -> bool:
        """Ensure browser manager is initialized."""
        # ❌ All managers inherit this
    
    async def _ensure_page_available(self) -> bool:
        """Ensure browser manager and active page are available."""
        # ❌ All managers inherit this
    
    async def _get_page_or_error(self, page_id: str) -> Optional[Page]:
        """Get page by ID or send error if not found."""
        # ❌ All managers inherit this
    
    async def _handle_error(
        self,
        operation_name: str,
        error: Exception,
        error_message: str,
        success_message: Optional[str] = None
    ) -> None:
        """Handle errors consistently."""
        # ❌ All managers inherit this
    
    async def _execute_with_error_handling(
        self,
        operation_name: str,
        operation_func,
        error_message_template: str,
        success_message: Optional[str] = None
    ) -> bool:
        """Execute an operation with consistent error handling."""
        # ❌ All managers inherit this
```

**Example: Managers That Don't Need All Methods**

```python
# PageEventCoordinator - Doesn't inherit from BaseManager
# But if it did, it wouldn't need browser/page validation methods
class PageEventCoordinator:
    """Coordinates page lifecycle events."""
    
    def __init__(self, page_manager, message_sender):
        self.page_manager = page_manager
        self.message_sender = message_sender
        # ✅ Doesn't need browser_manager validation
    
    # Would inherit _ensure_browser_initialized(), _ensure_page_available()
    # but doesn't need them

# MessageRouter - Doesn't inherit from BaseManager
# Doesn't need any browser/page validation
class MessageRouter:
    """Routes WebSocket messages to appropriate handlers."""
    
    def __init__(self, mouse_handler, keyboard_handler, start_callback):
        self.mouse_handler = mouse_handler
        self.keyboard_handler = keyboard_handler
        # ✅ Doesn't need browser_manager or message_sender
```

**Example: Managers That Use BaseManager Methods**

```python
# PageManager - Uses browser/page validation
class PageManager(BaseManager):
    async def switch_active_page(self, page_id: str) -> None:
        if not await self._ensure_page_available():  # ✅ Uses inherited method
            return
        # ... implementation

# NavigationManager - Uses browser/page validation and error handling
class NavigationManager(BaseManager):
    async def handle_navigation(self, data: dict) -> None:
        if not await self._ensure_page_available():  # ✅ Uses inherited method
            return
        
        await self._execute_with_error_handling(  # ✅ Uses inherited method
            operation_name='handle_navigation',
            operation_func=_navigate_operation,
            error_message_template='Navigation error: {error}'
        )
```

#### Problem

`BaseManager` provides helper methods for browser/page validation and error handling that all managers inherit, even when they don't need them. This violates ISP because:

1. **Unnecessary Inheritance**: Managers that don't work with browsers inherit browser validation methods
2. **Forced Dependencies**: Managers must accept `browser_manager` and `message_sender` even if unused
3. **Interface Bloat**: All managers see 5+ helper methods they may not need
4. **Coupling**: Managers are coupled to browser/page concepts they don't use
5. **Confusion**: Developers must understand methods they don't need

#### Solution Approach

1. **Separate Helper Classes**: Create separate helper classes for different concerns
2. **Composition Over Inheritance**: Use composition to add helpers only when needed
3. **Optional Mixins**: Make helper methods optional mixins
4. **Protocol-Based**: Use protocols to define minimal interfaces

#### Refactored Implementation (After)

**Option 1: Composition with Helper Classes**

```python
class BrowserValidationHelper:
    """Helper class for browser/page validation."""
    
    def __init__(
        self,
        browser_manager: Optional[BrowserManager] = None,
        message_sender: Optional[WebSocketMessageSender] = None
    ):
        self.browser_manager = browser_manager
        self.message_sender = message_sender
    
    async def ensure_browser_initialized(self) -> bool:
        """Ensure browser manager is initialized."""
        if not self.browser_manager:
            if self.message_sender:
                await self.message_sender.send_error('Browser not initialized')
            return False
        return True
    
    async def ensure_page_available(self) -> bool:
        """Ensure browser manager and active page are available."""
        if not await self.ensure_browser_initialized():
            return False
        
        if not self.browser_manager.page:
            if self.message_sender:
                await self.message_sender.send_error('No active page available')
            return False
        
        return True
    
    async def get_page_or_error(self, page_id: str) -> Optional[Page]:
        """Get page by ID or send error if not found."""
        if not await self.ensure_browser_initialized():
            return None
        
        page = self.browser_manager.get_page_by_id(page_id)
        if not page:
            if self.message_sender:
                await self.message_sender.send_error(f'Page with ID {page_id} not found')
            return None
        
        return page

class ErrorHandlingHelper:
    """Helper class for error handling."""
    
    def __init__(self, message_sender: Optional[WebSocketMessageSender] = None):
        self.message_sender = message_sender
    
    async def handle_error(
        self,
        operation_name: str,
        error: Exception,
        error_message: str,
        success_message: Optional[str] = None
    ) -> None:
        """Handle errors consistently."""
        logger.error("Error in operation", operation=operation_name, error=str(error), exc_info=True)
        if self.message_sender:
            await self.message_sender.send_error(error_message)
    
    async def execute_with_error_handling(
        self,
        operation_name: str,
        operation_func,
        error_message_template: str,
        success_message: Optional[str] = None
    ) -> bool:
        """Execute an operation with consistent error handling."""
        try:
            await operation_func()
            if success_message:
                logger.info("Operation completed successfully", operation=operation_name, message=success_message)
            return True
        except Exception as e:
            error_message = error_message_template.format(operation=operation_name, error=str(e))
            await self.handle_error(operation_name, e, error_message)
            return False

# Base manager - minimal, no helpers
class BaseManager:
    """Base class for managers - minimal interface."""
    
    def __init__(self, **kwargs):
        """Initialize base manager - subclasses define their own dependencies."""
        pass

# Managers that need browser validation - use composition
class PageManager(BaseManager):
    """Manages page operations - uses browser validation helper."""
    
    def __init__(
        self,
        browser_manager: BrowserManager,
        interaction_manager: InteractionManager,
        message_sender: WebSocketMessageSender
    ):
        super().__init__()
        self.browser_manager = browser_manager
        self.interaction_manager = interaction_manager
        self.message_sender = message_sender
        
        # ✅ Compose helper only when needed
        self._browser_helper = BrowserValidationHelper(browser_manager, message_sender)
        self._error_helper = ErrorHandlingHelper(message_sender)
    
    async def switch_active_page(self, page_id: str) -> None:
        if not await self._browser_helper.ensure_page_available():
            return
        # ... implementation

# Managers that don't need browser validation - no helpers
class MessageRouter(BaseManager):
    """Routes WebSocket messages - doesn't need browser validation."""
    
    def __init__(
        self,
        mouse_handler: Optional[MouseHandler] = None,
        keyboard_handler: Optional[KeyboardHandler] = None,
        start_callback: Optional[Callable] = None
    ):
        super().__init__()
        self.mouse_handler = mouse_handler
        self.keyboard_handler = keyboard_handler
        self.start_callback = start_callback
        # ✅ No browser_helper or error_helper - not needed
    
    async def route(self, text_data: str) -> None:
        # No browser validation needed
        pass
```

**Option 2: Optional Mixins**

```python
class BrowserValidationMixin:
    """Mixin for managers that need browser validation."""
    
    def __init__(self, *args, browser_manager=None, message_sender=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.browser_manager = browser_manager
        self.message_sender = message_sender
    
    async def _ensure_browser_initialized(self) -> bool:
        """Ensure browser manager is initialized."""
        if not self.browser_manager:
            if self.message_sender:
                await self.message_sender.send_error('Browser not initialized')
            return False
        return True
    
    async def _ensure_page_available(self) -> bool:
        """Ensure browser manager and active page are available."""
        if not await self._ensure_browser_initialized():
            return False
        
        if not self.browser_manager.page:
            if self.message_sender:
                await self.message_sender.send_error('No active page available')
            return False
        
        return True

class ErrorHandlingMixin:
    """Mixin for managers that need error handling."""
    
    def __init__(self, *args, message_sender=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_sender = message_sender
    
    async def _handle_error(self, operation_name: str, error: Exception, error_message: str) -> None:
        """Handle errors consistently."""
        logger.error("Error in operation", operation=operation_name, error=str(error), exc_info=True)
        if self.message_sender:
            await self.message_sender.send_error(error_message)
    
    async def _execute_with_error_handling(self, operation_name: str, operation_func, error_message_template: str) -> bool:
        """Execute an operation with consistent error handling."""
        try:
            await operation_func()
            return True
        except Exception as e:
            error_message = error_message_template.format(operation=operation_name, error=str(e))
            await self._handle_error(operation_name, e, error_message)
            return False

# Base manager - minimal
class BaseManager:
    """Base class for managers - minimal interface."""
    pass

# Managers that need helpers - use mixins
class PageManager(BaseManager, BrowserValidationMixin, ErrorHandlingMixin):
    """Manages page operations - uses browser validation and error handling."""
    
    def __init__(self, browser_manager, interaction_manager, message_sender):
        super().__init__(
            browser_manager=browser_manager,
            message_sender=message_sender
        )
        self.interaction_manager = interaction_manager
    
    async def switch_active_page(self, page_id: str) -> None:
        if not await self._ensure_page_available():  # ✅ From mixin
            return
        # ... implementation

# Managers that don't need helpers - no mixins
class MessageRouter(BaseManager):
    """Routes WebSocket messages - doesn't need browser validation."""
    
    def __init__(self, mouse_handler=None, keyboard_handler=None, start_callback=None):
        super().__init__()
        self.mouse_handler = mouse_handler
        self.keyboard_handler = keyboard_handler
        self.start_callback = start_callback
        # ✅ No mixins - doesn't need browser validation or error handling
```

#### Benefits

- ✅ **Minimal Interface**: Managers only see methods they need
- ✅ **Explicit Dependencies**: Managers explicitly declare what helpers they use
- ✅ **No Forced Methods**: Managers aren't forced to inherit unused helper methods
- ✅ **Better Composition**: Helpers can be reused across different manager types
- ✅ **Clearer Intent**: Intent is clear from which mixins/helpers are used
- ✅ **Easier Testing**: Test only helpers that are actually used

---

## Implementation Guidelines

### Step-by-Step Refactoring Process

1. **Identify Fat Interfaces**
   - Look for interfaces/abstract classes with many methods
   - Find methods that return empty/default values in implementations
   - Identify methods that are never called in certain subclasses

2. **Group Methods by Usage**
   - Categorize methods by which clients actually use them
   - Identify optional vs required methods
   - Find methods that are only used by some subclasses

3. **Create Separate Interfaces**
   - Split fat interfaces into smaller, focused interfaces
   - Use mixins for optional functionality
   - Create composition-based helpers for shared functionality

4. **Refactor Implementations**
   - Update classes to only implement interfaces they need
   - Remove empty/default method implementations
   - Use composition or mixins for optional features

5. **Update Clients**
   - Update code that uses refactored classes
   - Ensure backward compatibility where possible
   - Add tests for new interface structure

### Common Patterns to Use

#### 1. Interface Segregation with Mixins

```python
# Fat interface (violates ISP)
class IFatInterface(ABC):
    @abstractmethod
    def method1(self): pass
    @abstractmethod
    def method2(self): pass
    @abstractmethod
    def method3(self): pass
    @abstractmethod
    def method4(self): pass

# Segregated interfaces (follows ISP)
class IRequired(ABC):
    @abstractmethod
    def method1(self): pass

class IOptional1(ABC):
    @abstractmethod
    def method2(self): pass

class IOptional2(ABC):
    @abstractmethod
    def method3(self): pass

# Usage
class SimpleClass(IRequired):  # Only required methods
    def method1(self):
        pass

class ComplexClass(IRequired, IOptional1, IOptional2):  # All methods
    def method1(self): pass
    def method2(self): pass
    def method3(self): pass
```

#### 2. Composition Over Inheritance

```python
# Bad: Inheritance forces all methods
class BaseClass:
    def helper1(self): pass  # Not all subclasses need this
    def helper2(self): pass  # Not all subclasses need this

class SubClass(BaseClass):
    # Forced to inherit helper1 and helper2 even if unused
    pass

# Good: Composition allows selective use
class Helper1:
    def do_work(self): pass

class Helper2:
    def do_work(self): pass

class SubClass:
    def __init__(self):
        self.helper1 = Helper1()  # Only if needed
        # helper2 not included - not needed
```

#### 3. Hook Pattern

```python
# Base class with hooks
class BaseClass:
    def execute(self):
        # Call hook if it exists
        if hasattr(self, 'before_execute'):
            self.before_execute()
        
        # Core logic
        self._do_work()
        
        # Call hook if it exists
        if hasattr(self, 'after_execute'):
            self.after_execute()
    
    def _do_work(self):
        pass

# Simple implementation - no hooks
class SimpleClass(BaseClass):
    def _do_work(self):
        # Only implements what's needed
        pass

# Complex implementation - uses hooks
class ComplexClass(BaseClass):
    def before_execute(self):
        # Setup logic
        pass
    
    def _do_work(self):
        # Core logic
        pass
    
    def after_execute(self):
        # Cleanup logic
        pass
```

#### 4. Protocol-Based Interfaces

```python
from typing import Protocol

# Define minimal protocols
class IReadable(Protocol):
    def read(self) -> str: ...

class IWritable(Protocol):
    def write(self, data: str) -> None: ...

class IReadWrite(IReadable, IWritable, Protocol):
    pass

# Implementations only implement what they need
class Reader(IReadable):
    def read(self) -> str:
        return "data"

class Writer(IWritable):
    def write(self, data: str) -> None:
        pass

class ReaderWriter(IReadWrite):
    def read(self) -> str:
        return "data"
    
    def write(self, data: str) -> None:
        pass
```

### Testing Considerations

**Before Refactoring:**
```python
# Must test all methods even if unused
def test_simple_form():
    form = CounterForm()
    # Must test dependency methods even though they're empty
    assert form.get_field_dependencies() == {}
    assert form.populate_field("field", "value") == []
```

**After Refactoring:**
```python
# Only test methods that exist
def test_simple_form():
    form = CounterForm()
    # No dependency methods to test - they don't exist
    assert form.is_valid() == True

def test_form_with_dependencies():
    form = GoogleSheetsForm()
    # Only test dependency methods because form actually has them
    deps = form.get_field_dependencies()
    assert 'google_account' in deps
```

### Migration Strategy

1. **Phase 1: Add New Interfaces (Non-Breaking)**
   - Create new segregated interfaces alongside existing ones
   - Keep existing interfaces working
   - Add new optional mixins/helpers

2. **Phase 2: Update High-Priority Classes**
   - Refactor classes that benefit most from segregation
   - Update to use new interfaces
   - Maintain backward compatibility

3. **Phase 3: Gradual Migration**
   - Update remaining classes one by one
   - Remove empty implementations
   - Update tests

4. **Phase 4: Remove Old Interfaces**
   - Deprecate fat interfaces
   - Remove after all classes migrated
   - Update documentation

### Common Anti-Patterns to Avoid

1. **❌ Fat Interfaces**
   ```python
   # Bad: One interface with many methods
   class IWorker(ABC):
       def work(self): pass
       def eat(self): pass
       def sleep(self): pass
       def play(self): pass
   ```
   
   **✅ Segregated Interfaces:**
   ```python
   # Good: Separate interfaces
   class IWorker(ABC):
       def work(self): pass
   
   class IHuman(IWorker):
       def eat(self): pass
       def sleep(self): pass
   
   class IPlayer(IHuman):
       def play(self): pass
   ```

2. **❌ Forced Empty Implementations**
   ```python
   # Bad: Must implement unused methods
   class SimpleForm(BaseForm):
       def get_field_dependencies(self):
           return {}  # Empty - not used
   ```
   
   **✅ Optional Implementation:**
   ```python
   # Good: Only implement if needed
   class SimpleForm(BaseForm):
       # No dependency methods - not needed
       pass
   ```

3. **❌ Inheritance for Everything**
   ```python
   # Bad: Inheritance forces all methods
   class Manager(BaseManager):
       # Inherits 10+ methods, only uses 2
       pass
   ```
   
   **✅ Composition:**
   ```python
   # Good: Compose only what's needed
   class Manager:
       def __init__(self):
           self.helper = Helper()  # Only if needed
   ```

---

## Priority Ranking

### High Priority (Fix First)

1. **BaseForm Forcing DependencyInjector Implementation** ⭐⭐⭐
   - **Impact**: High - Affects all 13+ form classes in the codebase
   - **Complexity**: Medium - Requires interface separation
   - **Benefits**: Removes forced empty implementations, cleaner form code
   - **Affected Classes**: All forms inheriting from `BaseForm`

2. **BaseNodeProperty Requiring All Metadata Methods** ⭐⭐⭐
   - **Impact**: High - Affects all 100+ node classes
   - **Complexity**: Low - Properties have defaults, easy to segregate
   - **Benefits**: Cleaner node interfaces, explicit metadata usage
   - **Affected Classes**: All nodes inheriting from `BaseNode`

### Medium Priority

3. **BaseNodeMethod Lifecycle Methods** ⭐⭐
   - **Impact**: Medium - Affects all nodes, but methods have defaults
   - **Complexity**: Medium - Requires hook pattern or mixin approach
   - **Benefits**: Cleaner node lifecycle, explicit lifecycle management
   - **Affected Classes**: All nodes, especially simple ones

### Low Priority (Can Wait)

4. **BaseManager Helper Methods** ⭐
   - **Impact**: Low - Only affects 2 manager classes (PageManager, NavigationManager)
   - **Complexity**: Low - Simple composition or mixin solution
   - **Benefits**: Better separation of concerns, reusable helpers
   - **Affected Classes**: PageManager, NavigationManager

---

## Developer Checklist

Use this checklist when refactoring code to follow ISP:

### Before Refactoring

- [ ] Identify interfaces/abstract classes with many methods
- [ ] Find methods that return empty/default values in implementations
- [ ] Identify methods that are never called in certain subclasses
- [ ] Group methods by which clients actually use them
- [ ] Determine which methods are optional vs required
- [ ] Review existing tests to understand current behavior

### During Refactoring

- [ ] Create separate interfaces for different concerns
- [ ] Use mixins for optional functionality
- [ ] Use composition for shared functionality
- [ ] Remove empty/default method implementations
- [ ] Update classes to only implement interfaces they need
- [ ] Maintain backward compatibility where possible
- [ ] Write tests for new interface structure

### After Refactoring

- [ ] Verify existing tests still pass
- [ ] Add new tests for segregated interfaces
- [ ] Update documentation
- [ ] Check for any remaining fat interfaces
- [ ] Review code for other ISP violations
- [ ] Ensure no forced empty implementations remain

### Verification Questions

- [ ] Can I create a simple implementation without implementing unused methods?
- [ ] Are there any empty/default method implementations?
- [ ] Do all subclasses use all methods from their base class?
- [ ] Can I split interfaces into smaller, focused ones?
- [ ] Are optional features implemented via mixins or composition?
- [ ] Is the interface minimal for each client's needs?

### Code Review Checklist

When reviewing code for ISP compliance:

- [ ] No fat interfaces with many methods
- [ ] No forced empty/default implementations
- [ ] Optional features use mixins or composition
- [ ] Interfaces are segregated by client needs
- [ ] Simple implementations don't inherit complex interfaces
- [ ] Methods are only in interfaces if all implementers need them

### Red Flags (Indicators of ISP Violations)

Watch out for these patterns that violate ISP:

1. **Empty Method Implementations**
   ```python
   class MyClass(BaseClass):
       def unused_method(self):
           return {}  # Empty - not used
   ```

2. **Many Methods in One Interface**
   ```python
   class IFatInterface(ABC):
       def method1(self): pass
       def method2(self): pass
       # ... 10+ methods
   ```

3. **Forced Abstract Methods**
   ```python
   class BaseClass(ABC):
       @abstractmethod
       def method1(self): pass  # All subclasses must implement
       @abstractmethod
       def method2(self): pass  # But only some need this
   ```

4. **Inheritance for Everything**
   ```python
   class SimpleClass(BaseClass):
       # Inherits 20+ methods, only uses 2
       pass
   ```

---

## Summary

This document identified **4 major Interface Segregation Principle violations** in the codebase:

1. **BaseForm forcing DependencyInjector implementation** - All forms must implement dependency methods even when unused
2. **BaseNodeProperty requiring all metadata methods** - All nodes inherit metadata properties they may not need
3. **BaseNodeMethod lifecycle methods** - All nodes inherit lifecycle methods they may not use
4. **BaseManager helper methods** - Managers inherit browser validation methods they may not need

Each violation has been documented with:
- Current problematic code
- Explanation of the problem
- Refactored solution with code examples
- Benefits of the fix

**Next Steps:**
1. Review this document with the team
2. Prioritize violations based on impact
3. Start refactoring high-priority violations (BaseForm, BaseNodeProperty)
4. Use mixins, composition, and hook patterns for optional features
5. Update this document as violations are fixed
6. Use the checklist when writing new code

Remember: **Interface Segregation Principle is about creating small, focused interfaces that clients actually need. Avoid fat interfaces and forced implementations.**

---

## References

- [SOLID Principles - Interface Segregation Principle](https://en.wikipedia.org/wiki/Interface_segregation_principle)
- [Python Protocols (PEP 544)](https://www.python.org/dev/peps/pep-0544/)
- [Composition Over Inheritance](https://en.wikipedia.org/wiki/Composition_over_inheritance)
- Related Documentation:
  - [Dependency-Inversion-Violations.md](Dependency-Inversion-Violations.md)
  - [Open-Closed-Principle-Violations.md](Open-Closed-Principle-Violations.md)
  - [04-Node-System.md](04-Node-System.md)
  - [07-Form-System.md](07-Form-System.md)

---
