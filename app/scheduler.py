import asyncio
import logging
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.database import get_db, get_all_settings
from app.checker import check_domain
from app.notifier import send_notification

logger = logging.getLogger("domee.scheduler")

scheduler = AsyncIOScheduler()


def should_check_domain(expiry_date: str | None, last_checked: str | None, polling_interval: int) -> bool:
    """Determine if a domain needs checking based on expiry proximity.

    Polling frequency scales with how close the expiry date is:
    - No expiry / already available: check at normal polling interval
    - Expires in <7 days: check at normal polling interval
    - Expires in 7-30 days: check every 6 hours (min)
    - Expires in 30-90 days: check every 24 hours (min)
    - Expires in 90-365 days: check every 7 days (min)
    - Expires in >1 year: check every 30 days (min)
    """
    if not expiry_date:
        return _enough_time_passed(last_checked, polling_interval)

    try:
        expiry = datetime.strptime(expiry_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return _enough_time_passed(last_checked, polling_interval)

    now = datetime.now(timezone.utc)
    days_until = (expiry - now).days

    if days_until < 7:
        min_interval = polling_interval
    elif days_until < 30:
        min_interval = max(polling_interval, 360)
    elif days_until < 90:
        min_interval = max(polling_interval, 1440)
    elif days_until < 365:
        min_interval = max(polling_interval, 10080)
    else:
        min_interval = max(polling_interval, 43200)

    return _enough_time_passed(last_checked, min_interval)


def _enough_time_passed(last_checked: str | None, interval_minutes: int) -> bool:
    if not last_checked:
        return True
    try:
        last = datetime.fromisoformat(last_checked)
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - last >= timedelta(minutes=interval_minutes)
    except (ValueError, TypeError):
        return True


async def poll_domains():
    """Check all watched domains and send notifications for available ones."""
    settings = await get_all_settings()
    polling_interval = int(settings.get("polling_interval", "60"))
    db = await get_db()

    try:
        cursor = await db.execute("SELECT id, name, status, expiry_date, last_checked FROM domains")
        domains = await cursor.fetchall()

        if not domains:
            return

        to_check = [d for d in domains if should_check_domain(d["expiry_date"], d["last_checked"], polling_interval)]
        logger.info(f"Polling {len(to_check)}/{len(domains)} domains (others skipped — expiry too far out)")

        for domain in to_check:
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
        next_run_time=None,
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
