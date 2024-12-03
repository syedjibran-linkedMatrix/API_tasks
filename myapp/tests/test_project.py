from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from myapp.models import Project, User, UserRole


class ProjectViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.project_manager = User.objects.create_user(
            username="projectmanager",
            email="projectmanager123@gmail.com",
            password="password123",
            role=UserRole.PROJECT_MANAGER.name.lower(),
        )

        self.developer = User.objects.create_user(
            username="developer",
            email="developer123@gmail.com",
            password="password123",
            role=UserRole.DEVELOPER.name.lower(),
        )

        self.project = Project.objects.create(title="Test Project", manager=self.project_manager)

        self.project.project_members.add(self.developer)

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def create_user(self, username, role=UserRole.DEVELOPER):
        return User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="password123",
            role=role.name.lower(),
        )

    def test_project_creation_by_project_manager(self):
        self.client.force_authenticate(user=self.project_manager)

        project_data = {"title": "New Project", "description": "Project description"}
        response = self.client.post(reverse("project-list"), project_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Project.objects.count(), 2)

    def test_project_creation_by_non_project_manager(self):
        self.client.force_authenticate(user=self.developer)

        project_data = {
            "title": "Unauthorized Project",
            "description": "Should not be created",
        }
        response = self.client.post(reverse("project-list"), project_data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Project.objects.count(), 1)

    def test_project_update_by_manager(self):
        self.client.force_authenticate(user=self.project_manager)

        update_data = {"title": "Updated Project Name"}
        response = self.client.patch(
            reverse("project-detail", kwargs={"pk": self.project.id}), update_data
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(self.project.title, "Updated Project Name")

    def test_project_update_by_non_manager(self):
        self.client.force_authenticate(user=self.developer)

        update_data = {"title": "Unauthorized Update"}
        response = self.client.patch(
            reverse("project-detail", kwargs={"pk": self.project.id}), update_data
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_project_delete_by_manager(self):
        self.client.force_authenticate(user=self.project_manager)

        response = self.client.delete(reverse("project-detail", kwargs={"pk": self.project.id}))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Project.objects.filter(id=self.project.id).exists())

    def test_project_delete_by_non_manager(self):
        self.client.force_authenticate(user=self.developer)

        response = self.client.delete(reverse("project-detail", kwargs={"pk": self.project.id}))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Project.objects.filter(id=self.project.id).exists())

    def test_add_members_by_project_manager(self):
        user1 = self.create_user("user1")
        user2 = self.create_user("user2")

        self.client.force_authenticate(user=self.project_manager)
        data = {"user_ids": [user1.id, user2.id]}

        response = self.client.post(
            reverse("project-add-members", kwargs={"pk": self.project.id}), data
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertIn(user1, self.project.project_members.all())
        self.assertIn(user2, self.project.project_members.all())

    def test_add_members_by_non_manager(self):
        user1 = self.create_user("user1")

        self.client.force_authenticate(user=self.developer)
        data = {"user_ids": [user1.id]}

        response = self.client.post(
            reverse("project-add-members", kwargs={"pk": self.project.id}), data
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.project.refresh_from_db()
        self.assertNotIn(user1, self.project.project_members.all())

    def test_remove_members_by_project_manager(self):
        user_to_remove = self.create_user("removable_user")
        self.project.project_members.add(user_to_remove)
        self.client.force_authenticate(user=self.project_manager)

        data = {"user_ids": [user_to_remove.id]}

        response = self.client.post(
            reverse("project-remove-members", kwargs={"pk": self.project.id}), data
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertNotIn(user_to_remove, self.project.project_members.all())

    def test_remove_members_by_non_manager(self):
        user_to_remove = self.create_user("removable_user")
        self.project.project_members.add(user_to_remove)
        self.client.force_authenticate(user=self.developer)

        data = {"user_ids": [user_to_remove.id]}

        response = self.client.post(
            reverse("project-remove-members", kwargs={"pk": self.project.id}), data
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.project.refresh_from_db()
        self.assertIn(user_to_remove, self.project.project_members.all())
