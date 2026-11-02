class AppError(Exception):
    status_code = 400

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class UnauthorizedError(AppError):
    status_code = 401


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class InvalidError(AppError):
    status_code = 422
