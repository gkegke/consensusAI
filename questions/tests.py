from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from .models import Question, HumanVote

class VoteConstraintTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="testuser")
        
        self.binary_q = Question.objects.create(
            text="Will X happen?",
            slug="binary-q",
            question_type="PREDICTIVE_BINARY",
            resolution_date=timezone.now() + timedelta(days=10)
        )
        
        self.choice_q = Question.objects.create(
            text="Who will win?",
            slug="choice-q",
            question_type="PREDICTIVE_CHOICE",
            choices=["Option A", "Option B", "Option C"]
        )

    def test_valid_binary_vote_saves(self):
        vote = HumanVote.objects.create(question=self.binary_q, user=self.user, score=85.0)
        self.assertEqual(HumanVote.objects.count(), 1)

    def test_predictive_choice_requires_valid_json_math(self):
        # Math sums to 100.0 - Valid
        valid_forecast = [
            {"choice": "Option A", "confidence": 70.0},
            {"choice": "Option B", "confidence": 30.0}
        ]
        HumanVote.objects.create(question=self.choice_q, user=self.user, complex_forecast=valid_forecast)
        self.assertEqual(HumanVote.objects.filter(question=self.choice_q).count(), 1)

    def test_predictive_choice_fails_on_bad_math(self):
        # Math sums to 150.0 - Invalid
        invalid_forecast = [
            {"choice": "Option A", "confidence": 90.0},
            {"choice": "Option B", "confidence": 60.0}
        ]
        with self.assertRaises(ValidationError):
            HumanVote.objects.create(question=self.choice_q, user=self.user, complex_forecast=invalid_forecast)
            
    def test_predictive_choice_fails_on_invalid_choice(self):
        # Contains "Option D" which is not in question.choices
        invalid_forecast = [
            {"choice": "Option D", "confidence": 100.0}
        ]
        with self.assertRaises(ValidationError):
            HumanVote.objects.create(question=self.choice_q, user=self.user, complex_forecast=invalid_forecast)

    def test_voting_after_deadline_fails(self):
        expired_q = Question.objects.create(
            text="Expired?",
            slug="expired-q",
            question_type="PREDICTIVE_BINARY",
            resolution_date=timezone.now() - timedelta(days=1)
        )
        with self.assertRaises(ValidationError):
            HumanVote.objects.create(question=expired_q, user=self.user, score=50.0)