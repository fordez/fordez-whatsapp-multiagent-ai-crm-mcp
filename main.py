import warnings

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from whatsapp.webhook.route import router as webhook_router

warnings.filterwarnings("ignore", category=DeprecationWarning)

app = FastAPI()

# ✅ AGREGAR CORS ANTES DE LOS ROUTERS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
    ],  # En producción: ["https://www.facebook.com", "https://graph.facebook.com"]
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Registrar routers después del middleware
app.include_router(webhook_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
    )
