# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.expense_router import router as expense_router
from routers.auth_router import router as auth_router

app = FastAPI(
    title="XpenseIQ API",
    description="AI-powered Smart Expense Bill Scanner",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register both routers
app.include_router(auth_router)
app.include_router(expense_router)

@app.get("/")
def root():
    return {
        "message": "XpenseIQ API is running",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}