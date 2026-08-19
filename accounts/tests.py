from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

User = get_user_model()


class AuthTests(APITestCase):
    def test_register_creates_customer_by_default(self):
        response = self.client.post(
            "/api/auth/register/",
            {"username": "newuser", "email": "new@test.com", "password": "StrongPass123!"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        user = User.objects.get(username="newuser")
        self.assertEqual(user.role, "CUSTOMER")
        self.assertIn("token", response.data)

    def test_register_ignores_client_supplied_role(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "sneaky",
                "password": "StrongPass123!",
                "role": "STAFF",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        user = User.objects.get(username="sneaky")
        self.assertEqual(user.role, "CUSTOMER")

    def test_register_rejects_weak_password(self):
        response = self.client.post(
            "/api/auth/register/",
            {"username": "weakpassuser", "password": "123"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_returns_token_for_valid_credentials(self):
        User.objects.create_user(username="logintest", password="StrongPass123!")
        response = self.client.post(
            "/api/auth/login/", {"username": "logintest", "password": "StrongPass123!"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)

    def test_login_rejects_wrong_password(self):
        User.objects.create_user(username="logintest2", password="StrongPass123!")
        response = self.client.post(
            "/api/auth/login/", {"username": "logintest2", "password": "wrongpass"}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_deletes_token(self):
        user = User.objects.create_user(username="logouttest", password="StrongPass123!")
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.post("/api/auth/logout/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Token.objects.filter(user=user).exists())

    def test_logout_requires_authentication(self):
        response = self.client.post("/api/auth/logout/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)