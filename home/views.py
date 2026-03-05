from django.shortcuts import render
from django.views.generic import TemplateView

# Importance: Medium - Basic view to test template rendering
class HomePage(TemplateView):
    """
    Displays home page
    """
    template_name = 'index.html'