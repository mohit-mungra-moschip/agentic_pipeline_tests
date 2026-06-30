"""
tests/integration/test_complex_task_hierarchy.py — Complex business validation tests for self-referential tasks.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from datetime import datetime, timedelta, timezone

from app.main import app
from app.database import Base, get_db

# ── Test database setup ───────────────────────────────────────────────────────
TEST_DB_URL = "sqlite+aiosqlite:///./test_complex.db"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture(autouse=True, scope="function")
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ── Helpers ───────────────────────────────────────────────────────────────────

async def create_test_user(client: AsyncClient, email="test@example.com", name="Test User"):
    resp = await client.post("/api/users/", json={"email": email, "name": name})
    assert resp.status_code == 201
    return resp.json()


async def create_test_project(client: AsyncClient, owner_id: int, name="Test Project"):
    resp = await client.post("/api/projects/", json={"name": name, "owner_id": owner_id})
    assert resp.status_code == 201
    return resp.json()


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestComplexTaskHierarchy:
    """
    Test Case Name: Complex Task Hierarchy & Business Logic Tests
    Module: Task Manager - Integration
    """

    @pytest.mark.asyncio
    @pytest.mark.testid("TC-101")
    async def test_subtask_creation_valid(self, client):
        user = await create_test_user(client)
        project = await create_test_project(client, user["id"])
        
        # Create parent task
        p_resp = await client.post("/api/tasks/", json={
            "title": "Parent task",
            "project_id": project["id"]
        })
        assert p_resp.status_code == 201
        parent = p_resp.json()
        
        # Create subtask
        c_resp = await client.post("/api/tasks/", json={
            "title": "Subtask",
            "project_id": project["id"],
            "parent_id": parent["id"]
        })
        assert c_resp.status_code == 201
        child = c_resp.json()
        assert child["parent_id"] == parent["id"]

    @pytest.mark.asyncio
    @pytest.mark.testid("TC-102")
    async def test_subtask_different_project_failure(self, client):
        user = await create_test_user(client)
        p1 = await create_test_project(client, user["id"], "Proj 1")
        p2 = await create_test_project(client, user["id"], "Proj 2")
        
        # Create parent task in Proj 1
        p_resp = await client.post("/api/tasks/", json={
            "title": "Parent task in Proj 1",
            "project_id": p1["id"]
        })
        assert p_resp.status_code == 201
        parent = p_resp.json()
        
        # Try to create child in Proj 2 linked to parent in Proj 1 -> should fail
        c_resp = await client.post("/api/tasks/", json={
            "title": "Subtask in Proj 2",
            "project_id": p2["id"],
            "parent_id": parent["id"]
        })
        assert c_resp.status_code == 400
        assert "same project" in c_resp.json()["detail"]

    @pytest.mark.asyncio
    @pytest.mark.testid("TC-103")
    async def test_subtask_due_date_validation(self, client):
        user = await create_test_user(client)
        project = await create_test_project(client, user["id"])
        
        due_parent = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        due_child_invalid = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        
        # Create parent task with due date (2 days from now)
        p_resp = await client.post("/api/tasks/", json={
            "title": "Parent task",
            "project_id": project["id"],
            "due_date": due_parent
        })
        assert p_resp.status_code == 201
        parent = p_resp.json()
        
        # Try to create child with due date 3 days from now -> should fail
        c_resp = await client.post("/api/tasks/", json={
            "title": "Subtask with invalid due date",
            "project_id": project["id"],
            "parent_id": parent["id"],
            "due_date": due_child_invalid
        })
        assert c_resp.status_code == 400
        assert "due date" in c_resp.json()["detail"]

    @pytest.mark.asyncio
    @pytest.mark.testid("TC-104")
    async def test_circular_dependency_self(self, client):
        user = await create_test_user(client)
        project = await create_test_project(client, user["id"])
        
        # Create a task
        resp = await client.post("/api/tasks/", json={
            "title": "Task A",
            "project_id": project["id"]
        })
        assert resp.status_code == 201
        task = resp.json()
        
        # Try to update parent to self -> should fail
        update_resp = await client.put(f"/api/tasks/{task['id']}", json={
            "parent_id": task["id"]
        })
        assert update_resp.status_code == 400
        assert "cannot be its own parent" in update_resp.json()["detail"]

    @pytest.mark.asyncio
    @pytest.mark.testid("TC-105")
    async def test_circular_dependency_cycle(self, client):
        user = await create_test_user(client)
        project = await create_test_project(client, user["id"])
        
        # Task A
        a_resp = await client.post("/api/tasks/", json={"title": "Task A", "project_id": project["id"]})
        task_a = a_resp.json()
        
        # Task B (parent is A)
        b_resp = await client.post("/api/tasks/", json={
            "title": "Task B",
            "project_id": project["id"],
            "parent_id": task_a["id"]
        })
        task_b = b_resp.json()
        
        # Try to update Task A's parent to Task B (A -> B -> A cycle) -> should fail
        update_resp = await client.put(f"/api/tasks/{task_a['id']}", json={
            "parent_id": task_b["id"]
        })
        assert update_resp.status_code == 400
        assert "cycle detected" in update_resp.json()["detail"]

    @pytest.mark.asyncio
    @pytest.mark.testid("TC-106")
    async def test_parent_completion_blocked_by_open_subtask(self, client):
        user = await create_test_user(client)
        project = await create_test_project(client, user["id"])
        
        # Create parent task
        p_resp = await client.post("/api/tasks/", json={"title": "Parent task", "project_id": project["id"]})
        parent = p_resp.json()
        
        # Create subtask (default status in_progress / todo)
        await client.post("/api/tasks/", json={
            "title": "Open subtask",
            "project_id": project["id"],
            "parent_id": parent["id"]
        })
        
        # Try to mark parent as DONE -> should fail
        done_resp = await client.put(f"/api/tasks/{parent['id']}", json={
            "status": "done"
        })
        assert done_resp.status_code == 400
        assert "subtasks are still open" in done_resp.json()["detail"]

    @pytest.mark.asyncio
    @pytest.mark.testid("TC-107")
    async def test_parent_cancellation_cascades(self, client):
        user = await create_test_user(client)
        project = await create_test_project(client, user["id"])
        
        # Create parent task
        p_resp = await client.post("/api/tasks/", json={"title": "Parent task", "project_id": project["id"]})
        parent = p_resp.json()
        
        # Create open subtask
        c_resp = await client.post("/api/tasks/", json={
            "title": "Open subtask",
            "project_id": project["id"],
            "parent_id": parent["id"]
        })
        child = c_resp.json()
        
        # Cancel parent
        cancel_resp = await client.put(f"/api/tasks/{parent['id']}", json={
            "status": "cancelled"
        })
        assert cancel_resp.status_code == 200
        
        # Verify subtask is also cancelled
        child_get = await client.get(f"/api/tasks/{child['id']}")
        assert child_get.json()["status"] == "cancelled"
