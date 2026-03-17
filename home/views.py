from django.shortcuts import render
from django.views.generic import ListView
from questions.models import Question

class HomePage(ListView):
    """
    Displays the active and proposed questions to draw users into the funnel.
    """
    model = Question
    template_name = 'index.html'
    context_object_name = 'questions'
    
    def get_queryset(self):
        return Question.objects.filter(status__in=['PROPOSED', 'ACTIVE']).order_by('-created_at')