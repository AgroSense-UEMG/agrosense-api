from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()

from .models import Device, InstitutionalDomain, Project

class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Create allowed domain
        InstitutionalDomain.objects.create(domain='example.com')
        
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpassword123'
        }
        self.user = User.objects.create_user(**self.user_data)

    def test_user_creation_invalid_domain(self):
        """Test that user cannot be created with invalid domain"""
        with self.assertRaises(Exception): # ValidationError is wrapped in some contexts, but let's be broad or specific
             User.objects.create_user(username='baduser', email='bad@evil.com', password='pw')

    def test_user_creation(self):
        """Test if custom user is created correctly"""
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(self.user.username, 'testuser')
        self.assertTrue(self.user.check_password('testpassword123'))

    def test_jwt_token_obtain(self):
        """Test if we can get a JWT token"""
        response = self.client.post('/api/token/', {
            'username': 'testuser',
            'password': 'testpassword123'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_jwt_token_invalid_credentials(self):
        """Test login with wrong password"""
        response = self.client.post('/api/token/', {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ProjectApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        InstitutionalDomain.objects.create(domain="example.com")

        self.user_a = User.objects.create_user(
            username="usera",
            email="usera@example.com",
            password="password12345",
        )
        self.user_b = User.objects.create_user(
            username="userb",
            email="userb@example.com",
            password="password12345",
        )

        self.client.force_authenticate(user=self.user_a)

    def test_project_crud_scoped_to_user(self):
        # Create A
        create_resp = self.client.post(
            "/api/projects/",
            {"name": "Projeto A", "description": "desc"},
            format="json",
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        project_a_id = create_resp.data["id"]

        # Create B using separate client
        client_b = APIClient()
        client_b.force_authenticate(user=self.user_b)
        create_b_resp = client_b.post(
            "/api/projects/",
            {"name": "Projeto B", "description": "desc"},
            format="json",
        )
        self.assertEqual(create_b_resp.status_code, status.HTTP_201_CREATED)
        project_b_id = create_b_resp.data["id"]

        # List only A
        list_resp = self.client.get("/api/projects/")
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        ids = {p["id"] for p in list_resp.data}
        self.assertIn(project_a_id, ids)
        self.assertNotIn(project_b_id, ids)

        # Cannot access B (404 due to queryset scoping)
        retrieve_b_resp = self.client.get(f"/api/projects/{project_b_id}/")
        self.assertEqual(retrieve_b_resp.status_code, status.HTTP_404_NOT_FOUND)

        # Cannot update B
        patch_b_resp = self.client.patch(
            f"/api/projects/{project_b_id}/",
            {"name": "hacked"},
            format="json",
        )
        self.assertEqual(patch_b_resp.status_code, status.HTTP_404_NOT_FOUND)

        # Can update A
        patch_a_resp = self.client.patch(
            f"/api/projects/{project_a_id}/",
            {"name": "Projeto A2"},
            format="json",
        )
        self.assertEqual(patch_a_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_a_resp.data["name"], "Projeto A2")

        # Cannot delete B
        del_b_resp = self.client.delete(f"/api/projects/{project_b_id}/")
        self.assertEqual(del_b_resp.status_code, status.HTTP_404_NOT_FOUND)

        # Can delete A
        del_a_resp = self.client.delete(f"/api/projects/{project_a_id}/")
        self.assertEqual(del_a_resp.status_code, status.HTTP_204_NO_CONTENT)


class DeviceLinkProjectApiTests(TestCase):
    def setUp(self):
        self.client_a = APIClient()
        self.client_b = APIClient()
        InstitutionalDomain.objects.create(domain="example.com")

        self.user_a = User.objects.create_user(
            username="usera2",
            email="usera2@example.com",
            password="password12345",
        )
        self.user_b = User.objects.create_user(
            username="userb2",
            email="userb2@example.com",
            password="password12345",
        )

        self.client_a.force_authenticate(user=self.user_a)
        self.client_b.force_authenticate(user=self.user_b)

        self.project_a = Project.objects.create(name="PA", user=self.user_a)
        self.project_b = Project.objects.create(name="PB", user=self.user_b)

        self.device_a = Device.objects.create(name="DA", user=self.user_a)

    def test_user_cannot_patch_other_users_device(self):
        resp = self.client_b.patch(
            f"/api/devices/{self.device_a.id}/",
            {"name": "hacked"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_can_link_and_unlink_own_device_to_own_project(self):
        link_resp = self.client_a.patch(
            f"/api/devices/{self.device_a.id}/",
            {"project_id": self.project_a.id},
            format="json",
        )
        self.assertEqual(link_resp.status_code, status.HTTP_200_OK)

        detail_resp = self.client_a.get(f"/api/devices/{self.device_a.id}/")
        self.assertEqual(detail_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_resp.data["project"], self.project_a.id)

        unlink_resp = self.client_a.patch(
            f"/api/devices/{self.device_a.id}/",
            {"project_id": None},
            format="json",
        )
        self.assertEqual(unlink_resp.status_code, status.HTTP_200_OK)

        detail_resp2 = self.client_a.get(f"/api/devices/{self.device_a.id}/")
        self.assertEqual(detail_resp2.status_code, status.HTTP_200_OK)
        self.assertIsNone(detail_resp2.data["project"])

    def test_user_cannot_link_device_to_other_users_project(self):
        resp = self.client_a.patch(
            f"/api/devices/{self.device_a.id}/",
            {"project_id": self.project_b.id},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
