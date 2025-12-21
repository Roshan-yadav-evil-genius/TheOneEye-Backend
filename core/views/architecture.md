# Views Package Architecture

This document describes the architecture of the Views package, which provides a Flask-based web interface for the Node Engine.

## Package Structure

```
views/
├── __init__.py               # Package exports
├── app.py                    # Flask application factory
├── architecture.md           # This document
├── routes/                   # HTTP route handlers
│   ├── __init__.py
│   ├── pages.py              # HTML page routes
│   └── api.py                # REST API endpoints
├── services/                 # Business logic layer
│   ├── __init__.py           # ServiceContainer
│   ├── node_registry.py      # Node lookup & caching
│   ├── node_loader.py        # Dynamic class loading
│   ├── form_loader.py        # Form serialization
│   └── node_executor.py      # Node execution
├── scanner/                  # Node scanning layer
│   ├── __init__.py
│   ├── metadata_extractor.py # AST parsing
│   ├── file_scanner.py       # File scanning
│   ├── directory_scanner.py  # Directory traversal
│   └── tree_utils.py         # Tree operations
└── templates/
    └── index.html            # Web UI template
```

## High-Level Architecture

```mermaid
flowchart TB
    subgraph Client [Client Layer]
        Browser[Web Browser]
    end

    subgraph Routes [Routes Layer]
        Pages[pages.py]
        API[api.py]
    end

    subgraph Services [Services Layer]
        Container[ServiceContainer]
        Registry[NodeRegistry]
        Loader[NodeLoader]
        FormLoader[FormLoader]
        Executor[NodeExecutor]
    end

    subgraph Scanner [Scanner Layer]
        DirScanner[DirectoryScanner]
        FileScanner[FileScanner]
        Extractor[MetadataExtractor]
        TreeUtils[TreeUtils]
    end

    subgraph NodeSystem [Node System]
        NodeClasses[Node Classes]
        Forms[Form Classes]
    end

    Browser -->|HTTP| Pages
    Browser -->|HTTP| API
    
    Pages --> Container
    API --> Container
    
    Container --> Registry
    Container --> Loader
    Container --> FormLoader
    Container --> Executor
    
    Registry --> DirScanner
    FormLoader --> Loader
    Executor --> Loader
    
    DirScanner --> FileScanner
    DirScanner --> TreeUtils
    FileScanner --> Extractor
    
    Loader -->|Dynamic Import| NodeClasses
    FormLoader -->|Serialize| Forms
```

## Layer Responsibilities

### Routes Layer
Thin controllers that handle HTTP requests and delegate to services.

```mermaid
flowchart LR
    subgraph RoutesLayer [Routes Layer]
        direction TB
        PagesBlueprint[pages_bp]
        APIBlueprint[api_bp]
    end

    PagesBlueprint -->|"GET /"| IndexPage[Render index.html]
    
    APIBlueprint -->|"GET /api/nodes"| GetNodes[Get Node Tree]
    APIBlueprint -->|"GET /api/nodes/flat"| GetFlat[Get Flat List]
    APIBlueprint -->|"GET /api/nodes/count"| GetCount[Get Node Count]
    APIBlueprint -->|"GET /api/node/id/form"| GetForm[Get Node Form]
    APIBlueprint -->|"POST /api/node/id/execute"| Execute[Execute Node]
```

### Services Layer
Business logic with dependency injection via ServiceContainer.

```mermaid
classDiagram
    class ServiceContainer {
        -project_root: Path
        -_node_registry: NodeRegistry
        -_node_loader: NodeLoader
        -_form_loader: FormLoader
        -_node_executor: NodeExecutor
        +node_registry: NodeRegistry
        +node_loader: NodeLoader
        +form_loader: FormLoader
        +node_executor: NodeExecutor
    }

    class NodeRegistry {
        -_scanner: DirectoryScanner
        -_cache: Dict
        -_flat_cache: List
        +get_all_nodes() Dict
        +get_nodes_flat() List
        +find_by_identifier(id) Dict
        +get_count() int
        +refresh() void
    }

    class NodeLoader {
        -_project_root: Path
        +load_class(metadata) Type
        -_import_module(path) Module
    }

    class FormLoader {
        -_node_loader: NodeLoader
        +load_form(metadata) Dict
        -_create_dummy_instance() Node
        -_serialize_form(form) Dict
    }

    class NodeExecutor {
        -_node_loader: NodeLoader
        +execute(metadata, input, form) Dict
        -_run_node(class, metadata, input, form) Any
    }

    ServiceContainer --> NodeRegistry
    ServiceContainer --> NodeLoader
    ServiceContainer --> FormLoader
    ServiceContainer --> NodeExecutor
    
    FormLoader --> NodeLoader
    NodeExecutor --> NodeLoader
    NodeRegistry --> DirectoryScanner
```

