from django.urls import path
from .views import DashboardView, ProfileUpdateView

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('profile/edit/', ProfileUpdateView.as_view(), name='profile_edit'),
]