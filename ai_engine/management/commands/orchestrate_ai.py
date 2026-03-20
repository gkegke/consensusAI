import logging
import traceback
from decimal import Decimal
from django.db.models import Q
from concurrent.futures import ThreadPoolExecutor
from django.core.management.base import BaseCommand
from django.db import close_old_connections, transaction
from ai_engine.models import AIModel, ConsensusRun, AIResponse, OrchestrationLog
from ai_engine.services import AIOrchestratorService
from questions.models import Question

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Dispatches QUEUED or AUTO_POLL questions to AI models safely using DB-level locking."

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=3)
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        # CRITICAL - Atomic lock prevents multiple dynos from double-billing APIs
        with transaction.atomic():
            qs = Question.objects.select_for_update(skip_locked=True).filter(
                Q(orchestration_queued=True) | Q(is_auto_poll=True),
                status='ACTIVE'
            ).order_by('-ai_priority')[:options['limit']]
            
            targets = list(qs)
            
            if targets and not options['dry_run']:
                target_ids = [q.id for q in targets]
                # Reset the queue flag so they aren't picked up in the next minute
                Question.objects.filter(id__in=target_ids).update(orchestration_queued=False)
        
        if not targets:
            self.stdout.write("Queue empty or items locked by another process.")
            return

        total_processed = 0
        grand_cost = Decimal('0')
        error_details = []

        for question in targets:
            try:
                success, cost, msg = self.process_question(question, options['dry_run'])
                if success:
                    total_processed += 1
                    grand_cost += cost
                else:
                    error_details.append(f"Q: {question.slug} Failed: {msg}")
            except Exception as e:
                err_msg = f"CRITICAL_FAILURE | {question.slug} | {str(e)}"
                logger.error(err_msg, exc_info=True)
                error_details.append(err_msg)

        # Log Result for Admin Audit
        status = "SUCCESS" if total_processed == len(targets) else "PARTIAL" if total_processed > 0 else "FAILURE"
        
        if not options['dry_run']:
            OrchestrationLog.objects.create(
                task_name="orchestrate_ai",
                status=status,
                items_processed=total_processed,
                log_message="\n".join(error_details) if error_details else "All tasks completed successfully.",
                total_run_cost=grand_cost
            )

    def process_question(self, question, dry_run):
        # 1. Model Selection
        models_to_query = question.target_models.filter(is_active=True)
        if not models_to_query.exists():
            tags = question.model_group_tags or ['free']
            models_to_query = AIModel.objects.filter(is_active=True, tags__overlap=tags)[:3]

        if not models_to_query:
            return False, 0, "No active models matched criteria."

        if dry_run:
            self.stdout.write(f"DRY RUN: Would query {models_to_query.count()} models for {question.slug}")
            return True, 0, "Dry run"

        # 2. Initialize Run
        run = ConsensusRun.objects.create(question=question, status='PENDING')
        
        # 3. Parallel Querying
        with ThreadPoolExecutor(max_workers=3) as executor:
            for m in models_to_query:
                executor.submit(self.run_single_model, m, question, run)

        # 4. Synthesis
        run.refresh_from_db()
        if not run.responses.exists():
            run.status = 'FAILED'
            run.save()
            return False, 0, "Zero responses received from models."

        synthesis_dict, synth_cost = AIOrchestratorService.synthesize_run(run)
        
        if synthesis_dict:
            run.synthesis_summary = synthesis_dict.get('synthesis_summary', '')
            run.minority_report = synthesis_dict.get('minority_report', '')
            run.polarization_index = synthesis_dict.get('polarization_index', 0.0)
            run.status = 'COMPLETED'
            run.total_cost += Decimal(str(synth_cost))
            run.save()
            return True, run.total_cost, "Success"
        
        run.status = 'FAILED'
        run.save()
        return False, run.total_cost, "Synthesis model failed."

    def run_single_model(self, model_obj, question, run):
        try:
            close_old_connections()
            res_dict, cost = AIOrchestratorService.query_model(model_obj, question)
            if res_dict:
                AIResponse.objects.create(
                    run=run,
                    model=model_obj,
                    summary_sentence=res_dict.get('summary_sentence', ''),
                    normalized_score=res_dict.get('score'),
                    complex_forecast=res_dict.get('complex_forecast'),
                    is_refusal=res_dict.get('is_refusal', False),
                    cost=Decimal(str(cost))
                )
        except Exception:
            logger.error(f"THREAD_ERR | {model_obj.name} | {traceback.format_exc()}")
        finally:
            close_old_connections()