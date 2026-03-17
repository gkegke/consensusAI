from django.test import TestCase, Client, RequestFactory
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.contrib.sessions.middleware import SessionMiddleware
from .models import Question, HumanVote, AnonymousVote
from .services import process_vote, get_client_ip

class VoteServiceTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="testuser")
        self.choice_q = Question.objects.create(
            text="Who will win?",
            slug="choice-q",
            question_type="PREDICTIVE_CHOICE",
            choices=["Option A", "Option B"]
        )

    def test_process_vote_auto_calculates_other(self):
        """Test S5: Backend auto-balances the 'Other' category."""
        request = self.factory.post('/')
        request.user = self.user
        
        # User only provides 40% for Option A
        data = {
            'complex_forecast': [
                {'choice': 'Option A', 'confidence': 40.0}
            ]
        }
        
        success, msg = process_vote(request, self.choice_q, data)
        self.assertTrue(success)
        
        vote = HumanVote.objects.get(question=self.choice_q, user=self.user)
        # 40% Option A + 60% Other = 100%
        forecast = {i['choice']: i['confidence'] for i in vote.complex_forecast}
        self.assertEqual(forecast['Option A'], 40.0)
        self.assertEqual(forecast['Other'], 60.0)

    def test_vote_blocked_on_archived_question(self):
        """Hardening: Ensure users can't vote via POST on archived questions."""
        self.choice_q.status = 'ARCHIVED'
        self.choice_q.save()
        
        request = self.factory.post('/')
        request.user = self.user
        
        success, msg = process_vote(request, self.choice_q, {'score': 50.0})
        self.assertFalse(success)
        self.assertIn("archived", msg)

    def test_anonymous_session_persistence(self):
        """Test S3: Anonymous votes are correctly tied to session keys."""
        request = self.factory.post('/')
        request.user = User()
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(request)
        request.session.save()
        
        q = Question.objects.create(text="Slider", slug="slider", question_type="SUBJECTIVE_SLIDER")
        
        process_vote(request, q, {'score': 75.0})
        self.assertEqual(AnonymousVote.objects.filter(session_key=request.session.session_key).count(), 1)