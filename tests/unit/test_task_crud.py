"""
tests/unit/test_task_crud.py — Unit tests for Task CRUD logic.

Test Case Name: Task CRUD Unit Tests
Module: Task Manager - Unit
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app import schemas
from app.models import TaskStatus, TaskPriority


class TestTaskSchemas:
    """
    Test Case Name: Task Schema Validation
    Module: Task Manager - Unit
    Description: Verify Pydantic schemas correctly validate task data.
    Steps: Create schema instances with valid and invalid data.
    Expected Output: Valid data creates schema; invalid data raises ValidationError.
    """

    @pytest.mark.testid("TC-027")
    def test_task_create_defaults(self):
        """
        Test Case Name: Task Create Defaults
        Module: Task Manager - Unit
        Description: Verify a new task gets created with default status (TODO) and priority (MEDIUM).
        Steps: Create TaskCreate with title and project_id only.
        Expected Output: status is TODO, priority is MEDIUM, assignee_id is None.
        """
        task = schemas.TaskCreate(
            title="Fix login bug",
            project_id=1,
        )
        assert task.status == TaskStatus.TODO
        assert task.priority == TaskPriority.MEDIUM
        assert task.assignee_id is None

    @pytest.mark.testid("TC-028")
    def test_task_create_all_fields(self):
        """
        Test Case Name: Task Create All Fields
        Module: Task Manager - Unit
        Description: Verify a new task gets created successfully with all fields explicitly set.
        Steps: Create TaskCreate specifying title, description, status, priority, project_id, assignee_id.
        Expected Output: Schema validates and properties match setting.
        """
        task = schemas.TaskCreate(
            title="Implement auth",
            description="Add JWT auth",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            project_id=2,
            assignee_id=5,
        )
        assert task.title == "Implement auth"
        assert task.priority == TaskPriority.HIGH

    @pytest.mark.testid("TC-029")
    def test_task_update_partial(self):
        """
        Test Case Name: Task Update Partial Fields
        Module: Task Manager - Unit
        Description: Verify update schema allows changing individual fields without setting others.
        Steps: Create TaskUpdate with status=DONE, check dump keys.
        Expected Output: Only 'status' is present in the update dump.
        """
        update = schemas.TaskUpdate(status=TaskStatus.DONE)
        fields = update.model_dump(exclude_unset=True)
        assert "status" in fields
        assert "title" not in fields
        assert "priority" not in fields

    @pytest.mark.testid("TC-030")
    def test_task_status_enum_values(self):
        """
        Test Case Name: Task Status Enum Validity
        Module: Task Manager - Unit
        Description: Verify correct string values for TaskStatus enum options.
        Steps: Assert all TaskStatus string representation mappings.
        Expected Output: todo, in_progress, done, cancelled values match.
        """
        assert TaskStatus.TODO == "todo"
        assert TaskStatus.IN_PROGRESS == "in-progress"  # DEMO_BREAK
        assert TaskStatus.DONE == "done"
        assert TaskStatus.CANCELLED == "cancelled"

    @pytest.mark.testid("TC-031")
    def test_task_priority_ordering(self):
        """
        Test Case Name: Task Priority Options
        Module: Task Manager - Unit
        Description: Verify correct string mappings for TaskPriority levels.
        Steps: Check for low, medium, high, critical values in TaskPriority.
        Expected Output: All four priority options are defined.
        """
        priorities = [p.value for p in TaskPriority]
        assert "low" in priorities
        assert "medium" in priorities
        assert "high" in priorities
        assert "critical" in priorities


class TestUserSchemas:
    """
    Test Case Name: User Schema Validation
    Module: Task Manager - Unit
    Description: Verify user schemas handle email and name fields correctly.
    Expected Output: UserCreate requires valid email and name.
    """

    @pytest.mark.testid("TC-032")
    def test_user_create_valid(self):
        """
        Test Case Name: User Schema Create Valid
        Module: Task Manager - Unit
        Description: Verify UserCreate schema instantiates correctly with valid parameters.
        Steps: Instantiate UserCreate with email and name, check fields.
        Expected Output: Fields contain exact provided values.
        """
        user = schemas.UserCreate(email="dev@example.com", name="Dev User")
        assert user.email == "dev@example.com"
        assert user.name == "Dev User"

    @pytest.mark.testid("TC-033")
    def test_user_update_optional(self):
        """
        Test Case Name: User Schema Update Optional
        Module: Task Manager - Unit
        Description: Verify UserUpdate schema handles partial optional updates.
        Steps: Instantiate UserUpdate with name, assert update fields.
        Expected Output: Only the name field is included in the dump.
        """
        update = schemas.UserUpdate(name="New Name")
        fields = update.model_dump(exclude_unset=True)
        assert "name" in fields
        assert "is_active" not in fields


class TestProjectSchemas:
    """
    Test Case Name: Project Schema Validation
    Module: Task Manager - Unit
    Description: Verify project schemas validate owner_id correctly.
    Expected Output: ProjectCreate requires name and owner_id.
    """

    @pytest.mark.testid("TC-034")
    def test_project_create_minimal(self):
        """
        Test Case Name: Project Create Minimal
        Module: Task Manager - Unit
        Description: Verify ProjectCreate schema instantiates with minimal required fields.
        Steps: Instantiate ProjectCreate with name and owner_id, check description defaults.
        Expected Output: Project is initialized and description is None.
        """
        project = schemas.ProjectCreate(name="Sprint 1", owner_id=1)
        assert project.name == "Sprint 1"
        assert project.description is None

    @pytest.mark.testid("TC-035")
    def test_project_create_with_description(self):
        """
        Test Case Name: Project Create With Description
        Module: Task Manager - Unit
        Description: Verify ProjectCreate schema stores description when provided.
        Steps: Instantiate ProjectCreate with description.
        Expected Output: Description field matches provided input.
        """
        project = schemas.ProjectCreate(
            name="Alpha Release",
            description="First public release",
            owner_id=3,
        )
        assert project.description == "First public release"
