from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from datetime import timedelta

User = get_user_model()

from .models import Device, InstitutionalDomain, Measurement, Project, ProjectInvite

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
            'email': 'test@example.com',
            'password': 'testpassword123'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_jwt_token_invalid_credentials(self):
        """Test login with wrong password"""
        response = self.client.post('/api/token/', {
            'email': 'test@example.com',
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


class Sprint3ApiTests(TestCase):
    def setUp(self):
        InstitutionalDomain.objects.create(domain="example.com")

        self.owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="password12345",
        )
        self.member = User.objects.create_user(
            username="member",
            email="member@example.com",
            password="password12345",
        )
        self.outsider = User.objects.create_user(
            username="outsider",
            email="outsider@example.com",
            password="password12345",
        )

        self.owner_client = APIClient()
        self.member_client = APIClient()
        self.outsider_client = APIClient()
        self.owner_client.force_authenticate(user=self.owner)
        self.member_client.force_authenticate(user=self.member)
        self.outsider_client.force_authenticate(user=self.outsider)

        self.project = Project.objects.create(name="Estufa 1", user=self.owner)
        self.device = Device.objects.create(
            name="ESP32_A1",
            user=self.owner,
            project=self.project,
            manifest={
                "name": "Estufa",
                "components": [
                    {"id": "sensor_temp_ar", "type": "sensor"},
                ],
            },
        )

    def test_manifest_endpoint_returns_device_manifest(self):
        response = self.owner_client.get(f"/api/devices/{self.device.id}/manifest/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["manifest"]["name"], "Estufa")

    def test_readings_endpoint_filters_by_date_and_is_paginated(self):
        old_measurement = Measurement.objects.create(
            device=self.device,
            data={"sensor_temp_ar": 20},
        )
        Measurement.objects.filter(pk=old_measurement.pk).update(
            timestamp=timezone.now() - timedelta(days=3)
        )
        new_measurement = Measurement.objects.create(
            device=self.device,
            data={"sensor_temp_ar": 28},
        )

        start_date = (timezone.now() - timedelta(days=1)).date().isoformat()
        response = self.owner_client.get(
            f"/api/devices/{self.device.id}/readings/",
            {"start_date": start_date},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        ids = {item["id"] for item in response.data["results"]}
        self.assertIn(new_measurement.id, ids)
        self.assertNotIn(old_measurement.id, ids)

    def test_inventory_reports_status_after_telemetry(self):
        response = self.owner_client.post(
            "/api/hw/data/",
            {"name": self.device.name, "data": {"sensor_temp_ar": 29}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.device.refresh_from_db()
        self.assertTrue(self.device.is_online)
        self.assertIsNotNone(self.device.last_seen)

        inventory = self.owner_client.get("/api/devices/")
        self.assertEqual(inventory.status_code, status.HTTP_200_OK)
        self.assertEqual(inventory.data[0]["status"], "online")
        self.assertIsNotNone(inventory.data[0]["last_seen"])

    def test_invite_email_and_accept_grant_project_access(self):
        response = self.owner_client.post(
            f"/api/projects/{self.project.id}/invite/",
            {"email": self.member.email},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(str(response.data["token"]), mail.outbox[0].body)

        pending = self.member_client.get("/api/invites/")
        self.assertEqual(pending.status_code, status.HTTP_200_OK)
        self.assertEqual(len(pending.data), 1)

        accept = self.member_client.post(
            "/api/invites/accept/",
            {"token": response.data["token"]},
            format="json",
        )
        self.assertEqual(accept.status_code, status.HTTP_200_OK)

        invite = ProjectInvite.objects.get(pk=response.data["id"])
        self.assertEqual(invite.status, ProjectInvite.STATUS_ACCEPTED)
        self.assertTrue(self.project.members.filter(pk=self.member.pk).exists())

        member_projects = self.member_client.get("/api/projects/")
        self.assertEqual(member_projects.status_code, status.HTTP_200_OK)
        self.assertEqual(member_projects.data[0]["id"], self.project.id)

        member_devices = self.member_client.get("/api/devices/")
        self.assertEqual(member_devices.status_code, status.HTTP_200_OK)
        self.assertEqual(member_devices.data[0]["id"], self.device.id)

        forbidden_patch = self.member_client.patch(
            f"/api/devices/{self.device.id}/",
            {"name": "hacked"},
            format="json",
        )
        self.assertEqual(forbidden_patch.status_code, status.HTTP_404_NOT_FOUND)

    def test_outsider_cannot_read_project_device_history(self):
        response = self.outsider_client.get(f"/api/devices/{self.device.id}/readings/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_create_duplicate_pending_invite(self):
        first = self.owner_client.post(
            f"/api/projects/{self.project.id}/invite/",
            {"email": self.member.email},
            format="json",
        )
        second = self.owner_client.post(
            f"/api/projects/{self.project.id}/invite/",
            {"email": self.member.email},
            format="json",
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
