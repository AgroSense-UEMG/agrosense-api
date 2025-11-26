from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()

from .models import InstitutionalDomain

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
