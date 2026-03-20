from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from questions.models import Question, HumanVote
from django.utils import timezone
from datetime import timedelta

class UserAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_password = "testpassword123"
        self.user = User.objects.create_user(
            username="testuser", 
            email="test@example.com", 
            password=self.user_password
        )

    def test_user_profile_created_automatically(self):
        self.assertTrue(hasattr(self.user, 'cai_profile'))
        self.assertEqual(self.user.cai_profile.user.username, "testuser")

    def test_dashboard_requires_login(self):
        # Using follow=True to handle the redirect to login
        response = self.client.get(reverse('dashboard'), follow=True)
        self.assertIn('accounts/login/', response.redirect_chain[0][0])

    def test_dashboard_accessible_after_login(self):
        self.client.login(username="testuser", password=self.user_password)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        
    def test_dashboard_context_and_stats(self):
        self.client.login(username="testuser", password=self.user_password)
        
        # Test empty state
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['needs_onboarding'])
        
        # Populate votes
        q1 = Question.objects.create(text="Subj", slug="sub", question_type="SUBJECTIVE_SLIDER", status="ACTIVE")
        HumanVote.objects.create(question=q1, user=self.user, score=50.0)
        
        # Refresh dashboard
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['total_votes'], 1)
        self.assertFalse(response.context['needs_onboarding'])

    def test_profile_update_view(self):
        self.client.login(username="testuser", password=self.user_password)
        new_bio = "I am an AI researcher."
        # follow=True is critical for asserting redirects in Django tests
        response = self.client.post(reverse('profile_edit'), {'bio': new_bio}, follow=True)
        
        self.user.cai_profile.refresh_from_db()
        self.assertEqual(self.user.cai_profile.bio, new_bio)
        self.assertEqual(response.status_code, 200)