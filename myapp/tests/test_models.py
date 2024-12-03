from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from myapp.models import Comment, Document, Project, Task, TaskStatus, UserRole

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    def test_create_user(self):
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == UserRole.DEVELOPER.name.lower()

    def test_user_str_method(self):
        user = User.objects.create_user(
            username="johndoe",
            email="john@example.com",
            password="testpass123",
            role=UserRole.PROJECT_MANAGER.name.lower(),
        )

        assert str(user) == "johndoe - Project Manager"


@pytest.mark.django_db
class TestProjectModel:
    def test_create_project(self):
        manager = User.objects.create_user(
            username="manager",
            email="manager@example.com",
            password="testpass123",
            role=UserRole.PROJECT_MANAGER.name.lower(),
        )

        project = Project.objects.create(
            title="Test Project",
            description="A test project description",
            manager=manager,
        )

        assert project.title == "Test Project"
        assert project.manager == manager
        assert project.description == "A test project description"

    def test_project_members(self):
        manager = User.objects.create_user(
            username="manager",
            email="manager@example.com",
            password="testpass123",
            role=UserRole.PROJECT_MANAGER.name.lower(),
        )

        dev1 = User.objects.create_user(
            username="dev1",
            email="dev1@example.com",
            password="testpass123",
            role=UserRole.DEVELOPER.name.lower(),
        )

        dev2 = User.objects.create_user(
            username="dev2",
            email="dev2@example.com",
            password="testpass123",
            role=UserRole.DEVELOPER.name.lower(),
        )

        project = Project.objects.create(title="Team Project", manager=manager)

        project.project_members.add(dev1, dev2)

        assert list(project.project_members.all()) == [dev1, dev2]


@pytest.mark.django_db
class TestTaskModel:
    def test_create_task(self):
        manager = User.objects.create_user(
            username="manager",
            email="manager@example.com",
            password="testpass123",
            role=UserRole.PROJECT_MANAGER.name.lower(),
        )

        project = Project.objects.create(title="Test Project", manager=manager)

        dev = User.objects.create_user(
            username="dev",
            email="dev@example.com",
            password="testpass123",
            role=UserRole.DEVELOPER.name.lower(),
        )

        due_date = timezone.now().date() + timedelta(days=14)

        task = Task.objects.create(
            title="Implement Feature",
            description="Detailed task description",
            project=project,
            status=TaskStatus.TODO.name.lower(),
            assignee=dev,
            due_date=due_date,
        )

        task.assigned_to.add(dev)

        assert task.title == "Implement Feature"
        assert task.project == project
        assert task.status == TaskStatus.TODO.name.lower()
        assert task.assignee == dev
        assert task.due_date == due_date

    def test_task_status_choices(self):
        status_choices = dict(Task._meta.get_field("status").choices)

        assert len(status_choices) == 3
        assert "todo" in status_choices
        assert "in progress" in status_choices
        assert "completed" in status_choices


@pytest.mark.django_db
class TestDocumentModel:
    def test_create_document(self):
        manager = User.objects.create_user(
            username="manager", email="manager@example.com", password="testpass123"
        )

        project = Project.objects.create(title="Test Project", manager=manager)

        task = Task.objects.create(title="Test Task", project=project)

        test_file = SimpleUploadedFile(
            name="test_document.txt", content=b"Test file content"
        )

        document = Document.objects.create(
            file=test_file, uploaded_by=manager, task=task
        )

        assert document.uploaded_by == manager
        assert document.task == task
        assert document.file.name.startswith("documents/test_document")


@pytest.mark.django_db
class TestCommentModel:
    def test_create_comment(self):
        manager = User.objects.create_user(
            username="manager", email="manager@example.com", password="testpass123"
        )

        project = Project.objects.create(title="Test Project", manager=manager)

        task = Task.objects.create(title="Test Task", project=project)

        comment = Comment.objects.create(
            content="This is a test comment", task=task, created_by=manager
        )

        assert comment.content == "This is a test comment"
        assert comment.task == task
        assert comment.created_by == manager


@pytest.mark.django_db
class TestEnumChoices:
    def test_user_role_choices(self):
        choices = UserRole.choices()

        assert len(choices) == 3
        assert ("project_manager", "Project Manager") in choices
        assert ("developer", "Developer") in choices
        assert ("software_quality_assurance", "Software Quality Assurance") in choices

    def test_task_status_choices(self):
        choices = TaskStatus.choices()

        assert len(choices) == 3
        assert ("todo", "Todo") in choices
        assert ("in_progress", "In Progress") in choices
        assert ("completed", "Completed") in choices