### Scanner Layer
Scans filesystem and extracts node metadata using AST parsing.

```mermaid
classDiagram
    class DirectoryScanner {
        -_file_scanner: FileScanner
        +scan_directory(path) Dict
        +scan_nodes_folder(path) Dict
        -_should_skip(name) bool
        -_prune_empty_categories(nodes) Dict
    }

    class FileScanner {
        -_extractor: MetadataExtractor
        +scan_file(path) List~Dict~
        -_read_file(path) str
    }

    class MetadataExtractor {
        +NODE_BASE_TYPES: Set
        +extract_from_class(node) Dict
        -_get_node_type(node) str
        -_extract_identifier(node) str
        -_extract_form_class_name(node) str
        -_extract_property_string(node, name) str
    }

    class TreeUtils {
        <<functions>>
        +count_nodes(folder) int
        +prune_empty_folders(folder) Dict
        +flatten_nodes(folder, path) List
    }

    DirectoryScanner --> FileScanner
    DirectoryScanner --> TreeUtils
    FileScanner --> MetadataExtractor
```

## Request Flow Diagrams

### Page Load Flow

```mermaid
sequenceDiagram
    participant B as Browser
    participant P as pages.py
    participant SC as ServiceContainer
    participant NR as NodeRegistry
    participant DS as DirectoryScanner
    participant FS as FileScanner
    participant ME as MetadataExtractor

    B->>P: GET /
    P->>SC: get services
    P->>NR: get_all_nodes()
    
    alt Cache Miss
        NR->>DS: scan_nodes_folder()
        DS->>DS: iterate categories
        
        loop Each Python File
            DS->>FS: scan_file(path)
            FS->>FS: read file contents
            FS->>ME: extract_from_class(ast_node)
            ME-->>FS: node metadata
            FS-->>DS: list of nodes
        end
        
        DS->>DS: prune_empty_folders()
        DS-->>NR: hierarchical tree
        NR->>NR: cache result
    end
    
    NR-->>P: nodes tree
    P->>P: count_nodes()
    P->>P: render template
    P-->>B: HTML response
```

### Get Node Form Flow

```mermaid
sequenceDiagram
    participant B as Browser
    participant A as api.py
    participant SC as ServiceContainer
    participant NR as NodeRegistry
    participant FL as FormLoader
    participant NL as NodeLoader

    B->>A: GET /api/node/{id}/form
    A->>SC: get services
    A->>NR: find_by_identifier(id)
    NR-->>A: node metadata
    
    alt Node Not Found
        A-->>B: 404 Error
    else Node Has No Form
        A-->>B: JSON with form: null
    else Node Has Form
        A->>FL: load_form(metadata)
        FL->>NL: load_class(metadata)
        NL->>NL: import module
        NL->>NL: get class attribute
        NL-->>FL: node class
        FL->>FL: create dummy instance
        FL->>FL: call get_form()
        FL->>FL: serialize form
        FL-->>A: form JSON
        A-->>B: JSON response
    end
```

### Execute Node Flow

```mermaid
sequenceDiagram
    participant B as Browser
    participant A as api.py
    participant SC as ServiceContainer
    participant NR as NodeRegistry
    participant NE as NodeExecutor
    participant NL as NodeLoader
    participant NC as NodeClass

    B->>A: POST /api/node/{id}/execute
    Note right of B: {input_data, form_data}
    
    A->>SC: get services
    A->>NR: find_by_identifier(id)
    NR-->>A: node metadata
    
    alt Node Not Found
        A-->>B: 404 Error
    else Node Found
        A->>NE: execute(metadata, input, form)
        NE->>NL: load_class(metadata)
        NL-->>NE: node class
        
        alt Load Failed
            NE-->>A: error response
        else Load Success
            NE->>NC: create instance
            NE->>NC: init()
            NE->>NC: run(input)
            NC-->>NE: result
            NE-->>A: success response
        end
        
        A-->>B: JSON response
    end
```

## Data Flow

### Node Metadata Structure

