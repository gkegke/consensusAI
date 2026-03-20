from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib.sessions.middleware import SessionMiddleware
from .models import Question, HumanVote
from .services import process_vote

class QuestionPhase3Tests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="author", password="password")
        self.other_user = User.objects.create_user(username="voter", password="password")
        self.q = Question.objects.create(
            text="Will AI pass the Turing test in 2026?", 
            slug="ai-turing", 
            submitted_by=self.user,
            status="IN_REVIEW"
        )

    def test_upvote_toggle(self):
        """Test the logic for community validation (Upvoting)."""
        self.client.login(username="voter", password="password")
        url = reverse('question_upvote', kwargs={'slug': self.q.slug})
        
        self.client.post(url)
        self.assertEqual(self.q.upvoters.count(), 1)
        
        self.client.post(url)
        self.assertEqual(self.q.upvoters.count(), 0)

    def test_proposal_feed_visibility(self):
        """Verify that IN_REVIEW questions appear in the proposal feed."""
        url = reverse('proposal_feed')
        response = self.client.get(url)
        self.assertContains(response, self.q.text)

    def test_owner_edit_permissions(self):
        """Ensures the OwnerOnlyProposalMixin works as expected."""
        self.client.login(username="author", password="password")
        url = reverse('question_edit', kwargs={'slug': self.q.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Stranger cannot edit
        self.client.login(username="voter", password="password")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

class QuestionSecurityTests(TestCase):
    """
    CRITICAL - Verifies the 'Vote to Reveal' logic which is the USP.
    """
    def setUp(self):
        self.user = User.objects.create_user(username="author", password="password")
        self.voter = User.objects.create_user(username="voter", password="password")
        self.q = Question.objects.create(
            text="Will AI pass the Turing test in 2026?", 
            slug="ai-turing", 
            submitted_by=self.user,
            status="ACTIVE"
        )

    def test_voting_gate_logic(self):
        """Verify that the detail view correctly identifies if a user has unlocked results."""
        self.client.login(username="voter", password="password")
        url = reverse('question_detail', kwargs={'slug': self.q.slug})
        
        # 1. Initially, has_voted should be False
        response = self.client.get(url)
        self.assertFalse(response.context['has_voted'])
        self.assertContains(response, "Enter Prediction / Stance") # Check for the gate UI

        # 2. Submit a vote
        vote_url = reverse('question_vote', kwargs={'slug': self.q.slug})
        self.client.post(vote_url, {'score': 75, 'reasoning': 'I am confident.'})

        # 3. Now has_voted should be True and Gate should be gone
        response = self.client.get(url)
        self.assertTrue(response.context['has_voted'])
        self.assertContains(response, "Access Granted")

class VoteServiceTests(TestCase):
    """
    CRITICAL: Validates the core business logic algorithm that processes 
    categorical probabilities and ensures 'Other' balances out correctly.
    """
    def setUp(self):
        self.user = User.objects.create_user(username="voter2", password="password")
        self.q_choice = Question.objects.create(
            text="Who wins?", slug="who-wins", question_type="PREDICTIVE_CHOICE",
            choices=["A", "B", "C"], status="ACTIVE"
        )
        self.factory = RequestFactory()

    def test_predictive_choice_exceeds_100(self):
        """Ensure process_vote blocks forecasts > 100% natively in the backend."""
        request = self.factory.post('/fake-url')
        request.user = self.user
        
        parsed_data = {
            'complex_forecast': [
                {'choice': 'A', 'confidence': 60.0},
                {'choice': 'B', 'confidence': 50.0}
            ]
        }
        success, msg = process_vote(request, self.q_choice, parsed_data)
        self.assertFalse(success)
        self.assertIn("exceed", msg.lower())

    def test_predictive_choice_auto_balances_other(self):
        """Ensure process_vote auto-calculates 'Other' correctly to reach 100%."""
        request = self.factory.post('/fake-url')
        request.user = self.user
        
        # User only allocates 60%
        parsed_data = {
            'complex_forecast': [
                {'choice': 'A', 'confidence': 60.0},
            ]
        }
        success, msg = process_vote(request, self.q_choice, parsed_data)
        self.assertTrue(success)
        
        # Check database to ensure "Other: 40%" was appended automatically
        vote = HumanVote.objects.get(question=self.q_choice, user=self.user)
        forecast = vote.complex_forecast
        self.assertEqual(len(forecast), 2)
        self.assertEqual(forecast[1]['choice'].lower(), 'other')
        self.assertEqual(forecast[1]['confidence'], 40.0)