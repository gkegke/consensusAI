from django.contrib import admin
from django.db.models import Count
from .models import Question, HumanVote, AnonymousVote

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Core Content', {
            'fields': ('text', 'slug', 'context', 'question_type', 'choices')
        }),
        ('Moderation & Status', {
            'fields': ('status', 'admin_feedback', 'is_featured', 'is_auto_poll')
        }),
        ('Resolution Logic', {
            'fields': ('resolution_state', 'resolution_date', 'resolved_truth')
        }),
        ('AI Configuration', {
            'fields': ('target_models', 'latest_run', 'requires_web_search')
        }),
        ('Metadata', {
            'fields': ('submitted_by', 'tags', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    list_display = ('text', 'status', 'upvote_count', 'vote_count', 'is_auto_poll', 'created_at')
    list_filter = ('status', 'is_featured', 'is_auto_poll', 'question_type')
    search_fields = ('text', 'slug', 'context', 'submitted_by__username')
    prepopulated_fields = {'slug': ('text',)}
    autocomplete_fields = ['target_models']
    readonly_fields = ('created_at', 'updated_at')
    
    actions = ['make_active', 'make_proposed', 'make_rejected', 'make_in_review']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _upvote_count=Count('upvoters', distinct=True),
            _vote_count=Count('verified_votes', distinct=True) + Count('public_votes', distinct=True)
        )

    @admin.display(ordering='_upvote_count', description='Upvotes')
    def upvote_count(self, obj):
        return obj._upvote_count

    @admin.display(ordering='_vote_count', description='Total Votes')
    def vote_count(self, obj):
        return obj._vote_count

    @admin.action(description='Mark selected as ACTIVE (Enable AI)')
    def make_active(self, request, queryset):
        queryset.update(status='ACTIVE')

    @admin.action(description='Mark selected as PROPOSED (Halt AI / Approve Draft)')
    def make_proposed(self, request, queryset):
        queryset.update(status='PROPOSED')
        
    @admin.action(description='Mark selected as REJECTED (Needs Edits)')
    def make_rejected(self, request, queryset):
        queryset.update(status='REJECTED')

    @admin.action(description='Mark selected as IN_REVIEW (Waitlist)')
    def make_in_review(self, request, queryset):
        queryset.update(status='IN_REVIEW')