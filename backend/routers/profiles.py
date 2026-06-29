from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import re
from database import get_profiles, set_profile
import database

router = APIRouter()

class ProfileSwitchReq(BaseModel):
    name: str
    difficulty: str | None = None  # only honored when the profile is brand new — see database.set_profile

@router.get("/")
def list_profiles():
    return {"profiles": get_profiles(), "active": database.ACTIVE_PROFILE}

@router.post("/switch")
def switch_profile(req: ProfileSwitchReq):
    # sanitize name
    name = re.sub(r'[^a-zA-Z0-9_]', '', req.name)
    if not name:
        raise HTTPException(status_code=400, detail="Invalid profile name")

    set_profile(name, difficulty=req.difficulty)
    
    # After switching DBs, we must heal the portrait cache so the new profile 
    # claims the shared pool of pre-generated portraits, and queue up any 
    # pending LLM/generation jobs that belong to this profile.
    from services.portrait_cache import cleanup_portraits, reconcile_pending_portraits
    from routers.gacha import reconcile_pending_profiles
    cleanup_portraits()
    reconcile_pending_portraits()
    reconcile_pending_profiles()
    
    return {"ok": True, "active": name}

class ProfileRenameReq(BaseModel):
    old_name: str
    new_name: str

@router.post("/rename")
def rename_profile(req: ProfileRenameReq):
    import os
    import shutil
    from database import db
    old_name = re.sub(r'[^a-zA-Z0-9_]', '', req.old_name)
    new_name = re.sub(r'[^a-zA-Z0-9_]', '', req.new_name)
    if not old_name or not new_name:
        raise HTTPException(status_code=400, detail="Invalid profile names")
        
    old_path = os.path.join(database.SAVES_DIR, f"{old_name}.db")
    new_path = os.path.join(database.SAVES_DIR, f"{new_name}.db")
    
    if not os.path.exists(old_path):
        raise HTTPException(status_code=404, detail="Profile not found")
    if os.path.exists(new_path):
        raise HTTPException(status_code=400, detail="Profile with new name already exists")
        
    os.rename(old_path, new_path)
    
    # Rename portrait directory
    old_portraits = f"static/portraits/{old_name}"
    new_portraits = f"static/portraits/{new_name}"
    if os.path.exists(old_portraits):
        os.rename(old_portraits, new_portraits)
        
    # Update paths in database
    import sqlite3
    conn = sqlite3.connect(new_path)
    conn.execute("UPDATE heroes SET portrait_path = REPLACE(portrait_path, ?, ?) WHERE portrait_path IS NOT NULL", (f"static/portraits/{old_name}/", f"static/portraits/{new_name}/"))
    conn.commit()
    conn.close()
    
    if database.ACTIVE_PROFILE == old_name:
        set_profile(new_name)
    return {"ok": True}

class ProfileDeleteReq(BaseModel):
    name: str

@router.post("/delete")
def delete_profile(req: ProfileDeleteReq):
    import os
    import shutil
    name = re.sub(r'[^a-zA-Z0-9_]', '', req.name)
    if not name:
        raise HTTPException(status_code=400, detail="Invalid profile name")
        
    path = os.path.join(database.SAVES_DIR, f"{name}.db")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Profile not found")
        
    try:
        os.remove(path)
        if os.path.exists(path + "-wal"):
            os.remove(path + "-wal")
        if os.path.exists(path + "-shm"):
            os.remove(path + "-shm")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete profile: {e}")
    
    portraits_dir = f"static/portraits/{name}"
    if os.path.exists(portraits_dir):
        shutil.rmtree(portraits_dir)
        
    if database.ACTIVE_PROFILE == name:
        database.clear_active_profile()
    return {"ok": True}
