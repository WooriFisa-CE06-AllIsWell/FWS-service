from fastapi import FastAPI, Query
from pydantic import BaseModel

import db

app = FastAPI(title="FWS Log Server")


class LogEntry(BaseModel):
    level: str
    module: str = ""
    event: str = ""
    message: str
    vm_name: str = ""
    server_ip: str = ""


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/logs", status_code=201)
def receive_log(entry: LogEntry):
    db.insert_log(
        level=entry.level,
        module=entry.module,
        event=entry.event,
        message=entry.message,
        vm_name=entry.vm_name,
        server_ip=entry.server_ip,
    )
    return {"saved": True}


@app.get("/logs")
def get_logs(
    level: str = Query(None),
    event: str = Query(None),
    vm_name: str = Query(None),
    limit: int = Query(100, le=1000),
):
    return db.fetch_logs(level=level, event=event, vm_name=vm_name, limit=limit)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=9000, reload=True)
