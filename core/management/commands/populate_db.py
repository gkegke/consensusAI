from decimal import Decimal
import json
import logging
import os
from pathlib import Path
from dateutil.parser import parse as parse_date
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth.models import User
from ai_engine.models import AIModel, ConsensusRun, AIResponse
from questions.models import Question

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Idempotently syncs database models, questions, and mock AI runs from JSON seed files.'

    def handle(self, *args, **kwargs):
        seed_dir = Path(settings.BASE_DIR) / "data" / "seed"
        
        self.stdout.write("Checking for admin user...")
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'adminpass123')
            self.stdout.write(self.style.SUCCESS("Created superuser: admin"))

        self.sync_models(seed_dir / "ai_models.json")
        self.sync_questions(seed_dir / "questions.json")
        self.sync_runs(seed_dir / "consensus_runs.json")
        
        self.stdout.write(self.style.SUCCESS("✓ Sync Complete"))

    def sync_models(self, file_path):
        if not file_path.exists():
            return
        with open(file_path, 'r') as f:
            data = json.load(f)
            for item in data:
                AIModel.objects.update_or_create(
                    api_identifier=item['api_identifier'],
                    defaults={
                        'name': item['name'],
                        'developer': item['developer'],
                        'is_active': item.get('is_active', True),
                        'tags': item.get('tags',[])
                    }
                )

    def sync_questions(self, file_path):
        if not file_path.exists():
            return
        with open(file_path, 'r') as f:
            data = json.load(f)
            for item in data:
                resolution_date = parse_date(item['resolution_date']) if item.get('resolution_date') else None
                obj, _ = Question.objects.update_or_create(
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

    def sync_runs(self, file_path):
        if not file_path.exists():
            return

        with open(file_path, 'r') as f:
            data = json.load(f)
            for run_data in data:
                try:
                    q = Question.objects.get(slug=run_data['question_slug'])
                    
                    run, created = ConsensusRun.objects.update_or_create(
                        question=q,
                        prompt_version=run_data.get('prompt_version', 'seed-data-v1'),
                        defaults={
                            'synthesis_summary': run_data.get('synthesis_summary', ''),
                            'minority_report': run_data.get('minority_report', ''),
                            'polarization_index': run_data.get('polarization_index', 0.0),
                            'status': 'COMPLETED'
                        }
                    )
                    
                    run.responses.all().delete()

                    for resp in run_data.get('responses', []):
                        model = AIModel.objects.filter(api_identifier=resp['api_identifier']).first()
                        if model:
                            AIResponse.objects.create(
                                run=run,
                                model=model,
                                summary_sentence=resp.get('summary_sentence', ''),
                                normalized_score=resp.get('normalized_score'),
                                complex_forecast=resp.get('complex_forecast'),
                                cost=Decimal(str(resp.get('cost', 0)))
                            )
                    
                    # Ensure Question.latest_run is linked
                    q.latest_run = run
                    q.save()
                    
                    self.stdout.write(f"  [Run] Synced: {q.slug} (Responses: {run.responses.count()})")
                except Question.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"  [Skip] Question slug {run_data['question_slug']} not found."))