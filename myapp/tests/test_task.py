from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from myapp.models import Document, Project, Task, User


class TaskAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.manager_user = User.objects.create_user(
            username="manager", email="manager@gmail.com", password="testpass123"
        )
        self.team_member = User.objects.create_user(
            username="team_member",
            email="team_member@gmail.com",
            password="testpass123",
        )

        self.project = Project.objects.create(title="Test Project", manager=self.manager_user)

        self.task = Task.objects.create(
            title="Test Task",
            project=self.project,
            assignee=self.manager_user,
        )
        self.task.assigned_to.add(self.team_member)

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_create_task_by_project_manager(self):
        self.authenticate(self.manager_user)

        task_data = {
            "title": "New Task by project manager",
            "description": "Task description",
            "project_id": self.project.id,
            "assigned_to": [self.team_member.id],
        }

        response = self.client.post(reverse("task-list"), task_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.count(), 2)

    def test_create_task_by_non_manager(self):
        self.authenticate(self.team_member)

        task_data = {
            "title": "New Task",
            "description": "Task description",
            "project_id": self.project.id,
            "assigned_to": [self.team_member.id],
        }

        response = self.client.post(reverse("task-list"), task_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_tasks_for_assigned_user(self):
        task = Task.objects.create(
            title="Assigned Task",
            project=self.project,
            assignee=self.manager_user,
        )
        task.assigned_to.add(self.team_member)

        self.authenticate(self.team_member)
        response = self.client.get(reverse("task-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_update_task_by_project_manager(self):
        task = Task.objects.create(
            title="Original Task Title",
            project=self.project,
            assignee=self.manager_user,
        )

        self.authenticate(self.manager_user)
        update_data = {"title": "Updated Task Title"}

        response = self.client.patch(reverse("task-detail", kwargs={"pk": task.id}), update_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertEqual(task.title, "Updated Task Title")

    def test_delete_task_by_project_manager(self):
        task = Task.objects.create(
            title="Task to Delete",
            project=self.project,
            assignee=self.manager_user,
        )

        self.authenticate(self.manager_user)
        response = self.client.delete(reverse("task-detail", kwargs={"pk": task.id}))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Task.objects.filter(id=task.id).exists())

    def test_invalid_task_creation_validations(self):
        self.authenticate(self.manager_user)

        invalid_data = {
            "title": "Hi",
            "project_id": self.project.id,
            "assigned_to": [self.team_member.id],
        }
        response = self.client.post(reverse("task-list"), invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        invalid_data["title"] = "Valid Task Title"
        invalid_data["due_date"] = timezone.now().date() + timedelta(days=400)
        response = self.client.post(reverse("task-list"), invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_document(self, user=None):
        if not user:
            user = self.manager_user

        self.authenticate(user)

        document_data = {
            "file": SimpleUploadedFile(
                name="document.pdf",
                content=b"file content",
                content_type="application/pdf",
            )
        }

        response = self.client.post(
            reverse("task-upload-document", kwargs={"pk": self.task.id}),
            document_data,
            format="multipart",
        )

        return response

    def test_upload_document_by_assignee(self):
        response = self.test_upload_document(user=self.manager_user)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Document.objects.count(), 1)

    def test_upload_document_by_assigned_user(self):
        response = self.test_upload_document(user=self.team_member)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Document.objects.count(), 1)

    def test_upload_document_by_non_assignee_or_assigned_user(self):
        non_assigned_user = User.objects.create_user(
            username="non_assigned_user",
            email="non_assigned_user@gmail.com",
            password="testpass123",
        )

        self.authenticate(non_assigned_user)

        document_data = {
            "file": SimpleUploadedFile(
                name="document.pdf",
                content=b"file content",
                content_type="application/pdf",
            )
        }

        response = self.client.post(
            reverse("task-upload-document", kwargs={"pk": self.task.id}), document_data
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_view_documents(self, user=None):
        if not user:
            user = self.manager_user

        self.authenticate(user)
        response = self.client.get(reverse("task-documents", kwargs={"pk": self.task.id}))
        return response

    def test_view_documents_by_assignee(self):
        Document.objects.create(task=self.task, file="document.pdf", uploaded_by=self.manager_user)

        response = self.test_view_documents(user=self.manager_user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_view_documents_by_assigned_user(self):
        Document.objects.create(task=self.task, file="document.pdf", uploaded_by=self.manager_user)

        response = self.test_view_documents(user=self.team_member)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_view_documents_by_non_assignee_or_assigned_user(self):
        non_assigned_user = User.objects.create_user(
            username="non_assigned_user",
            email="non_assigned_user@gmail.com",
            password="testpass123",
        )

        Document.objects.create(task=self.task, file="document.pdf", uploaded_by=self.manager_user)

        response = self.test_view_documents(user=non_assigned_user)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_document(self, user=None):
        if not user:
            user = self.manager_user

        document = Document.objects.create(
            task=self.task, file="document.pdf", uploaded_by=self.manager_user
        )

        self.authenticate(user)

        response = self.client.delete(
            reverse(
                "task-delete-document",
                kwargs={"pk": self.task.id, "document_id": document.id},
            )
        )
        return response

    def test_delete_document_by_assignee(self):
        response = self.test_delete_document(user=self.manager_user)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Document.objects.count(), 0)

    def test_delete_document_by_uploaded_user(self):
        document = Document.objects.create(
            task=self.task, file="document.pdf", uploaded_by=self.team_member
        )

        self.authenticate(self.team_member)

        response = self.client.delete(
            reverse(
                "task-delete-document",
                kwargs={"pk": self.task.id, "document_id": document.id},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Document.objects.count(), 0)

    def test_delete_document_by_non_assignee_or_uploaded_user(self):
        non_assigned_user = User.objects.create_user(
            username="non_assigned_user",
            email="non_assigned_user@gmail.com",
            password="testpass123",
        )

        response = self.test_delete_document(user=non_assigned_user)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
