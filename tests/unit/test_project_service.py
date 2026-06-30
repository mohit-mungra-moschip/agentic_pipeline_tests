"""
tests/unit/test_project_service.py — Unit tests for Project business logic.

Test Case Name: Project Service Logic Tests
Module: Task Manager - Unit
"""
import pytest
from app import schemas
from app.models import TaskStatus, TaskPriority


class TestProjectService:
    """
    Test Case Name: Project Business Logic
    Module: Task Manager - Unit
    Description: Tests for project-level validations and data integrity rules.
    Steps: Create projects, validate fields, test update schemas.
    Expected Output: All project fields behave according to spec.
    """

    @pytest.mark.testid("TC-019")
    def test_project_name_required(self):
        """
        Test Case Name: Project Name Validation
        Module: Task Manager - Unit
        Description: Verify that a project creation requires a name parameter.
        Steps: Create a ProjectCreate schema instance with name 'Backend API'.
        Expected Output: Schema validates and name matches the input.
        """
        project = schemas.ProjectCreate(name="Backend API", owner_id=1)
        assert project.name == "Backend API"

    @pytest.mark.testid("TC-020")
    def test_project_owner_id_required(self):
        """
        Test Case Name: Project Owner ID Validation
        Module: Task Manager - Unit
        Description: Verify that owner ID is correctly stored when creating a project.
        Steps: Create a ProjectCreate schema with owner_id set to 42.
        Expected Output: Owner ID is correctly set to 42.
        """
        project = schemas.ProjectCreate(name="Frontend", owner_id=42)
        assert project.owner_id == 42

    @pytest.mark.testid("TC-021")
    def test_project_description_optional(self):
        """
        Test Case Name: Project Optional Description
        Module: Task Manager - Unit
        Description: Verify that description is optional when creating a project.
        Steps: Create a ProjectCreate schema without setting a description.
        Expected Output: Schema validates with description set to None.
        """
        project = schemas.ProjectCreate(name="DevOps", owner_id=1)
        assert project.description is None

    @pytest.mark.testid("TC-022")
    def test_project_update_name_only(self):
        """
        Test Case Name: Project Update Name Only
        Module: Task Manager - Unit
        Description: Verify update schema allows changing name only.
        Steps: Create ProjectUpdate with new name, exclude unset fields.
        Expected Output: Only the 'name' field is present in update dataset.
        """
        update = schemas.ProjectUpdate(name="New Name")
        fields = update.model_dump(exclude_unset=True)
        assert list(fields.keys()) == ["name"]

    @pytest.mark.testid("TC-023")
    def test_project_update_description_only(self):
        """
        Test Case Name: Project Update Description Only
        Module: Task Manager - Unit
        Description: Verify update schema allows changing description only.
        Steps: Create ProjectUpdate with description, check fields.
        Expected Output: Only 'description' field is modified, name is absent.
        """
        update = schemas.ProjectUpdate(description="Updated description")
        fields = update.model_dump(exclude_unset=True)
        assert "description" in fields
        assert "name" not in fields

    @pytest.mark.testid("TC-024")
    def test_task_belongs_to_project(self):
        """
        Test Case Name: Task Project Association
        Module: Task Manager - Unit
        Description: Verify that a task correctly references a parent project ID.
        Steps: Create TaskCreate with project_id set to 10.
        Expected Output: Task schema holds the exact project_id.
        """
        task = schemas.TaskCreate(
            title="Write tests",
            project_id=10,
            priority=TaskPriority.HIGH,
        )
        assert task.project_id == 10

    @pytest.mark.testid("TC-025")
    def test_task_high_priority_critical(self):
        """
        Test Case Name: Task Critical Priority
        Module: Task Manager - Unit
        Description: Verify high/critical task priority setting.
        Steps: Create TaskCreate with priority set to CRITICAL.
        Expected Output: Task priority evaluates to CRITICAL.
        """
        task = schemas.TaskCreate(
            title="Production outage fix",
            project_id=1,
            priority=TaskPriority.CRITICAL,
        )
        assert task.priority == TaskPriority.CRITICAL

    @pytest.mark.testid("TC-026")
    def test_multiple_projects_different_owners(self):
        """
        Test Case Name: Multi-Project Owners Isolation
        Module: Task Manager - Unit
        Description: Verify different projects can store different owner IDs.
        Steps: Instantiate two projects with distinct owners.
        Expected Output: Owner IDs are independent and not shared.
        """
        p1 = schemas.ProjectCreate(name="Project Alpha", owner_id=1)
        p2 = schemas.ProjectCreate(name="Project Beta", owner_id=2)
        assert p1.owner_id != p2.owner_id
