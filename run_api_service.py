import os

import uvicorn


HOST = os.environ.get("IGSISMANI_API_HOST", "0.0.0.0")
PORT = int(os.environ.get("IGSISMANI_API_PORT", "8000"))
WORKERS = int(os.environ.get("IGSISMANI_API_WORKERS", "1"))
LOG_LEVEL = os.environ.get("IGSISMANI_API_LOG_LEVEL", "info")


if __name__ == "__main__":
    uvicorn.run(
        "iganima.api.main:app",
        host=HOST,
        port=PORT,
        workers=WORKERS,
        log_level=LOG_LEVEL,
    )