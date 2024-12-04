from enum import Enum, auto

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(Enum):
    PROJECT_MANAGER = auto()
    DEVELOPER = auto()
    SOFTWARE_QUALITY_ASSURANCE = auto()

    def __str__(self):
        return self.name.lower()

    @classmethod
    def choices(cls):
        return [
            (role.name.lower(), role.name.replace("_", " ").title()) for role in cls
        ]


class TaskStatus(Enum):
    TODO = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()

    def __str__(self):
        return self.name.lower()

    @classmethod
    def choices(cls):
        return [
            (role.name.lower(), role.name.replace("_", " ").title()) for role in cls
        ]


class User(AbstractUser):
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=50,
        choices=UserRole.choices(),
        default=UserRole.DEVELOPER.name.lower(),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} - {self.get_role_display()}"


class Project(models.Model):
    title = models.CharField(max_length=200, null=True)
    description = models.TextField(blank=True, null=True)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="managed_projects",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    project_members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="project_members"
    )

    def __str__(self):
        return self.title


class Task(models.Model):
    title = models.CharField(max_length=200, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices(),
        default=TaskStatus.TODO.name.lower(),
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
    )
    assigned_to = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="assigned_to"
    )
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.project.title}"


class Document(models.Model):
    file = models.FileField(upload_to="documents/")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="uploaded_documents",
    )
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="documents")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document for Task: {self.task.title} by {self.uploaded_by.username}"


class Comment(models.Model):
    content = models.TextField()
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_comments",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Comment by {self.created_by.username} on {self.task.title}"
