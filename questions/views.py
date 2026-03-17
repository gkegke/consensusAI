import logging
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, View
from django.contrib import messages
from .models import Question, HumanVote, AnonymousVote
from .services import process_vote

logger = logging.getLogger(__name__)

class QuestionDetailView(DetailView):
    model = Question
    template_name = 'questions/question_detail.html'
    context_object_name = 'question'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        question = self.object
        request = self.request
        
        has_voted = False
        user_vote = None

        if request.user.is_authenticated:
            vote_qs = HumanVote.objects.filter(user=request.user, question=question)
            if vote_qs.exists():
                has_voted = True
                user_vote = vote_qs.first()
        else:
            session_key = request.session.session_key
            if session_key:
                vote_qs = AnonymousVote.objects.filter(session_key=session_key, question=question)
                if vote_qs.exists():
                    has_voted = True
                    user_vote = vote_qs.first()

        context['has_voted'] = has_voted
        context['user_vote'] = user_vote
        context['can_view_results'] = has_voted or question.allow_skip_vote or question.status == 'ARCHIVED'
        
        return context

class VoteSubmitView(View):
    def post(self, request, slug, *args, **kwargs):
        question = get_object_or_404(Question, slug=slug)
        parsed_data = {
            'reasoning': request.POST.get('reasoning', '').strip()
        }

        if question.question_type in ['SUBJECTIVE_SLIDER', 'PREDICTIVE_BINARY']:
            try:
                parsed_data['score'] = float(request.POST.get('score', 0))
            except ValueError:
                parsed_data['score'] = 0.0
                 
        elif question.question_type == 'PREDICTIVE_CHOICE':
            names = request.POST.getlist('custom_names')
            values = request.POST.getlist('custom_values')
            
            complex_forecast = []
            for name, val in zip(names, values):
                try:
                    confidence = float(val)
                    if confidence > 0:
                        complex_forecast.append({
                            "choice": name[:100], 
                            "confidence": confidence
                        })
                except ValueError:
                    continue
            parsed_data['complex_forecast'] = complex_forecast

        success, message = process_vote(request, question, parsed_data)
        
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)

        return redirect('question_detail', slug=slug)