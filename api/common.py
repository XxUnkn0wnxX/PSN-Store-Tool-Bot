class APIError(Exception):
    "Exception raised for any type of errors in the API."

    def __init__(
        self,
        message: str,
        code: str | None = None,
        hints: dict[str, bool] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.hints = hints or {}
