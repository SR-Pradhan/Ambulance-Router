from fastapi import FastAPI
from app.api import route

app = FastAPI(title="Ambulance Route Optimizer")

app.include_router(route.router)

@app.get("/")
def root():
    return {"status": "running"}