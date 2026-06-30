"""
tests/integration/test_api_users.py — Integration tests for User API endpoints.

Test Case Name: User API Integration Tests
Module: Task Manager - Integration
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database import Base, get_db

TEST_DB_URL = "sqlite+aiosqlite:///./test_users.db"
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


class TestUserAPI:
    """
    Test Case Name: User CRUD API Tests
    Module: Task Manager - Integration
    Description: Integration tests for the User REST API endpoints.
    Steps:
        1. POST /api/users/ to create user
        2. GET /api/users/{id} to fetch
        3. PUT /api/users/{id} to update name
        4. Test duplicate email rejection
    Expected Output: All endpoints return correct status codes and user data.
    """

    @pytest.mark.asyncio
    @pytest.mark.testid("TC-012")
    async def test_create_user(self, client):
        """
        Test Case Name: API Create User
        Module: Task Manager - Integration
        Description: Verify successful creation of a new user via POST /api/users/.
        Steps: Send POST request with JSON user data, assert response code is 201.
        Expected Output: Response 201 Created and contains matching fields.
        """
        resp = await client.post("/api/users/", json={
            "email": "alice@test.com",
            "name": "Alice Johnson"
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "alice@test.com"
        assert data["name"] == "Alice Johnson"
        assert data["is_active"] is True

    @pytest.mark.asyncio
    @pytest.mark.testid("TC-013")
    async def test_duplicate_email_rejected(self, client):
        """
        Test Case Name: API Create Duplicate Email Rejected
        Module: Task Manager - Integration
        Description: Verify that duplicate email registration returns conflict code.
        Steps: POST first user. POST second user with the same email.
        Expected Output: Second POST returns 409 Conflict.
        """
        await client.post("/api/users/", json={"email": "dup@test.com", "name": "User 1"})
        resp = await client.post("/api/users/", json={"email": "dup@test.com", "name": "User 2"})
        assert resp.status_code == 409

    @pytest.mark.asyncio
    @pytest.mark.testid("TC-014")
    async def test_get_user(self, client):
        """
        Test Case Name: API Get User By ID
        Module: Task Manager - Integration
        Description: Verify retrieving a user by their unique ID.
        Steps: Create user, extract ID, send GET request to /api/users/{id}.
        Expected Output: Response 200 OK containing correct user details.
        """
        create = await client.post("/api/users/", json={"email": "bob@test.com", "name": "Bob"})
        user_id = create.json()["id"]
        resp = await client.get(f"/api/users/{user_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == user_id

    @pytest.mark.asyncio
    @pytest.mark.testid("TC-015")
    async def test_update_user_name(self, client):
        """
        Test Case Name: API Update User Name
        Module: Task Manager - Integration
        Description: Verify updating a user's name via PUT /api/users/{id}.
        Steps: Create user, send PUT with new name, assert response.
        Expected Output: Response 200 OK with name updated to Carol Smith.
        """
        create = await client.post("/api/users/", json={"email": "carol@test.com", "name": "Carol"})
        user_id = create.json()["id"]
        resp = await client.put(f"/api/users/{user_id}", json={"name": "Carol Smith"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Carol Smith"

    @pytest.mark.asyncio
    @pytest.mark.testid("TC-016")
    async def test_list_users(self, client):
        """
        Test Case Name: API List Users
        Module: Task Manager - Integration
        Description: Verify listing all registered users.
        Steps: Create multiple users, send GET to /api/users/.
        Expected Output: Response 200 OK containing list of users.
        """
        await client.post("/api/users/", json={"email": "u1@test.com", "name": "User 1"})
        await client.post("/api/users/", json={"email": "u2@test.com", "name": "User 2"})
        resp = await client.get("/api/users/")
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    @pytest.mark.asyncio
    @pytest.mark.testid("TC-017")
    async def test_get_nonexistent_user(self, client):
        """
        Test Case Name: API Get Non-Existent User
        Module: Task Manager - Integration
        Description: Verify GET for missing user ID returns 404.
        Steps: Send GET request to /api/users/99999.
        Expected Output: Response 404 Not Found.
        """
        resp = await client.get("/api/users/99999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.testid("TC-018")
    async def test_health_endpoint(self, client):
        """
        Test Case Name: API Health Check
        Module: Task Manager - Integration
        Description: Verify health check returns status OK.
        Steps: Send GET request to /health.
        Expected Output: Response 200 OK.
        """
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
