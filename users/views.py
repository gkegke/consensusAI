import logging
from django.urls import reverse_lazy
from django.views.generic import TemplateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from .models import UserProfile
from questions.models import HumanVote

logger = logging.getLogger(__name__)

class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Displays the authenticated user's voting history and profile stats.
    Satisfies LO3 and Phase 2.1 Requirements.
    """
    template_name = 'users/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        base_votes = HumanVote.objects.filter(user=user)
        
        context['total_votes'] = base_votes.count()
        context['predictive_count'] = base_votes.filter(
            question__question_type__icontains='PREDICTIVE'
        ).count()
        
        context['needs_onboarding'] = not user.cai_profile.is_onboarded and context['total_votes'] == 0
        
        context['votes'] = base_votes.select_related(
            'question', 
            'question__latest_run'
        ).order_by('-created_at')[:50]
        
        logger.info(f"Dashboard: User {user.username} (Votes: {context['total_votes']})")
        return context

class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """
    Allows users to update their profile information.
    """
    model = UserProfile
    fields = ['bio']
    template_name = 'users/profile_form.html'
    success_url = reverse_lazy('dashboard')

    def get_object(self, queryset=None):
        return self.request.user.cai_profile

    def form_valid(self, form):
        # Once they save their profile, consider them onboarded
        profile = form.save(commit=False)
        profile.is_onboarded = True
        profile.save()
        
        messages.success(self.request, "Profile updated successfully.")
        logger.info(f"User {self.request.user.username} updated their bio and finished onboarding.")
        return super().form_valid(form)