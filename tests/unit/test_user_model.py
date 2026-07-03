"""
tests/unit/test_user_model.py — Unit tests for User model behavior.

Test Case Name: User Model Validation Tests
Module: Task Manager - Unit
"""
import pytest
from app import schemas
from app.models import TaskStatus


class TestUserModel:
    """
    Test Case Name: User Model Logic
    Module: Task Manager - Unit
    Description: Tests for user model field validations and schema contracts.
    Steps: Instantiate schemas with various inputs, check field values.
    Expected Output: Fields match what was provided; defaults are correct.
    """

    @pytest.mark.testid("TC-036")
    def test_user_email_is_string(self):
        """
        Test Case Name: User Email DataType
        Module: Task Manager - Unit
        Description: Verify email field in UserCreate schema is a string.
        Steps: Instantiate UserCreate schema with email and name, check type of email.
        Expected Output: The schema validates and email is a Python string.
        """
        user = schemas.UserCreate(email="alice@example.com", name="Alice")
        assert isinstance(user.email, str)

    @pytest.mark.testid("TC-037")
    def test_user_name_not_empty(self):
        """
        Test Case Name: User Name Non-Empty
        Module: Task Manager - Unit
        Description: Verify name field contains characters when creating a user.
        Steps: Instantiate UserCreate schema, assert length of name > 0.
        Expected Output: Schema validates and length check passes.
        """
        user = schemas.UserCreate(email="bob@test.com", name="Bob")
        assert len(user.name) > 0  # DEMO_BREAK

    @pytest.mark.testid("TC-038")
    def test_user_update_is_active_flag(self):
        """
        Test Case Name: User Update Status Flag
        Module: Task Manager - Unit
        Description: Verify user active status can be updated/deactivated.
        Steps: Instantiate UserUpdate with is_active=False.
        Expected Output: Update schema correctly stores is_active as False.
        """
        update = schemas.UserUpdate(is_active=False)
        assert update.is_active is False

    @pytest.mark.testid("TC-039")
    def test_user_update_empty_noop(self):
        """
        Test Case Name: User Update No-Op
        Module: Task Manager - Unit
        Description: Verify update schema accepts empty values without producing updates.
        Steps: Instantiate UserUpdate with no arguments, check dump.
        Expected Output: Model dump of unset fields is empty.
        """
        update = schemas.UserUpdate()
        fields = update.model_dump(exclude_unset=True)
        assert fields == {}

    @pytest.mark.testid("TC-040")
    def test_task_status_todo_is_default(self):
        """
        Test Case Name: Task Default Status
        Module: Task Manager - Unit
        Description: Verify new task creation defaults to TODO status.
        Steps: Instantiate TaskCreate, check status property.
        Expected Output: Task status equals TaskStatus.TODO.
        """
        task = schemas.TaskCreate(title="My Task", project_id=1)
        assert task.status == TaskStatus.TODO

    @pytest.mark.testid("TC-041")
    def test_task_done_status_assignment(self):
        """
        Test Case Name: Task Status Assignment
        Module: Task Manager - Unit
        Description: Verify status updates work for TaskUpdate schemas.
        Steps: Instantiate TaskUpdate with TaskStatus.DONE, verify status.
        Expected Output: Status matches TaskStatus.DONE.
        """
        update = schemas.TaskUpdate(status=TaskStatus.DONE)
        assert update.status == TaskStatus.DONE

    @pytest.mark.testid("TC-042")
    def test_task_title_minimum_length(self):
        """
        Test Case Name: Task Title Length Validation
        Module: Task Manager - Unit
        Description: Verify that a task title has at least 1 character.
        Steps: Instantiate TaskCreate with single character title.
        Expected Output: Schema validates successfully.
        """
        task = schemas.TaskCreate(title="A", project_id=1)
        assert len(task.title) >= 1

    @pytest.mark.testid("TC-043")
    def test_multiple_tasks_independent(self):
        """
        Test Case Name: Multi-Task Schema Isolation
        Module: Task Manager - Unit
        Description: Verify different task schemas hold independent values.
        Steps: Create two task schemas with different titles and project IDs.
        Expected Output: Assertions verify the datasets are distinct.
        """
        t1 = schemas.TaskCreate(title="Task One", project_id=1)
        t2 = schemas.TaskCreate(title="Task Two", project_id=2)
        assert t1.title != t2.title
        assert t1.project_id != t2.project_id