```mermaid
flowchart LR
    subgraph PythonFile [Python File]
        ClassDef[Class Definition]
    end

    subgraph Metadata [Node Metadata]
        Name[name]
        Identifier[identifier]
        Type[type]
        HasForm[has_form]
        FormClass[form_class]
        Label[label]
        Description[description]
        FilePath[file_path]
    end

    subgraph Tree [Folder Tree]
        Category[Category]
        Subfolder[Subfolder]
        Nodes[Nodes List]
    end

    ClassDef -->|AST Parse| Metadata
    Metadata -->|Organize| Tree
```

### Hierarchical Tree Structure

```mermaid
flowchart TB
    subgraph Root [Nodes Folder]
        direction TB
        Browser[Browser/]
        Data[Data/]
        Delay[Delay/]
    end

    subgraph BrowserCategory [Browser Category]
        direction TB
        BrowserNodes[nodes: WebPageLoader]
        Freelancer[Freelancer/]
        Actions[actions/]
    end

    subgraph FreelancerSub [Freelancer Subfolder]
        FreelancerNodes["nodes: Bidder, JobMonitor"]
    end

    Browser --> BrowserCategory
    BrowserCategory --> Freelancer
    Freelancer --> FreelancerSub
```

## Dependency Injection

```mermaid
flowchart TB
    subgraph Factory [Factory Functions]
        CreateApp[create_app]
        CreateServices[create_services]
        CreateScanner[create_scanner]
    end

    subgraph Instances [Created Instances]
        App[Flask App]
        Container[ServiceContainer]
        Scanner[DirectoryScanner]
    end

    subgraph Dependencies [Injected Dependencies]
        FileScn[FileScanner]
        Extract[MetadataExtractor]
    end

    CreateApp --> App
    CreateApp --> CreateServices
    CreateServices --> Container
    Container --> CreateScanner
    CreateScanner --> Scanner
    CreateScanner --> FileScn
    CreateScanner --> Extract
    
    App -->|extensions| Container
```

## Caching Strategy

```mermaid
stateDiagram-v2
    [*] --> Empty: Application Start
    
    Empty --> Scanning: First Request
    Scanning --> Cached: Scan Complete
    Cached --> Cached: Subsequent Requests
    Cached --> Empty: refresh() Called
    
    state Cached {
        [*] --> TreeCache
        TreeCache --> FlatCache: get_nodes_flat()
    }
```

## Error Handling

```mermaid
flowchart TB
    subgraph Errors [Error Types]
        FileError[File Read Error]
        SyntaxError[Python Syntax Error]
        ImportError[Module Import Error]
        ClassError[Class Load Error]
        ExecError[Execution Error]
    end

    subgraph Handling [Error Handling]
        LogError[Log to Console]
        ReturnNone[Return None/Empty]
        HTTPError[Return HTTP Error]
    end

    FileError --> LogError --> ReturnNone
    SyntaxError --> LogError --> ReturnNone
    ImportError --> LogError --> ReturnNone
    ClassError --> HTTPError
    ExecError --> HTTPError
```

## Design Principles

### Single Responsibility Principle

| Module | Single Responsibility |
|--------|----------------------|
| `MetadataExtractor` | Parse AST and extract class metadata |
| `FileScanner` | Read and scan Python files |
| `DirectoryScanner` | Traverse directories and build tree |
| `TreeUtils` | Operate on tree data structures |
| `NodeRegistry` | Cache and lookup node metadata |
| `NodeLoader` | Dynamically load Python classes |
| `FormLoader` | Load and serialize forms |
| `NodeExecutor` | Execute nodes with input data |
| `pages.py` | Handle HTML page requests |
| `api.py` | Handle API requests |

### Dependency Injection

Services are injected via `ServiceContainer`, enabling:
- Easy mocking for unit tests
- Lazy initialization
- Centralized configuration

### Application Factory Pattern

`create_app()` function allows:
- Multiple app instances for testing
- Custom configuration per instance
- Clean initialization flow

## API Reference

### Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Main web interface |
| GET | `/api/nodes` | Get all nodes as tree |
| GET | `/api/nodes/flat` | Get all nodes as flat list |
| GET | `/api/nodes/count` | Get total node count |
| GET | `/api/node/<id>/form` | Get node form JSON |
| POST | `/api/node/<id>/execute` | Execute a node |

### Scanner Factory

```python
from views.scanner import create_scanner

scanner = create_scanner()
nodes = scanner.scan_nodes_folder()
```

### Services Factory

```python
from views.services import create_services

services = create_services()
node = services.node_registry.find_by_identifier('my-node')
```

