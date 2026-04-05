from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.routes.summoner import router as summoner_router
from src.routes.matches import router as matches_router
from src.routes.champion import router as champion_router
from src.routes.match import router as match_router

app = FastAPI(
    title="LoL Galaxy — Riot API Service",
    description="Microservice centralisé pour tous les appels Riot Games API de l'écosystème LoL Galaxy.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(summoner_router)
app.include_router(matches_router)
app.include_router(champion_router)
app.include_router(match_router)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "service": "riot-api-service"}
