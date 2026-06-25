from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os
import threading
import time

env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

from database import init_db, db
from routers import heroes, gacha, tower, base, runs, equipment, profiles, chat, relics, crafting, arena

init_db()

app = FastAPI(title="Tower of Eternity Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("static/portraits", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

def _reconcile_loop():
    """reconcile_pending_profiles() only ran once, at startup — a hero whose
    LLM enrichment thread dies mid-flight *after* that point (a transient
    Gemini outage, rate limit, etc.) was stuck on a placeholder identity for
    the rest of the session with nothing to retry it. Re-run the same scan
    periodically instead so it self-heals without needing a backend restart."""
    from routers.gacha import reconcile_pending_profiles
    while True:
        time.sleep(300)
        try:
            reconcile_pending_profiles()
        except Exception as e:
            print(f"[Reconcile] Periodic profile reconciliation failed: {e}")

@app.on_event("startup")
async def startup():
    init_db()
    from services.portrait_cache import cleanup_portraits, start_cache_worker, reconcile_pending_portraits, queue_missing_enemy_portraits, queue_missing_boss_portraits, queue_missing_family_portraits
    cleanup_portraits()
    start_cache_worker()
    reconcile_pending_portraits()
    queue_missing_enemy_portraits()
    queue_missing_boss_portraits()
    queue_missing_family_portraits()
    from services.chat_service import start_chat_worker
    start_chat_worker()
    from routers.gacha import reconcile_pending_profiles
    reconcile_pending_profiles()
    threading.Thread(target=_reconcile_loop, daemon=True).start()
    print("Portrait and Chat workers started.")


app.include_router(heroes.router, prefix="/heroes", tags=["heroes"])
app.include_router(gacha.router, prefix="/gacha", tags=["gacha"])
app.include_router(tower.router, prefix="/tower", tags=["Tower"])
app.include_router(base.router, prefix="/base", tags=["Base"])
app.include_router(runs.router, prefix="/runs", tags=["Runs"])
app.include_router(equipment.router, prefix="/equipment", tags=["Equipment"])
app.include_router(relics.router, prefix="/relics", tags=["Relics"])
app.include_router(profiles.router, prefix="/profiles", tags=["Profiles"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(crafting.router, prefix="/forge", tags=["Forge"])
app.include_router(arena.router, prefix="/arena", tags=["Arena"])


@app.get("/portrait-cache/status")
def cache_status():
    from services.portrait_cache import get_cache_counts
    counts = get_cache_counts()
    total = sum(counts.values())
    return {"counts_by_star": counts, "total_available": total}

@app.post("/portrait-cache/cleanup")
def cache_cleanup():
    """Manually trigger portrait cleanup — removes orphaned files and clears cache pool."""
    from services.portrait_cache import cleanup_portraits
    cleanup_portraits()
    return {"ok": True, "message": "Portrait cache cleaned. Orphaned files removed. Cache worker will regenerate fresh portraits."}

@app.post("/portrait-cache/regenerate")
def cache_regenerate():
    """Delete ALL cached portraits (not hero-owned) and regenerate from scratch with new diverse prompts."""
    import os, json
    from services.portrait_cache import cleanup_portraits, get_cache_counts

    portrait_dir = "static/portraits"
    with db() as conn:
        # Get hero-owned portrait filenames
        rows = conn.execute("SELECT portrait_path FROM heroes WHERE portrait_path IS NOT NULL").fetchall()
        owned = {os.path.basename(r["portrait_path"]) for r in rows}
        # Clear entire cache pool
        conn.execute("DELETE FROM portrait_cache")

    # Delete all non-owned portrait files in subdirectories
    deleted = 0
    for subdir in ["main", "cached"]:
        dir_path = os.path.join(portrait_dir, subdir)
        if os.path.isdir(dir_path):
            for fname in os.listdir(dir_path):
                if fname.endswith(".png") and fname not in owned and not fname.startswith("default_"):
                    try:
                        os.remove(os.path.join(dir_path, fname))
                        deleted += 1
                    except Exception:
                        pass

    return {
        "ok": True,
        "deleted": deleted,
        "kept_hero_portraits": len(owned),
        "message": f"Deleted {deleted} cached portraits. Cache worker will regenerate with new diversity system."
    }

frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(os.path.join(frontend_dist, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

@app.get("/{catchall:path}")
def serve_react_app(catchall: str):
    file_path = os.path.join(frontend_dist, catchall)
    if catchall and os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    index_path = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "Frontend not built. Run 'npm run build' in frontend directory."}
