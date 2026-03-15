import json
import logging
from pathlib import Path
from dateutil.parser import parse as parse_date
from django.core.management.base import BaseCommand
from django.conf import settings
from ai_engine.models import AIModel
from questions.models import Question

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Idempotently syncs database models and questions from JSON seed files.'

    def handle(self, *args, **kwargs):
        seed_dir = Path(settings.BASE_DIR) / "data" / "seed"
        
        self.sync_models(seed_dir / "ai_models.json")
        self.sync_questions(seed_dir / "questions.json")
        
        self.stdout.write(self.style.SUCCESS("✓ Sync Complete"))

    def sync_models(self, file_path):
        if not file_path.exists():
            self.stdout.write(self.style.WARNING(f"File not found: {file_path}"))
            return

        with open(file_path, 'r') as f:
            data = json.load(f)
            for item in data:
                obj, created = AIModel.objects.update_or_create(
                    api_identifier=item['api_identifier'],
                    defaults={
                        'name': item['name'],
                        'developer': item['developer'],
                        'is_active': item.get('is_active', True),
                        'tags': item.get('tags',[])
                    }
                )
                status = "Created" if created else "Updated"
                self.stdout.write(f"  [AIModel] {status}: {obj.api_identifier}")

    def sync_questions(self, file_path):
        if not file_path.exists():
            self.stdout.write(self.style.WARNING(f"File not found: {file_path}"))
            return

        with open(file_path, 'r') as f:
            data = json.load(f)
            for item in data:
                resolution_date = None
                if 'resolution_date' in item and item['resolution_date']:
                    resolution_date = parse_date(item['resolution_date'])
                    
                obj, created = Question.objects.update_or_create(
                    slug=item['slug'],
                    defaults={
                        'text': item['text'],
                        'context': item.get('context', ''),
                        'question_type': item.get('question_type', 'SUBJECTIVE_SLIDER'),
                        'choices': item.get('choices',[]),
                        'resolution_date': resolution_date,
                        'requires_web_search': item.get('requires_web_search', False),
                        'status': item.get('status', 'PROPOSED'),
                        'is_auto_poll': item.get('is_auto_poll', False),
                        'is_featured': item.get('is_featured', False),
                        'tags': item.get('tags',[])
                    }
                )
                if obj.question_type != 'SUBJECTIVE_SLIDER' and obj.resolution_state == 'N_A':
                     obj.resolution_state = 'PENDING'
                     obj.save()
                     
                status = "Created" if created else "Updated"
                self.stdout.write(f"  [Question] {status}: {obj.slug}")