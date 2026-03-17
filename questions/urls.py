from django.urls import path
from .views import QuestionDetailView, VoteSubmitView

urlpatterns = [
    path('<slug:slug>/', QuestionDetailView.as_view(), name='question_detail'),
    path('<slug:slug>/vote/', VoteSubmitView.as_view(), name='question_vote'),
]