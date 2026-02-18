# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PyVRP is a state-of-the-art vehicle routing problem (VRP) solver. It uses a hybrid architecture: performance-critical parts are implemented in C++20, while the high-level algorithm and customization interface are in Python. This design provides both speed and flexibility.

The package supports various VRP variants including CVRP (capacitated), VRPTW (with time windows), multi-depot, pickups/deliveries, heterogeneous fleets, optional clients, and more.

**New features**:
- Elevation cost: Clients and depots support `elevation` parameter. Routes calculate `load × elevation_gain` cost for cargo bike optimization. Enable via `VehicleType(unit_elevation_cost=...)`. See `tests/test_elevation_minimal.py` for usage.

## Build System

PyVRP uses Meson as its build system to compile C++ extensions into Python modules.

### Building the project

```bash
# Install dependencies (uses uv package manager)
uv sync

# Build C++ extensions (release mode, default)
uv run buildtools/build_extensions.py

# Build with debug symbols and coverage
uv run buildtools/build_extensions.py --build_type debug --clean

# Build with verbose output
uv run buildtools/build_extensions.py --verbose
```

Build types:
- `release`: Optimized build (default)
- `debug`: Debug symbols, no optimization, enables coverage
- `debugoptimized`: Debug symbols with optimization

The build process uses Meson to:
1. Compile C++ source files in `pyvrp/cpp/` into static libraries
2. Generate Python bindings using pybind11 from `bindings.cpp` files
3. Install compiled extensions as `_*.so` files into the `pyvrp/` package directory

### Running tests

```bash
uv run pytest
```

### Linting and formatting

```bash
# Run all pre-commit hooks
uv run pre-commit run --all-files

# Run specific hook
uv run pre-commit run ruff --all-files
uv run pre-commit run mypy --all-files
```

The project uses:
- `ruff` for linting and import sorting (line length: 79)
- `mypy` for type checking
- `clang-format` for C++ formatting

## Architecture

### Hybrid Python/C++ Design

The codebase follows a clear separation:

**Python layer** (`pyvrp/*.py`):
- High-level algorithm orchestration (`IteratedLocalSearch`, `solve`)
- User-facing modeling interface (`Model`, `Edge`, `Profile`)
- Configuration and parameters (`SolveParams`, `PenaltyParams`, etc.)
- Utilities (plotting, reading instances, statistics)

**C++ layer** (`pyvrp/cpp/`):
- Performance-critical data structures (`Solution`, `Route`, `Trip`)
- Cost evaluation (`CostEvaluator`, with caching and delta evaluation)
- Local search implementation (`LocalSearch`, neighborhood structures)
- Search operators (`Exchange`, `SwapTails`, `RelocateWithDepot`, etc.)
- Problem data representation (`ProblemData`)

**Bindings** (`pyvrp/cpp/*/bindings.cpp`):
- Each subdirectory has a `bindings.cpp` that exposes C++ classes/functions to Python
- Compiled into extension modules named `_<subdir>.so` (e.g., `_pyvrp.so`, `_search.so`)
- Documentation is auto-generated from C++ headers into `*_docs.h` files

### Key Components

**Model interface** (`pyvrp/Model.py`):
- User-friendly API for defining VRP instances
- Creates `Client`, `Depot`, `VehicleType`, `ClientGroup` objects
- Builds `Edge` objects for routing profiles
- Converts to `ProblemData` for solving

**Solver** (`pyvrp/solve.py`):
- `solve()` function is the main entry point
- Constructs the algorithm components: `LocalSearch`, `PenaltyManager`, `IteratedLocalSearch`
- `SolveParams` allows customization of operators, penalties, neighborhoods

**Search operators** (`pyvrp/search/` and `pyvrp/cpp/search/`):
- Two types: `UnaryOperator` (single route) and `BinaryOperator` (two routes)
- Default operators: `Exchange10`, `Exchange20`, `Exchange11`, `Exchange21`, `Exchange22`, `SwapTails`, `RelocateWithDepot`, `RemoveAdjacentDepot`, `RemoveOptional`
- Operators evaluate moves using delta cost calculations for efficiency
- Custom operators can be added by implementing the operator interface

**Iterated Local Search** (`pyvrp/IteratedLocalSearch.py`):
- Uses late acceptance hill-climbing for solution acceptance
- Iterates between local search improvement and perturbation
- Restarts after `num_iters_no_improvement` iterations without improvement

