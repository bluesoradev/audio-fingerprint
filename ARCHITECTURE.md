# Component-Based Architecture

This project has been refactored into a component-based architecture following senior developer best practices.

## Architecture Overview

The codebase is organized into clear layers with separation of concerns:

```
testm3/
├── core/                    # Domain models and interfaces
│   ├── models.py           # Domain models (QueryResult, TransformConfig, etc.)
│   └── interfaces.py       # Abstract interfaces for dependency injection
│
├── repositories/            # Data access layer
│   ├── index_repository.py # FAISS index operations
│   ├── file_repository.py  # File I/O operations
│   └── config_repository.py # Configuration management
│
├── services/                # Business logic layer
│   ├── query_service.py     # Main query orchestration
│   ├── transform_service.py # Transform-related logic
│   ├── aggregation_service.py # Result aggregation
│   └── recall_estimator.py  # Recall estimation
│
├── infrastructure/          # Infrastructure and DI
│   ├── dependency_container.py # Dependency injection container
│   └── exceptions.py        # Custom exceptions
│
├── api/                     # API layer
│   └── routes.py           # FastAPI route handlers
│
└── fingerprint/            # Legacy modules (being migrated)
    └── run_queries.py       # Original implementation
```

## Key Principles

### 1. Separation of Concerns
- **Core**: Domain models and interfaces (no dependencies on infrastructure)
- **Repositories**: Data access abstraction
- **Services**: Business logic orchestration
- **Infrastructure**: External dependencies and DI
- **API**: HTTP endpoints

### 2. Dependency Injection
All services are injected via interfaces, making the code:
- **Testable**: Easy to mock dependencies
- **Flexible**: Swap implementations without changing business logic
- **Maintainable**: Clear dependencies

### 3. Single Responsibility Principle
Each component has one clear responsibility:
- `QueryService`: Orchestrates query execution
- `AggregationService`: Aggregates segment results
- `TransformService`: Transform-related operations
- `IndexRepository`: Index operations only

### 4. Interface-Based Design
All dependencies use interfaces (`IQueryService`, `IIndexRepository`, etc.):
- Enables easy testing with mocks
- Allows swapping implementations
- Documents expected behavior

## Usage Examples

### Basic Query Execution

```python
from infrastructure.dependency_container import get_container
from pathlib import Path

# Initialize container
container = get_container()
container.load_index(Path("data/index.bin"))
container.load_model_config(Path("config/fingerprint_v1.yaml"))

# Get query service
query_service = container.get_query_service()

# Execute query
result = query_service.query_file(
    file_path=Path("audio/test.wav"),
    transform_type="low_pass_filter",
    expected_orig_id="track1"
)

# Access results
print(f"Top candidate: {result.top_candidates[0]}")
print(f"Recall@5: {result.get_recall_at_k(5)}")
```

### Custom Service Setup

```python
from repositories import IndexRepository, FileRepository, ConfigRepository
from services import QueryService, TransformService
from infrastructure.dependency_container import DependencyContainer

# Create custom container
container = DependencyContainer()
container.initialize_repositories()

# Load dependencies
container.load_index(index_path)
container.load_model_config(config_path)

# Get service
query_service = container.get_query_service()
```

## Migration Guide

### Migrating from `run_queries.py`

The original `run_query_on_file` function has been refactored into `QueryService.query_file()`:

**Before:**
```python
from fingerprint.run_queries import run_query_on_file

result = run_query_on_file(
    file_path,
    index,
    model_config,
    topk=30,
    index_metadata=metadata,
    transform_type="low_pass_filter"
)
```

**After:**
```python
from infrastructure.dependency_container import get_container

container = get_container()
container.load_index(index_path)
container.load_model_config(config_path)

query_service = container.get_query_service()
result = query_service.query_file(
    file_path=file_path,
    transform_type="low_pass_filter",
    expected_orig_id="track1"
)
```

## Benefits

1. **Testability**: Each component can be tested in isolation
2. **Maintainability**: Clear separation makes changes easier
3. **Extensibility**: Easy to add new features without breaking existing code
4. **Reusability**: Services can be reused across different contexts
5. **Type Safety**: Domain models provide clear contracts

## Next Steps

1. Migrate remaining code in `ui/app.py` to use new services
2. Add unit tests for each service
3. Create integration tests for full query pipeline
4. Document API endpoints
5. Add performance monitoring
