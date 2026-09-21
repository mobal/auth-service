import pybreaker

DEFAULT_FAIL_MAX = 5
DEFAULT_RESET_TIMEOUT_SECONDS = 30


def create_circuit_breaker(name: str) -> pybreaker.CircuitBreaker:
    """Create a breaker with the defaults used by outbound clients."""
    return pybreaker.CircuitBreaker(
        fail_max=DEFAULT_FAIL_MAX,
        reset_timeout=DEFAULT_RESET_TIMEOUT_SECONDS,
        name=name,
    )
