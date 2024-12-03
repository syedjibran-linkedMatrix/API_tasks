from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from myapp.models import User


class UserRegistrationTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = "/api/register/"

        self.valid_payload = {
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "strongpassword123",
        }

        self.invalid_payloads = [
            {"email": "incomplete@example.com", "password": "password123"},
            {"username": "incompleteuser", "password": "password123"},
            {"username": "nopassword", "email": "nopass@example.com"},
        ]

    def test_user_registration_success(self):
        response = self.client.post(self.register_url, self.valid_payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("token", response.data)
        self.assertIn("user_id", response.data)
        self.assertIn("username", response.data)

        user = User.objects.get(username=self.valid_payload["username"])
        self.assertIsNotNone(user)

        token = Token.objects.get(user=user)
        self.assertEqual(response.data["token"], token.key)

    def test_duplicate_username_registration(self):

        User.objects.create_user(**self.valid_payload)
        response = self.client.post(self.register_url, self.valid_payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)

    def test_invalid_registration_payloads(self):
        for payload in self.invalid_payloads:
            response = self.client.post(self.register_url, payload)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_email_uniqueness(self):
        first_response = self.client.post(self.register_url, self.valid_payload)
        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)

        duplicate_payload = self.valid_payload.copy()
        duplicate_payload["username"] = "differentusername"

        second_response = self.client.post(self.register_url, duplicate_payload)
        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", second_response.data)