**Penalty Manager** (`pyvrp/PenaltyManager.py`):
- Manages penalty weights for soft constraints (capacity, time windows)
- Dynamically adjusts penalties to balance feasibility and solution quality
- Provides `CostEvaluator` instances with current penalty weights

**Local Search** (`pyvrp/search/LocalSearch.py`, `pyvrp/cpp/search/LocalSearch.cpp`):
- Applies operators in a granular neighborhood
- Evaluates and applies improving moves
- Can run in normal or exhaustive mode

### Data Flow

1. User defines problem using `Model` API
2. `Model.data()` creates `ProblemData` instance
3. `solve()` constructs algorithm components
4. `IteratedLocalSearch.run()` executes the search:
   - Select parents from population (genetic algorithm component)
   - Apply crossover to create offspring
   - Apply local search to offspring
   - Update population with new solution
   - Adjust penalty weights
   - Check stopping criterion
5. Returns `Result` with best solution and statistics

### Extension Architecture

The C++ extensions mirror the Python package structure:
- `pyvrp/cpp/` → `_pyvrp.so` (core types)
- `pyvrp/cpp/search/` → `_search.so` (search operators)

Files in each directory:
- `*.h` and `*.cpp`: C++ implementation
- `bindings.cpp`: pybind11 bindings
- `*_docs.h`: Auto-generated docstrings (generated by Meson)

Naming convention: symbols start with `pyvrp::` namespace and `PYVRP_` prefix are reserved for internal use.

## Testing

Tests are organized by module in `tests/`:
- `tests/search/`: Tests for search operators and local search
- `tests/plotting/`: Plotting utilities tests
- Root-level tests for core functionality

Test utilities in `tests/helpers.py` provide fixtures and helper functions.

CI runs tests with:
- Multiple Python versions (3.11-3.14)
- Multiple compilers (gcc 10-14, clang 14-19)
- Coverage reporting to Codecov

## Instance Data

- `instances/`: Contains VRP benchmark instances
- Use `pyvrp.read()` to load instances in standard formats (VRPLIB, Solomon, etc.)
- Use `pyvrp.read_solution()` to load solution files

## Documentation

Please see docs/CLAUDE.md for an index of the documentation with brief summaries of each page.

## Development Notes

### When modifying C++ code:

1. Make changes to `.h` and `.cpp` files
2. Update `bindings.cpp` if adding/changing public API
3. Rebuild: `uv run buildtools/build_extensions.py --clean`
4. Run tests to verify changes

### When adding a new operator:

1. Create `.h` and `.cpp` files in `pyvrp/cpp/search/`
2. Inherit from `UnaryOperator` or `BinaryOperator`
3. Implement required methods (`evaluate`, `apply`, `supports`)
4. Add bindings in `pyvrp/cpp/search/bindings.cpp`
5. Export in `pyvrp/search/__init__.py`
6. Optionally add to `OPERATORS` list for default use

### When adding a new cost component:

**Two Route classes**: PyVRP has `pyvrp::Route` (full statistics) and `pyvrp::search::Route` (fast search). New cost methods must be added to both.

**CostEvaluatable concept**: Add method signature to `CostEvaluatable` concept in `CostEvaluator.h`:
```cpp
concept CostEvaluatable = requires(T arg) {
    { arg.newCost() } -> std::same_as<Cost>;
};
```

**Implementation order**:
1. Add field/getter to `Route` and `Solution` (in `pyvrp/cpp/`)
2. Compute in `Route` constructor (section between distance and load statistics)
3. Add stub to `search::Route` (often `return 0;`)
4. Update `CostEvaluator::penalisedCost()` to include new cost
5. Update bindings: expose getter, update pickle with `t.size() > N` pattern for backward compatibility
6. For performance: implement delta evaluation in `search::Route::Proposal`

**Location access**: Use `data.location(idx)` which handles both depots and clients via union type. Client indices are offset by `numDepots()`.

### Performance considerations:

- The C++ local search accounts for 80-90% of runtime
- Delta evaluation is critical: operators compute cost changes, not full costs
- Granular neighborhoods reduce search space from O(n²) to O(kn)
- Integer arithmetic is used for distances/durations (user must scale data)
- Caching is used extensively in cost evaluation

### Extending PyVRP for new VRP variants:

Guidelines at https://pyvrp.org/dev/new_vrp_variants.html

Generally requires:
1. Adding data attributes to `ProblemData`
2. Updating cost evaluation functions
3. Modifying operators to handle new constraints
4. Adding caching for new cost components if needed
