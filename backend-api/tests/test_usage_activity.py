import asyncio

from app.services.model_usage_service import (
    current_day_key,
    day_label,
    get_usage_activity,
    record_daily_activity,
    record_provider_usage,
)


class _FakeCollection:
    def __init__(self):
        self.docs: dict[str, dict] = {}

    async def update_one(self, query, update, upsert=False):
        doc_id = query["_id"]
        doc = self.docs.get(doc_id, {"_id": doc_id})
        if "$inc" in update:
            for key, value in update["$inc"].items():
                doc[key] = int(doc.get(key) or 0) + value
        if "$set" in update:
            doc.update(update["$set"])
        self.docs[doc_id] = doc

    async def find_one(self, query):
        return self.docs.get(query["_id"])

    def find(self):
        return self

    def sort(self, *args, **kwargs):
        return self

    async def __aiter__(self):
        return
        yield  # pragma: no cover


class _FakeDb:
    def __init__(self):
        self.modelUsageCounters = _FakeCollection()
        self.usageLimits = _FakeCollection()
        self.aiProviders = _FakeCollection()


def test_record_daily_activity_increments():
    db = _FakeDb()

    async def run():
        await record_daily_activity(db, requests=2, tokens=500)
        doc_id = f"daily:global:{current_day_key()}"
        return await db.modelUsageCounters.find_one({"_id": doc_id})

    doc = asyncio.run(run())
    assert doc["requests"] == 2
    assert doc["tokens"] == 500


def test_record_provider_usage_also_records_daily():
    db = _FakeDb()

    async def run():
        await record_provider_usage(
            db,
            provider_id="507f1f77bcf86cd799439011",
            tokens=120,
            requests=1,
        )
        return await db.modelUsageCounters.find_one(
            {"_id": f"daily:global:{current_day_key()}"}
        )

    day_doc = asyncio.run(run())
    assert day_doc["requests"] == 1
    assert day_doc["tokens"] == 120


def test_get_usage_activity_fills_days():
    db = _FakeDb()

    async def run():
        await record_daily_activity(db, requests=3, tokens=90)
        return await get_usage_activity(db, days=7)

    result = asyncio.run(run())
    assert result.days == 7
    assert len(result.series) == 7
    today = result.series[-1]
    assert today.requests == 3
    assert today.tokens == 90
    assert today.label == day_label(today.date)
