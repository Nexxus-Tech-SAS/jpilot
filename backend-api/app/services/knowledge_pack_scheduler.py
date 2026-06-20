"""Scheduled Knowledge Pack sync from Stack Calibration Studio."""

from __future__ import annotations

import asyncio
import logging

from app.config import settings
from app.database import get_database
from app.services.calibration_sync_service import CalibrationSyncError, sync_calibrations_from_studio
from app.services.knowledge_pack_service import DEFAULT_SYNC_SCHEDULE_HOURS, get_knowledge_pack_state

logger = logging.getLogger(__name__)


async def run_startup_knowledge_pack_sync() -> None:
    if not settings.calibration_sync_enabled or not settings.knowledge_pack_enabled:
        return
    db = get_database()
    state = await get_knowledge_pack_state(db)
    if not state.get("syncScheduleEnabled", True):
        logger.info("Startup knowledge pack sync disabled in schedule settings.")
        return
    try:
        result = await sync_calibrations_from_studio(db)
        logger.info(
            "Startup knowledge pack sync complete (pack_updated=%s pack_skipped=%s skills_updated=%d).",
            result.knowledge_pack_updated,
            result.knowledge_pack_skipped,
            result.updated,
        )
    except CalibrationSyncError as exc:
        logger.warning("Startup knowledge pack sync skipped: %s", exc)
    except Exception:
        logger.exception("Startup knowledge pack sync failed")


async def periodic_knowledge_pack_sync(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        db = get_database()
        state = await get_knowledge_pack_state(db)
        hours = int(state.get("syncScheduleHours") or DEFAULT_SYNC_SCHEDULE_HOURS)
        interval = max(3600, hours * 3600)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass
        if stop_event.is_set():
            break
        if not settings.calibration_sync_enabled or not settings.knowledge_pack_enabled:
            continue
        if not state.get("syncScheduleEnabled", True):
            continue
        try:
            result = await sync_calibrations_from_studio(db)
            logger.info(
                "Scheduled knowledge pack sync complete (pack_updated=%s pack_skipped=%s skills_updated=%d).",
                result.knowledge_pack_updated,
                result.knowledge_pack_skipped,
                result.updated,
            )
        except CalibrationSyncError as exc:
            logger.warning("Scheduled knowledge pack sync skipped: %s", exc)
        except Exception:
            logger.exception("Scheduled knowledge pack sync failed")
