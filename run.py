import os
import uvicorn

if __name__ == "__main__":
    host = os.environ.get("EFAKE_HOST", "127.0.0.1")
    port = int(os.environ.get("EFAKE_PORT", "8000"))
    uvicorn.run("backend.main:app", host=host, port=port, reload=True)
