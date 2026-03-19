from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Question

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
        
        # First POST upvotes
        self.client.post(url)
        self.assertEqual(self.q.upvoters.count(), 1)
        
        # Second POST removes upvote
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