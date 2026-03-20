from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from ai_engine.models import AIModel, ConsensusRun, AIResponse
from questions.models import Question

class CostCalculationTests(TestCase):
    """
    CRITICAL: Tests that AI response creation correctly triggers signals 
    that aggregate total costs up to the parent ConsensusRun to prevent leaky API spend.
    """
    def setUp(self):
        self.question = Question.objects.create(
            text="Will it rain?", 
            slug="rain", 
            question_type="PREDICTIVE_BINARY"
        )
        self.run = ConsensusRun.objects.create(question=self.question)
        self.model_a = AIModel.objects.create(name="Model A", api_identifier="a", developer="dev")
        self.model_b = AIModel.objects.create(name="Model B", api_identifier="b", developer="dev")

    def test_run_cost_aggregation_signals(self):
        # 1. Base Cost Should Be Zero
        self.assertEqual(self.run.total_cost, Decimal('0.0000000000'))

        # 2. Add first response
        r1 = AIResponse.objects.create(
            run=self.run, 
            model=self.model_a, 
            summary_sentence="Yes.",
            normalized_score=90.0, 
            cost=Decimal('0.0015000000')
        )
        self.run.refresh_from_db()
        self.assertEqual(self.run.total_cost, Decimal('0.0015000000'))

        # 3. Add second response
        r2 = AIResponse.objects.create(
            run=self.run, 
            model=self.model_b, 
            summary_sentence="No.",
            normalized_score=10.0, 
            cost=Decimal('0.0020000000')
        )
        self.run.refresh_from_db()
        self.assertEqual(self.run.total_cost, Decimal('0.0035000000'))

        # 4. Deleting a response should correctly reduce the cost total
        r1.delete()
        self.run.refresh_from_db()
        self.assertEqual(self.run.total_cost, Decimal('0.0020000000'))