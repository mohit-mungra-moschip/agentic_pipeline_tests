"""
tests/e2e/test_full_workflow.py — End-to-end workflow test.

Test Case Name: Full Project Workflow E2E Test
Module: Task Manager - E2E
Description: Tests the complete workflow of creating a project, assigning tasks,
             updating statuses, and verifying completion.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database import Base, get_db

TEST_DB_URL = "sqlite+aiosqlite:///./test_e2e.db"
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


class TestFullWorkflow:
    """
    Test Case Name: Complete Project Workflow
    Module: Task Manager - E2E
    Description: End-to-end test simulating a real sprint workflow.
    Steps:
        1. Create project manager and developer users
        2. Create a sprint project
        3. Create tasks with different priorities
        4. Assign tasks to developer
        5. Mark tasks as in_progress and then done
        6. Verify final state
    Expected Output: All steps complete successfully; final task count and statuses are correct.
    """

    @pytest.mark.asyncio
    @pytest.mark.testid("TC-005")
    async def test_complete_sprint_workflow(self, client):
        """
        Test Case Name: E2E Sprint Workflow
        Module: Task Manager - E2E
        Description: End-to-end simulation of a complete sprint workflow.
        Steps:
            1. Create manager and developer users.
            2. Create a sprint project.
            3. Create 4 tasks under project, assign to developer.
            4. Transition two tasks to in_progress.
            5. Transition all 4 tasks to done.
            6. Verify final state and project information.
        Expected Output: Users, projects, and tasks are created and transition successfully. Final task check returns 4 done tasks.
        """
        # Step 1: Create users
        pm = await client.post("/api/users/", json={"email": "pm@company.com", "name": "Project Manager"})
        assert pm.status_code == 201
        pm_id = pm.json()["id"]

        dev = await client.post("/api/users/", json={"email": "dev@company.com", "name": "Developer"})
        assert dev.status_code == 201
        dev_id = dev.json()["id"]

        # Step 2: Create project
        proj = await client.post("/api/projects/", json={
            "name": "Sprint 1 - Auth Module",
            "description": "User authentication features",
            "owner_id": pm_id
        })
        assert proj.status_code == 201
        proj_id = proj.json()["id"]

        # Step 3: Create tasks
        tasks_data = [
            {"title": "Design DB schema", "priority": "high"},
            {"title": "Implement login endpoint", "priority": "critical"},
            {"title": "Add JWT token support", "priority": "high"},
            {"title": "Write auth tests", "priority": "medium"},
        ]
        task_ids = []
        for t in tasks_data:
            resp = await client.post("/api/tasks/", json={
                **t, "project_id": proj_id, "assignee_id": dev_id
            })
            assert resp.status_code == 201
            task_ids.append(resp.json()["id"])

        # Step 4: Start working (move to in_progress)
        for task_id in task_ids[:2]:
            resp = await client.put(f"/api/tasks/{task_id}", json={"status": "in_progress"})
            assert resp.status_code == 200
            assert resp.json()["status"] == "in_progress"

        # Step 5: Complete tasks
        for task_id in task_ids:
            resp = await client.put(f"/api/tasks/{task_id}", json={"status": "done"})
            assert resp.status_code == 200
            assert resp.json()["status"] == "done"

        # Step 6: Verify all tasks are done
        resp = await client.get(f"/api/tasks/?project_id={proj_id}&status=done")
        assert resp.status_code == 200
        done_tasks = resp.json()
        assert len(done_tasks) == 4, f"Expected 4 done tasks, got {len(done_tasks)}"

        # Verify project still exists
        proj_resp = await client.get(f"/api/projects/{proj_id}")
        assert proj_resp.status_code == 200
        assert proj_resp.json()["name"] == "Sprint 1 - Auth Module"
