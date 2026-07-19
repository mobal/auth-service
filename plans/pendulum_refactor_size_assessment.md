# Pendulum to datetime Refactor Size Assessment

## Answer to the Original Question

**How big will the refactor be?**

The refactor to replace Pendulum with Python's built-in datetime library is of **moderate size and complexity**:

### Quantitative Measures:
- **Files affected**: 19 files (4 production code files, 10 test files, 1 configuration file, 1 initialization file)
- **Instances to refactor**: Approximately 57 instances of Pendulum usage
- **Lines of code to change**: Estimated 100-150 lines across all files
- **Estimated effort**: 8-12 hours including implementation, testing, and validation

### Complexity Breakdown:
1. **Simple replacements** (imports, basic method calls): 30-40 instances
2. **Medium complexity** (timestamp conversions, ISO formatting): 15-20 instances
3. **Higher complexity** (timezone handling, time arithmetic): 5-10 instances

### Risk Level: Medium
The main risks are:
- Ensuring timezone consistency across all datetime objects
- Maintaining compatibility with existing timestamp expectations
- Preserving test compatibility

## Detailed Breakdown

### Files That Need Changes

#### Production Code (4 files)
1. `app/__init__.py` - Timezone initialization
2. `app/repositories/authorization_code_repository.py` - Basic datetime operations
3. `app/services/auth_service.py` - Complex datetime operations and calculations
4. `app/services/token_service.py` - Timestamp conversions and formatting

#### Test Files (10 files)
All test files use various Pendulum methods for test data creation and assertions.

#### Configuration (1 file)
- `pyproject.toml` - Dependency removal

### Types of Changes Required

1. **Import Statement Updates**
   - Replace `import pendulum` with `from datetime import datetime, timezone, timedelta`

2. **Method Replacements**
   - `pendulum.now()` → `datetime.now(timezone.utc)`
   - `pendulum.from_timestamp(ts)` → `datetime.fromtimestamp(ts, timezone.utc)`
   - `dt.add(duration)` → `dt + timedelta(**duration_params)`
   - `dt.subtract(duration)` → `dt - timedelta(**duration_params)`

3. **Property Replacements**
   - `dt.int_timestamp` → `int(dt.timestamp())`
   - `dt.to_iso8601_string()` → `dt.isoformat().replace("+00:00", "Z")`

4. **Timezone Handling**
   - `pendulum.timezone("UTC")` → `timezone.utc`
   - `pendulum.set_local_timezone()` → Custom timezone handling logic

## Implementation Effort Estimate

### Phase 1: Preparation (1-2 hours)
- Create backup of current code
- Set up test environment
- Review current Pendulum usage patterns

### Phase 2: Code Refactoring (4-6 hours)
- Update production code files (2-3 hours)
- Update test files (2-3 hours)

### Phase 3: Testing and Validation (3-4 hours)
- Run unit tests and fix issues (1-2 hours)
- Run integration tests and fix issues (1-2 hours)
- Manual testing of critical datetime functionality (1 hour)

### Phase 4: Review and Polish (1-2 hours)
- Code review
- Documentation updates if needed
- Final validation

## Conclusion

This refactor is **moderately sized** - not trivial but also not extremely complex. It requires careful attention to detail, especially around timezone handling and timestamp conversions, but follows well-established patterns that make it predictable in scope.

The refactor offers good value by reducing external dependencies while maintaining all existing functionality, with the main benefit being reduced dependency on third-party libraries for core datetime operations.