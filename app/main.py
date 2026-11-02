from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="TRAKKO")

    @app.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
