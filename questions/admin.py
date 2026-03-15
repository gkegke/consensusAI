from django.contrib import admin
from .models import Question, HumanVote, AnonymousVote

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'status', 'is_featured', 'is_auto_poll', 'created_at')
    list_filter = ('status', 'is_featured', 'is_auto_poll', 'created_at')
    search_fields = ('text', 'slug', 'context')
    prepopulated_fields = {'slug': ('text',)}
    
    # <important importance="8/10">
    # Custom Admin actions to rapidly approve community 'Proposed' questions into the AI Pipeline.
    # </important>
    actions =['make_active', 'make_proposed']

    @admin.action(description='Mark selected questions as ACTIVE (Enable AI)')
    def make_active(self, request, queryset):
        queryset.update(status='ACTIVE')

    @admin.action(description='Mark selected questions as PROPOSED (Halt AI)')
    def make_proposed(self, request, queryset):
        queryset.update(status='PROPOSED')

@admin.register(HumanVote)
class HumanVoteAdmin(admin.ModelAdmin):
    list_display = ('question', 'user', 'score', 'created_at')
    list_filter = ('question', 'created_at')
    search_fields = ('user__username', 'question__text')

@admin.register(AnonymousVote)
class AnonymousVoteAdmin(admin.ModelAdmin):
    list_display = ('question', 'session_key', 'score', 'ip_address', 'created_at')
    list_filter = ('question', 'created_at')
    search_fields = ('session_key', 'ip_address')