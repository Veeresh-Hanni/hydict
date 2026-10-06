class HydictError(Exception):
    """Base exception for hydict."""


class BackendError(HydictError):
    """Base exception for backend failures."""


class BackendConnectionError(BackendError):
    """Raised when a backend cannot be reached."""


class BackendOperationError(BackendError):
    """Raised when a backend operation fails."""