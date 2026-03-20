from django.contrib import admin
from .models import AIModel, ConsensusRun, AIResponse, OrchestrationLog
from .forms import AIResponseAdminForm

class AIResponseInline(admin.TabularInline):
    model = AIResponse
    form = AIResponseAdminForm
    extra = 1
    fields = ('model', 'normalized_score', 'complex_forecast', 'summary_sentence', 'is_refusal', 'cost', 'is_manual_entry')

@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'developer', 'api_identifier', 'is_active', 'tag_list')
    list_filter = ('is_active', 'developer')
    search_fields = ('name', 'api_identifier', 'developer')
    
    def tag_list(self, obj):
        return ", ".join(obj.tags) if obj.tags else "-"

@admin.register(ConsensusRun)
class ConsensusRunAdmin(admin.ModelAdmin):
    list_display = ('question_link', 'created_at', 'total_cost', 'response_count')
    list_filter = ('prompt_version', 'created_at')
    readonly_fields = ('total_cost', 'created_at', 'updated_at')
    inlines = [AIResponseInline]

    def question_link(self, obj):
        from django.utils.html import format_html
        from django.urls import reverse
        url = reverse("admin:questions_question_change", args=[obj.question.id])
        return format_html('<a href="{}">{}</a>', url, obj.question.text)

    def response_count(self, obj):
        return obj.responses.count()

@admin.register(AIResponse)
class AIResponseAdmin(admin.ModelAdmin):
    form = AIResponseAdminForm
    list_display = ('run', 'model', 'normalized_score', 'is_manual_entry', 'cost')
    list_filter = ('is_refusal', 'is_manual_entry', 'model')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(OrchestrationLog)
class OrchestrationLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'status', 'items_processed', 'total_run_cost')
    readonly_fields = ('created_at', 'task_name', 'status', 'items_processed', 'log_message', 'total_run_cost')