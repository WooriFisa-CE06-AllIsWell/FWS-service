import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers import vm, resources

# ── 로깅 설정 ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

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
