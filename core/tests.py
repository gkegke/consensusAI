from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth.models import User
from questions.models import Question
from ai_engine.models import AIModel

class PopulateDBCommandTest(TestCase):
    
    def test_populate_db_command(self):
        """Test that the populate_db command runs and creates initial data securely."""
        
        # Run command
        call_command('populate_db')
        
        # Assert Superuser
        self.assertTrue(User.objects.filter(username='admin').exists())
        
        # Assert AI Models exist and are configured for free tiers
        self.assertTrue(AIModel.objects.count() >= 2)
        self.assertTrue(AIModel.objects.filter(api_identifier='gemini/gemini-3.1-flash-lite-preview', is_active=True).exists())
        
        # Assert Questions loaded
        self.assertTrue(Question.objects.count() >= 2)
