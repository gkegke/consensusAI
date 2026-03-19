from django.contrib import admin
from .models import AIModel, ConsensusRun, AIResponse

@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'developer', 'api_identifier', 'is_active')
    list_filter = ('is_active', 'developer')
    search_fields = ('name', 'api_identifier')
    
@admin.register(ConsensusRun)
class ConsensusRunAdmin(admin.ModelAdmin):
    list_display = ('question', 'created_at', 'total_cost', 'polarization_index')
    list_filter = ('prompt_version', 'created_at')
    search_fields = ('question__text',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(AIResponse)
class AIResponseAdmin(admin.ModelAdmin):
    list_display = ('run', 'model', 'normalized_score', 'selected_choice', 'is_refusal', 'cost')
    list_filter = ('is_refusal', 'model', 'run__question__question_type')
    
    readonly_fields = ('created_at', 'updated_at')