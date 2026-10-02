"""Errors the planning rules raise.

These are not HTTP errors. The API layer translates them into responses.
Keeping them here means the rules can be tested without a web server.
"""


class DomainError(Exception):
    def __init__(self, message: str, status_code: int = 409) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
