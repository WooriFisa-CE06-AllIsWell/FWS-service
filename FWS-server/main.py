import logging
import logging.handlers
import json
import urllib.request

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers import vm, resources


class LogServerHandler(logging.Handler):
    """LOG_SERVER_URL 이 설정된 경우 로그를 HTTP POST 로 전송한다."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            parts = record.getMessage().split("|")
            event = parts[0].strip() if len(parts) > 0 else ""
            payload = json.dumps({
                "level": record.levelname,
                "module": record.name,
                "event": event,
                "message": record.getMessage(),
                "vm_name": "",
                "server_ip": "",
            }).encode()
            req = urllib.request.Request(
                f"{settings.LOG_SERVER_URL}/logs",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=2)
        except Exception:
            pass  # 로그 서버 장애가 서비스에 영향을 주지 않도록 무시


# ── 로깅 설정 ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

if settings.LOG_SERVER_URL:
    _log_handler = LogServerHandler()
    _log_handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(_log_handler)

app = FastAPI(
    title="FWS Backend",
    description="VMware vSphere 기반 VM 온디맨드 프로비저닝 API",
    version="1.0.0",
)

# ── CORS ────────────────────────────────────────────────────────────────────
# 프론트엔드(192.168.11.x)에서 호출 가능하도록 설정
# CORS_ORIGINS 환경변수로 특정 IP만 허용 가능 (기본: 전체 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 라우터 등록 ──────────────────────────────────────────────────────────────
app.include_router(vm.router, prefix="/api", tags=["VM"])
app.include_router(resources.router, prefix="/api", tags=["Resources"])


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "mock_mode": settings.MOCK_MODE,
        "vcenter": settings.VCENTER_HOST,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
