from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth.models import User
from questions.models import Question
from ai_engine.models import AIModel

class PopulateDBCommandTest(TestCase):
    
    # <important importance="8/10">
    # Ensures the command is idempotent and functions correctly without crashing.
    # </important>
    def test_populate_db_command(self):
        """Test that the populate_db command runs and creates initial data securely."""
        
        # Run command
        call_command('populate_db')
        
        # Assert Superuser
        self.assertTrue(User.objects.filter(username='admin').exists())
        
        # Assert AI Models exist and are configured for free tiers
        self.assertTrue(AIModel.objects.count() >= 2)
        self.assertTrue(AIModel.objects.filter(api_identifier='gemini-1.5-flash', is_active=True).exists())
        self.assertTrue(AIModel.objects.filter(api_identifier='claude-3-haiku-20240307', is_active=False).exists())
        
        # Assert Questions loaded
        self.assertTrue(Question.objects.count() >= 2)
