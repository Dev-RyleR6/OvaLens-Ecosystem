from datetime import datetime, timezone
from fastapi import Request, status
from fastapi.responses import JSONResponse


class OvaLensAPIException(Exception):
    """Base API Exception for OvaLens domain errors."""
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, error_code: str = "BAD_REQUEST"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)


class DuplicateEntityException(OvaLensAPIException):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=status.HTTP_409_CONFLICT, error_code="DUPLICATE_ENTITY")


class EntityNotFoundException(OvaLensAPIException):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=status.HTTP_404_NOT_FOUND, error_code="NOT_FOUND")


class InvalidBatchStateTransitionException(OvaLensAPIException):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, error_code="INVALID_STATE_TRANSITION")


async def ovalens_exception_handler(request: Request, exc: OvaLensAPIException) -> JSONResponse:
    """Standardized RFC 7807 problem details JSON format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "status_code": exc.status_code,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": request.url.path
        }
    )
