import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.database import get_db, get_all_settings
from app.checker import check_domain
from app.notifier import send_notification

logger = logging.getLogger("domee.scheduler")

scheduler = AsyncIOScheduler()


async def poll_domains():
    """Check all watched domains and send notifications for available ones."""
    settings = await get_all_settings()
    db = await get_db()

    try:
        cursor = await db.execute("SELECT id, name, status FROM domains")
        domains = await cursor.fetchall()

        if not domains:
            return

        logger.info(f"Polling {len(domains)} domains...")

        for domain in domains:
            try:
                result = await asyncio.to_thread(check_domain, domain["name"])
                now = datetime.now(timezone.utc).isoformat()

                new_status = "available" if result.available else "registered"

                await db.execute(
                    "UPDATE domains SET status = ?, expiry_date = ?, last_checked = ? WHERE id = ?",
                    (new_status, result.expiry_date, now, domain["id"]),
                )
                await db.commit()

                # Send notification if domain became available
                if result.available and domain["status"] != "available":
                    notification_email = settings.get("notification_email", "")
                    smtp_host = settings.get("smtp_host", "")

                    if notification_email and smtp_host:
                        try:
                            await send_notification(
                                domain_name=domain["name"],
                                smtp_host=smtp_host,
                                smtp_port=int(settings.get("smtp_port", "587")),
                                smtp_username=settings.get("smtp_username", ""),
                                smtp_password=settings.get("smtp_password", ""),
                                smtp_use_tls=settings.get("smtp_use_tls", "true") == "true",
                                smtp_from_email=settings.get("smtp_from_email", ""),
                                notification_email=notification_email,
                            )
                            logger.info(f"Notification sent for {domain['name']}")
                        except Exception as e:
                            logger.error(f"Failed to send notification for {domain['name']}: {e}")

            except Exception as e:
                logger.error(f"Error checking {domain['name']}: {e}")

    finally:
        await db.close()


def start_scheduler(interval_minutes: int = 60):
    """Start the background scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)

    scheduler.add_job(
        poll_domains,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="poll_domains",
        replace_existing=True,
        next_run_time=None,  # Don't run immediately on start
    )

    if not scheduler.running:
        scheduler.start()

    logger.info(f"Scheduler started with {interval_minutes}min interval")


def reschedule(interval_minutes: int):
    """Update the polling interval."""
    scheduler.reschedule_job(
        "poll_domains",
        trigger=IntervalTrigger(minutes=interval_minutes),
    )
    logger.info(f"Scheduler rescheduled to {interval_minutes}min interval")
