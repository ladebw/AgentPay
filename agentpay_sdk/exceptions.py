"""Custom exceptions for the AgentPay SDK."""


class AgentPayError(Exception):
    """Base exception for all AgentPay SDK errors."""
    pass


class AuthenticationError(AgentPayError):
    """Raised when authentication fails."""
    pass


class ValidationError(AgentPayError):
    """Raised when input validation fails."""
    pass


class APIError(AgentPayError):
    """Raised when the API returns an error."""
    def __init__(self, message: str, status_code: int = None, response=None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class NotFoundError(APIError):
    """Raised when a resource is not found."""
    pass


class RateLimitError(APIError):
    """Raised when rate limit is exceeded."""
    pass