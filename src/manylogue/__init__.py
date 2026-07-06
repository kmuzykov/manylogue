import os
import uvicorn
import typer

app = typer.Typer()


@app.command()
def run(home: str | None = None, host: str = "127.0.0.1",
        port: int = 8000, reload: bool = False) -> None:
    if home:
        os.environ["MANYLOGUE_HOME"] = home
    # Open SSE streams never drain on their own, and uvicorn's default graceful
    # shutdown waits for connections forever — Ctrl+C would hang until every
    # browser tab closes. Give the drain a short bound, then cancel the streams.
    uvicorn.run("manylogue.app:app", host=host, port=port, reload=reload,
                timeout_graceful_shutdown=3)


def main() -> None:
    app()
