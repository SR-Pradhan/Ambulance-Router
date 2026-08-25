from fastapi import FastAPI
from app.api import route, hospitals, requests

app = FastAPI(title="Ambulance Route Optimizer")

app.include_router(route.router)
app.include_router(hospitals.router)
app.include_router(requests.router)

@app.get("/")
def root():
    return {"status": "running"}