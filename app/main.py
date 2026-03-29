import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.database import init_db, get_db, get_all_settings, update_settings
from app.checker import check_domain
from app.scheduler import start_scheduler, reschedule

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("domee")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    settings = await get_all_settings()
    interval = int(settings.get("polling_interval", "60"))
    start_scheduler(interval)
    logger.info("Domee started")
    yield
    logger.info("Domee shutting down")


app = FastAPI(title="Domee", version="1.0.0", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")


# --- Models ---


class DomainAdd(BaseModel):
    name: str


class DomainCheck(BaseModel):
    name: str


class SettingsUpdate(BaseModel):
    polling_interval: str | None = None
    notification_email: str | None = None
    smtp_host: str | None = None
    smtp_port: str | None = None
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: str | None = None
    smtp_from_email: str | None = None


# --- Routes ---


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.get("/api/domains")
async def list_domains():
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, name, expiry_date, status, last_checked, created_at FROM domains ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


@app.post("/api/domains")
async def add_domain(body: DomainAdd):
    name = body.name.strip().lower()
    if not name:
        raise HTTPException(status_code=400, detail="Domain name is required")

    # Check domain info
    result = await asyncio.to_thread(check_domain, name)

    db = await get_db()
    try:
        try:
            now = datetime.now(timezone.utc).isoformat()
            status = "available" if result.available else "registered"
            await db.execute(
                "INSERT INTO domains (name, expiry_date, status, last_checked) VALUES (?, ?, ?, ?)",
                (name, result.expiry_date, status, now),
            )
            await db.commit()
        except Exception:
            raise HTTPException(status_code=409, detail="Domain already in watchlist")

        cursor = await db.execute(
            "SELECT id, name, expiry_date, status, last_checked, created_at FROM domains WHERE name = ?",
            (name,),
        )
        row = await cursor.fetchone()
        return dict(row)
    finally:
        await db.close()


@app.delete("/api/domains/{domain_id}")
async def delete_domain(domain_id: int):
    db = await get_db()
    try:
        cursor = await db.execute("DELETE FROM domains WHERE id = ?", (domain_id,))
        await db.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Domain not found")
        return {"ok": True}
    finally:
        await db.close()


@app.post("/api/check")
async def check_domain_availability(body: DomainCheck):
    name = body.name.strip().lower()
    if not name:
        raise HTTPException(status_code=400, detail="Domain name is required")

    result = await asyncio.to_thread(check_domain, name)

    return {
        "name": result.name,
        "available": result.available,
        "expiry_date": result.expiry_date,
        "error": result.error,
    }


@app.get("/api/settings")
async def get_settings():
    settings = await get_all_settings()
    # Mask password for frontend
    if settings.get("smtp_password"):
        settings["smtp_password"] = "••••••••"
    return settings


@app.put("/api/settings")
async def update_settings_endpoint(body: SettingsUpdate):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}

    # Don't overwrite password with mask
    if updates.get("smtp_password") == "••••••••":
        del updates["smtp_password"]

    if updates:
        await update_settings(updates)

    # Reschedule if interval changed
    if "polling_interval" in updates:
        try:
            reschedule(int(updates["polling_interval"]))
        except Exception as e:
            logger.error(f"Failed to reschedule: {e}")

    return await get_all_settings()


@app.post("/api/poll")
async def trigger_poll():
    """Manually trigger a poll of all domains."""
    from app.scheduler import poll_domains

    await poll_domains()
    return {"ok": True}
