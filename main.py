import warnings

from fastapi import FastAPI

from whatsapp.webhook.route import router as webhook_router

warnings.filterwarnings("ignore", category=DeprecationWarning)

app = FastAPI()
app.include_router(webhook_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
