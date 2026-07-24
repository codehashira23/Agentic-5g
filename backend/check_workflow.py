"""Check latest workflow trace and service calls."""
import asyncio, sys
sys.path.insert(0, ".")

async def check():
    from app.infrastructure.config.settings import Settings
    from app.infrastructure.db.engine import Database
    from sqlalchemy import select, text
    from app.infrastructure.db.models import WorkflowRow, WorkflowTraceRow, ServiceCallRow

    cfg = Settings()
    db = Database(path=cfg.db_path)
    await db.init()

    async with db.session() as s:
        wf = (await s.execute(
            select(WorkflowRow).order_by(text("created_at DESC")).limit(1)
        )).scalar_one_or_none()

        if not wf:
            print("No workflows found")
            return

        print(f"\n=== Workflow: {wf.id} status={wf.status} stage={wf.stage} ===")
        print(f"Goal: {wf.goal}")

        traces = (await s.execute(
            select(WorkflowTraceRow)
            .where(WorkflowTraceRow.workflow_id == wf.id)
            .order_by(text("ts ASC"))
        )).scalars().all()

        print(f"\nTrace ({len(traces)} entries):")
        for t in traces:
            print(f"  [{t.stage}] {t.agent_role}: {t.rationale[:100]}")

        calls = (await s.execute(
            select(ServiceCallRow)
            .where(ServiceCallRow.correlation_id == wf.id)
        )).scalars().all()

        print(f"\nService calls ({len(calls)}):")
        for c in calls:
            print(f"  {c.service_name} → {c.status}")

    await db.close()

asyncio.run(check())
