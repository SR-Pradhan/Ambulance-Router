import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import route, hospitals, requests, ambulances, admin

app = FastAPI(title="Ambulance Route Optimizer")

# Browsers block a page on one origin from calling an API on another unless the
# API says it is allowed. The React dev server runs on a different port to this
# API, so without this every frontend fetch fails with a CORS error -- and the
# browser reports it as a network failure, which is misleading to debug.
#
# These are DEV origins (Vite's default 5173, CRA's 3000). A deployed app would
# list its real domain instead of localhost, and would not use "*".
# Extra origins come from the environment, comma separated, so the deployed
# frontend's domain can be added without a code change. Local dev ports stay in
# the list so nothing breaks when running locally.
_extra = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",")
          if o.strip()]

ALLOWED_ORIGINS = _extra + [
    # 5174 is this project's Vite port (5173 was already taken on this machine).
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(route.router)
app.include_router(hospitals.router)
app.include_router(requests.router)
app.include_router(ambulances.router)
app.include_router(admin.router)


@app.get("/")
def root():
    return {"status": "running"}
