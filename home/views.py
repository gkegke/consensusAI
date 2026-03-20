import logging
from collections import Counter
from django.views.generic import TemplateView
from django.db.models import Count, Q
from questions.models import Question

logger = logging.getLogger(__name__)

class HomePage(TemplateView):
    template_name = 'index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            # 1. Featured - Explicitly selected by Admin (The "Recruiter Path")
            # We prioritize those with AI runs so the USP is immediately visible.
            context['featured_questions'] = Question.objects.filter(
                is_featured=True, 
                status__in=['ACTIVE', 'PROPOSED']
            ).select_related('latest_run').order_by('-latest_run__created_at', '-created_at')[:3]
            
            featured_ids = [q.id for q in context['featured_questions']]

            # 2. Recently Analyzed (The "AI vs Crowd" USP Display)
            # Exclude featured to keep the feed fresh
            context['recently_analyzed'] = Question.objects.filter(
                latest_run__isnull=False, 
                status='ACTIVE'
            ).exclude(id__in=featured_ids).select_related('latest_run').order_by('-latest_run__created_at')[:4]
            
            # 3. Trending Proposals (Crowd sourcing logic)
            context['trending_proposals'] = Question.objects.filter(
                status='PROPOSED'
            ).exclude(id__in=featured_ids).annotate(
                upvote_count=Count('upvoters')
            ).order_by('-upvote_count', '-created_at')[:6]
            
            # 4. Extract Top Tags
            all_tags_lists = Question.objects.filter(
                status__in=['ACTIVE', 'PROPOSED']
            ).values_list('tags', flat=True)
            
            tag_counts = Counter([tag for sublist in all_tags_lists for tag in sublist if tag])
            context['popular_tags'] = [tag for tag, count in tag_counts.most_common(8)]

            logger.info("HOME_LOAD_SUCCESS | Context optimized for discovery.")
        except Exception as e:
            logger.error(f"HOME_LOAD_ERROR | {e}", exc_info=True)
            
        return context