from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from myapp.models import User


class UserLoginTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.login_url = "/api/login/"
        self.user = User.objects.create_user(
            username="testuser", password="testpassword123"
        )
        self.valid_payload = {"username": "testuser", "password": "testpassword123"}

        self.invalid_payloads = [
            {"username": "wronguser", "password": "testpassword123"},
            {"username": "testuser", "password": "wrongpassword"},
            {"username": "", "password": "testpassword123"},
            {"username": "testuser", "password": ""},
        ]

    def test_successful_login(self):
        response = self.client.post(self.login_url, self.valid_payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.assertIn("user_id", response.data)
        self.assertIn("username", response.data)

        token = Token.objects.get(user=self.user)
        self.assertEqual(response.data["token"], token.key)

    def test_login_with_inactive_user(self):
        self.user.is_active = False
        self.user.save()

        response = self.client.post(self.login_url, self.valid_payload)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("error", response.data)


class UserLogoutTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.logout_url = "/api/logout/"
        self.user = User.objects.create_user(
            username="testuser", password="testpassword123"
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_successful_logout(self):
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        with self.assertRaises(Token.DoesNotExist):
            Token.objects.get(user=self.user)

    def test_logout_without_authentication(self):
        self.client.credentials()
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
