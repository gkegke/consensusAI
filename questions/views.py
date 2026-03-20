import logging
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, View, CreateView, ListView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Count
from .models import Question, HumanVote, AnonymousVote
from .services import process_vote
from .forms import QuestionSubmissionForm

logger = logging.getLogger(__name__)

class OwnerOnlyProposalMixin(UserPassesTestMixin):
    def test_func(self):
        question = self.get_object()
        return self.request.user == question.submitted_by and question.can_be_edited

class QuestionUpdateView(LoginRequiredMixin, OwnerOnlyProposalMixin, UpdateView):
    model = Question
    form_class = QuestionSubmissionForm
    template_name = 'questions/question_form.html'
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        question = form.save(commit=False)
        if question.status == 'REJECTED':
            question.status = 'IN_REVIEW'
        
        question.save()
        messages.success(self.request, "Question updated and resubmitted for review.")
        logger.info(f"USER_UPDATE | Q:{question.slug} | BY:{self.request.user.username}")
        return super().form_valid(form)

class QuestionDeleteView(LoginRequiredMixin, OwnerOnlyProposalMixin, DeleteView):
    model = Question
    template_name = 'questions/question_confirm_delete.html'
    success_url = reverse_lazy('dashboard')

    def delete(self, request, *args, **kwargs):
        question = self.get_object()
        logger.warning(f"USER_DELETE | Q:{question.slug} | BY:{self.request.user.username}")
        messages.success(request, "Question proposal deleted.")
        return super().delete(request, *args, **kwargs)

class ProposalFeedView(ListView):
    model = Question
    template_name = 'questions/proposal_feed.html'
    context_object_name = 'questions'
    paginate_by = 10
    
    def get_queryset(self):
        sort = self.request.GET.get('sort', 'trending')
        
        queryset = Question.objects.filter(status__in=['PROPOSED', 'IN_REVIEW']) \
            .annotate(upvote_count=Count('upvoters'))
        
        if sort == 'newest':
            return queryset.order_by('-created_at')
        return queryset.order_by('-upvote_count', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_sort'] = self.request.GET.get('sort', 'trending')
        return context

class QuestionCreateView(LoginRequiredMixin, CreateView):
    model = Question
    form_class = QuestionSubmissionForm
    template_name = 'questions/question_form.html'
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        question = form.save(commit=False)
        question.submitted_by = self.request.user
        question.status = 'IN_REVIEW'
        question.save()
        
        if 'choices' in form.cleaned_data:
            question.choices = form.cleaned_data['choices']
            question.save()

        messages.success(self.request, "Your question has been submitted for review!")
        logger.info(f"USER_SUBMIT | Q:{question.slug} | BY:{self.request.user.username}")
        return super().form_valid(form)

class UpvoteToggleView(LoginRequiredMixin, View):
    def post(self, request, slug, *args, **kwargs):
        question = get_object_or_404(Question, slug=slug)
        
        if request.user in question.upvoters.all():
            question.upvoters.remove(request.user)
            messages.info(request, "Upvote removed.")
            logger.info(f"UPVOTE_REMOVE | Q:{slug} | BY:{request.user.username}")
        else:
            question.upvoters.add(request.user)
            messages.success(request, "Question upvoted!")
            logger.info(f"UPVOTE_ADD | Q:{slug} | BY:{request.user.username}")
            
        # Robust redirect fallback for tests and headless requests
        referer = request.META.get('HTTP_REFERER')
        if referer:
            return redirect(referer)
        return redirect('question_detail', slug=slug)

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
            context['has_upvoted'] = request.user in question.upvoters.all()
        else:
            session_key = request.session.session_key
            if session_key:
                vote_qs = AnonymousVote.objects.filter(session_key=session_key, question=question)
                if vote_qs.exists():
                    has_voted = True
                    user_vote = vote_qs.first()

        context['has_voted'] = has_voted
        context['user_vote'] = user_vote
        
        is_owner_or_admin = request.user.is_staff or (request.user == question.submitted_by)
        context['can_view_results'] = has_voted or question.allow_skip_vote or is_owner_or_admin
        context['can_user_edit'] = (request.user == question.submitted_by) and question.can_be_edited
        
        return context

class VoteSubmitView(View):
    def post(self, request, slug, *args, **kwargs):
        question = get_object_or_404(Question, slug=slug)
        parsed_data = {'reasoning': request.POST.get('reasoning', '').strip()}

        if question.question_type in ['SUBJECTIVE_SLIDER', 'PREDICTIVE_BINARY']:
            try:
                parsed_data['score'] = float(request.POST.get('score', 50))
            except ValueError:
                parsed_data['score'] = 50.0
                 
        elif question.question_type == 'PREDICTIVE_CHOICE':
            names = request.POST.getlist('custom_names')
            values = request.POST.getlist('custom_values')
            complex_forecast = []
            for name, val in zip(names, values):
                try:
                    confidence = float(val)
                    if confidence > 0:
                        complex_forecast.append({"choice": name[:100], "confidence": confidence})
                except ValueError:
                    continue
            parsed_data['complex_forecast'] = complex_forecast

        success, message = process_vote(request, question, parsed_data)
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)

        return redirect('question_detail', slug=slug)