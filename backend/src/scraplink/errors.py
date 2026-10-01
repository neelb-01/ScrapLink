class DomainError(Exception):
    """A business-rule failure, mapped to an HTTP status by the API layer."""

    status_code = 400

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class Invalid(DomainError):
    status_code = 422


class Forbidden(DomainError):
    status_code = 403


class NotFound(DomainError):
    status_code = 404


class Conflict(DomainError):
    status_code = 409
