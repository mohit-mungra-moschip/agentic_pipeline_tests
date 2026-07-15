"""
tests/integration/test_api_tasks.py — Integration tests for Task API endpoints.
Uses httpx AsyncClient against the real FastAPI app (in-memory SQLite for speed).

Test Case Name: Task API Integration Tests
Module: Task Manager - Integration
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database import Base, get_db


# ── Test database setup ───────────────────────────────────────────────────────
TEST_DB_URL = "sqlite+aiosqlite:///./test_tasks.db"

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

class TestTaskAPI:
    """
    Test Case Name: Task CRUD API Tests
    Module: Task Manager - Integration
    Description: Full integration tests for the Task REST API.
    Steps:
        1. Create user and project as prerequisites
        2. POST /api/tasks/ to create a task
        3. GET /api/tasks/{id} to retrieve
        4. PUT /api/tasks/{id} to update status
        5. DELETE /api/tasks/{id} to remove
    Expected Output: All CRUD operations return correct status codes and data.
    """

    @pytest.mark.asyncio
    @pytest.mark.testid("TC-044")
    async def test_create_task(self, client):
        """
        Test Case Name: API Create Task
        Module: Task Manager - Integration
        Description: Verify successful creation of a task via POST /api/tasks/.
        Steps:
            1. Create a user and a project.
            2. POST new task under that project.
        Expected Output: Response 201 Created containing task details.
        """
        user = await create_test_user(client)
        project = await create_test_project(client, user["id"])

        resp = await client.post("/api/tasks/", json={
            "title": "Write unit tests",
            "project_id": project["id"],
            "priority": "high"
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Write unit tests"
        assert data["status"] == "todo"
        assert data["priority"] == "high"

    @pytest.mark.asyncio
    @pytest.mark.testid("TC-006")
    async def test_get_task(self, client):
        """
        Test Case Name: API Get Task By ID
        Module: Task Manager - Integration
        Description: Verify retrieving a specific task by its unique ID.
        Steps:
            1. Create user, project, and task.
            2. Send GET request for task ID.
        Expected Output: Response 200 OK containing corresponding task data.
        """
        user = await create_test_user(client)
        project = await create_test_project(client, user["id"])

        create_resp = await client.post("/api/tasks/", json={
            "title": "Fetch this task",
            "project_id": project["id"],
        })
        task_id = create_resp.json()["id"]

        resp = await client.get(f"/api/tasks/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == task_id

    @pytest.mark.asyncio
    @pytest.mark.testid("TC-007")
    async def test_update_task_status(self, client):
        """
        Test Case Name: API Update Task Status
        Module: Task Manager - Integration
        Description: Verify updating task status via PUT /api/tasks/{id}.
        Steps:
            1. Create prerequisite user, project, and task.
            2. PUT status update of 'done'.
        Expected Output: Response 200 OK and task status becomes 'done'.
        """
        user = await create_test_user(client)
        project = await create_test_project(client, user["id"])

        create_resp = await client.post("/api/tasks/", json={
            "title": "Task to update",
            "project_id": project["id"],
        })
        task_id = create_resp.json()["id"]

        resp = await client.put(f"/api/tasks/{task_id}", json={"status": "done"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "done"

    @pytest.mark.asyncio
    @pytest.mark.testid("TC-008")
    async def test_delete_task(self, client):
        """
        Test Case Name: API Delete Task
        Module: Task Manager - Integration
        Description: Verify task deletion via DELETE /api/tasks/{id} and check retrieval.
        Steps:
            1. Create task.
            2. Send DELETE request.
            3. Verify subsequent GET request returns 404.
        Expected Output: DELETE returns 204, GET returns 404.
        """
        user = await create_test_user(client)
        project = await create_test_project(client, user["id"])

        create_resp = await client.post("/api/tasks/", json={
            "title": "Delete me",
            "project_id": project["id"],
        })
        task_id = create_resp.json()["id"]

        del_resp = await client.delete(f"/api/tasks/{task_id}")
        assert del_resp.status_code == 204

        get_resp = await client.get(f"/api/tasks/{task_id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.testid("TC-009")
    async def test_list_tasks_filter_by_project(self, client):
        """
        Test Case Name: API List Tasks Filtered By Project
        Module: Task Manager - Integration
        Description: Verify listing tasks filtered by project ID.
        Steps:
            1. Create 3 tasks under project.
            2. Send GET /api/tasks/?project_id={id}.
        Expected Output: Response 200 OK containing exactly 3 tasks.
        """
        user = await create_test_user(client)
        project = await create_test_project(client, user["id"])

        for title in ["Task A", "Task B", "Task C"]:
            await client.post("/api/tasks/", json={"title": title, "project_id": project["id"]})

        resp = await client.get(f"/api/tasks/?project_id={project['id']}")
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    @pytest.mark.asyncio
    @pytest.mark.testid("TC-010")
    async def test_create_task_invalid_project(self, client):
        """
        Test Case Name: API Create Task Invalid Project
        Module: Task Manager - Integration
        Description: Verify task creation fails when specifying invalid project.
        Steps: POST task with project_id = 99999.
        Expected Output: Response 404 Not Found.
        """
        resp = await client.post("/api/tasks/", json={
            "title": "Orphan task",
            "project_id": 99999,
        })
        assert resp.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.testid("TC-011")
    async def test_get_nonexistent_task(self, client):
        """
        Test Case Name: API Get Non-Existent Task
        Module: Task Manager - Integration
        Description: Verify GET for missing task ID returns 404.
        Steps: Send GET request for task ID 99999.
        Expected Output: Response 404 Not Found.
        """
        resp = await client.get("/api/tasks/99999")
        assert resp.status_code == 404
