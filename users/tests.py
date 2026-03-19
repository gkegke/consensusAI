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
        """Tests the signal: UserProfile should exist for new users."""
        self.assertTrue(hasattr(self.user, 'cai_profile'))
        self.assertEqual(self.user.cai_profile.user.username, "testuser")

    def test_dashboard_requires_login(self):
        """Tests: Protected views redirect to login."""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('account_login'), response.url)

    def test_dashboard_accessible_after_login(self):
        """Tests successful login and dashboard access."""
        self.client.login(username="testuser", password=self.user_password)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/dashboard.html')
        
    def test_dashboard_context_and_stats(self):
        """Tests that dashboard aggregations and onboarding logic compute accurately."""
        self.client.login(username="testuser", password=self.user_password)
        
        # Assert empty state (needs onboarding)
        res_empty = self.client.get(reverse('dashboard'))
        self.assertTrue(res_empty.context['needs_onboarding'])
        self.assertEqual(res_empty.context['total_votes'], 0)
        
        # Populate votes
        q1 = Question.objects.create(text="Subjective Q", slug="sub", question_type="SUBJECTIVE_SLIDER")
        q2 = Question.objects.create(text="Predictive Q", slug="pred", question_type="PREDICTIVE_BINARY", resolution_date=timezone.now() + timedelta(days=1))
        
        HumanVote.objects.create(question=q1, user=self.user, score=50.0)
        HumanVote.objects.create(question=q2, user=self.user, score=80.0)
        
        res_populated = self.client.get(reverse('dashboard'))
        self.assertFalse(res_populated.context['needs_onboarding'])
        self.assertEqual(res_populated.context['total_votes'], 2)
        self.assertEqual(res_populated.context['predictive_count'], 1)

    def test_profile_update_view(self):
        """Tests that a user can update their own bio via the form."""
        self.client.login(username="testuser", password=self.user_password)
        new_bio = "I am an AI researcher."
        response = self.client.post(reverse('profile_edit'), {'bio': new_bio})
        
        self.user.cai_profile.refresh_from_db()
        self.assertEqual(self.user.cai_profile.bio, new_bio)
        self.assertTrue(self.user.cai_profile.is_onboarded)
        self.assertRedirects(response, reverse('dashboard'))