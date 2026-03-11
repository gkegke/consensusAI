from django.test import TestCase
from django.contrib.auth.models import User
from django.db.utils import IntegrityError
from .models import Question, HumanVote

# <critical importance="10/10">
# Capstone Requirement (LO4): Ensuring database layer blocks hallucinated/invalid inputs
# </critical>
class VoteConstraintTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="testuser")
        self.question = Question.objects.create(
            text="Test Question?",
            slug="test-question",
            status="PROPOSED"
        )

    def test_valid_vote_saves_successfully(self):
        vote = HumanVote.objects.create(question=self.question, user=self.user, score=50.0)
        self.assertEqual(HumanVote.objects.count(), 1)

    def test_invalid_high_vote_raises_integrity_error(self):
        with self.assertRaises(IntegrityError):
            HumanVote.objects.create(question=self.question, user=self.user, score=150.0)

    def test_invalid_low_vote_raises_integrity_error(self):
        with self.assertRaises(IntegrityError):
            HumanVote.objects.create(question=self.question, user=self.user, score=-10.0)