import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database import Base, get_db

TEST_DB_URL = "sqlite+aiosqlite:///./test_broken.db"
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


class TestBrokenSamples:
    """
    Test Case Name: AI Self-Healing Demo — Broken Tests
    Module: Task Manager - Sample Failures
    Description: Intentionally broken tests to demonstrate the AI self-healing pipeline.
    Expected Output: AI agent detects bug type (TEST_BUG), fixes assertion/code, re-runs to PASS.
    """

    @pytest.mark.asyncio
    @pytest.mark.testid("TC-001")
    async def test_create_user_wrong_status_code(self, client):
        """
        Test Case Name: Demo - User Status Code Check
        Module: Task Manager - Sample Failures
        Description: Intentionally broken test asserting status code 200 instead of 201 for creation.
        Steps: POST a user payload and assert response status code is 201 (initially 200).
        Expected Output: Response returns 201.
        """
        resp = await client.post("/api/users/", json={
            "email": "bug1@test.com",
            "name": "Bug User One"
        })
        assert resp.status_code == 201  # Fixed expected status code

    @pytest.mark.asyncio
    @pytest.mark.testid("TC-002")
    async def test_task_default_status_wrong_assertion(self, client):
        """
        Test Case Name: Demo - Task Default Status Check
        Module: Task Manager - Sample Failures
        Description: Intentionally broken test asserting status 'pending' instead of 'todo' for task defaults.
        Steps: Create user, project, and task. Assert task status is 'todo' (initially 'pending').
        Expected Output: Created task defaults to status 'todo'.
        """
        # Setup
        user = await client.post("/api/users/", json={"email": "bug2@test.com", "name": "Bug User 2"})
        user_id = user.json()["id"]
        project = await client.post("/api/projects/", json={"name": "Bug Project", "owner_id": user_id})
        project_id = project.json()["id"]

        resp = await client.post("/api/tasks/", json={
            "title": "Test task",
            "project_id": project_id,
        })
        assert resp.status_code == 201
        assert resp.json()["status"] == "todo"  # Fixed expected default status

    @pytest.mark.asyncio
    @pytest.mark.testid("TC-003")
    async def test_list_users_wrong_count(self, client):
        """
        Test Case Name: Demo - User Count Check
        Module: Task Manager - Sample Failures
        Description: Intentionally broken test asserting count is 5 instead of 3.
        Steps: Create 3 users and assert total count returned from API is 3 (initially 5).
        Expected Output: Returned users list length matches 3.
        """
        for i in range(3):
            await client.post("/api/users/", json={"email": f"count{i}@test.com", "name": f"User {i}"})

        resp = await client.get("/api/users/")
        assert resp.status_code == 200
        assert len(resp.json()) == 3  # Fixed expected user count

    @pytest.mark.asyncio
    @pytest.mark.testid("TC-004")
    async def test_health_wrong_field(self, client):
        """
        Test Case Name: Demo - Health Check Field Check
        Module: Task Manager - Sample Failures
        Description: Intentionally broken test accessing missing field 'health' instead of 'status'.
        Steps: Call /health endpoint and assert 'status' is 'ok' (initially key checked was 'health').
        Expected Output: Response JSON contains key 'status' with value 'ok'.
        """
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"  # Fixed field name
