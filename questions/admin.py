from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html
from .models import Question, HumanVote, AnonymousVote

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Core Content', {
            'fields': ('text', 'slug', 'context', 'question_type', 'choices')
        }),
        ('Moderation & Status', {
            'fields': ('status', 'admin_feedback', 'is_featured')
        }),
        ('AI Configuration & Execution', {
            'fields': ('orchestration_queued', 'ai_priority', 'is_auto_poll', 'target_models', 'model_group_tags', 'requires_web_search', 'latest_run')
        }),
        ('Resolution Logic', {
            'fields': ('resolution_state', 'resolution_date', 'resolved_truth')
        }),
        ('Metadata', {
            'fields': ('submitted_by', 'tags', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Combined List Display: Metrics + Queue Status
    list_display = ('text_truncated', 'status', 'queue_indicator', 'upvote_count', 'ai_priority', 'is_auto_poll')
    list_filter = ('status', 'orchestration_queued', 'is_auto_poll', 'question_type')
    list_editable = ('ai_priority', 'status')
    search_fields = ('text', 'slug', 'context')
    prepopulated_fields = {'slug': ('text',)}
    
    # Works now because AIModelAdmin has search_fields
    autocomplete_fields = ['target_models']
    readonly_fields = ('created_at', 'updated_at')
    
    actions = ['make_active', 'make_proposed', 'force_orchestration', 'dequeue_from_orchestration']

    def text_truncated(self, obj):
        return obj.text[:60] + "..." if len(obj.text) > 60 else obj.text
    text_truncated.short_description = "Question"

    def queue_indicator(self, obj):
        if obj.orchestration_queued:
            return format_html('<span style="color: #ff9800; font-weight: bold;">⌛ IN QUEUE</span>')
        if obj.latest_run:
            return format_html('<span style="color: #2e7d32;">✅ COMPLETE</span>')
        return format_html('<span style="color: #9e9e9e;">—</span>')
    queue_indicator.short_description = "AI Orchestration"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _upvote_count=Count('upvoters', distinct=True)
        )

    @admin.display(ordering='_upvote_count', description='Upvotes')
    def upvote_count(self, obj):
        return obj._upvote_count

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and 'latest_run' in form.base_fields:
            form.base_fields['latest_run'].queryset = obj.runs.all().order_by('-created_at')
        return form

    # --- Actions ---

    @admin.action(description='Add to AI Queue Now (Mark Active)')
    def force_orchestration(self, request, queryset):
        updated = queryset.update(orchestration_queued=True, status='ACTIVE')
        self.message_user(request, f"{updated} questions added to next orchestration run.")

    @admin.action(description='Remove from Queue')
    def dequeue_from_orchestration(self, request, queryset):
        updated = queryset.update(orchestration_queued=False)
        self.message_user(request, f"{updated} questions removed from queue.")

    @admin.action(description='Mark as ACTIVE')
    def make_active(self, request, queryset):
        queryset.update(status='ACTIVE')

    @admin.action(description='Mark as PROPOSED')
    def make_proposed(self, request, queryset):
        queryset.update(status='PROPOSED')

@admin.register(HumanVote)
class HumanVoteAdmin(admin.ModelAdmin):
    list_display = ('question', 'user', 'score', 'created_at')
    list_filter = ('question__question_type',)
    search_fields = ('user__username', 'question__text')

@admin.register(AnonymousVote)
class AnonymousVoteAdmin(admin.ModelAdmin):
    list_display = ('question', 'session_key', 'score', 'ip_address', 'created_at')
    readonly_fields = ('ip_address', 'user_agent')