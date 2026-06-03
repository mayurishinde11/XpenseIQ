# main.py
# This is the entry point of our entire backend application.
# When you start the server, this file runs first.
# It creates the FastAPI app and registers all the routes.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create the FastAPI application instance
# title, description, version show up in the auto-generated API docs
app = FastAPI(
    title="XpenseIQ API",
    description="AI-powered Smart Expense Bill Scanner",
    version="1.0.0"
)

# CORS middleware allows our Streamlit frontend to talk to this backend
# Without this, the browser blocks requests between different ports
# allow_origins=["*"] means any frontend can talk to this backend
# In production we would replace "*" with our actual frontend URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root route - when someone visits http://localhost:8000
# this function runs and returns a JSON response
@app.get("/")
def root():
    return {
        "message": "XpenseIQ API is running",
        "version": "1.0.0",
        "status": "healthy"
    }

# Health check route - standard in every production system
# Monitoring tools ping this route to check if the server is alive
# If it returns 200, the server is healthy
@app.get("/health")
def health_check():
    return {"status": "ok"}