from django.urls import path
from .views import (
    QuestionDetailView, 
    VoteSubmitView, 
    QuestionCreateView, 
    QuestionUpdateView,
    QuestionDeleteView,
    UpvoteToggleView,
    ProposalFeedView
)

urlpatterns = [
    path('submit/', QuestionCreateView.as_view(), name='question_submit'),
    path('proposals/', ProposalFeedView.as_view(), name='proposal_feed'),
    path('<slug:slug>/', QuestionDetailView.as_view(), name='question_detail'),
    path('<slug:slug>/edit/', QuestionUpdateView.as_view(), name='question_edit'),
    path('<slug:slug>/delete/', QuestionDeleteView.as_view(), name='question_delete'),
    path('<slug:slug>/vote/', VoteSubmitView.as_view(), name='question_vote'),
    path('<slug:slug>/upvote/', UpvoteToggleView.as_view(), name='question_upvote'),
]