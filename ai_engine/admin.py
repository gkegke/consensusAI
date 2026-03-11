from django.contrib import admin
from .models import AIModel, ConsensusRun, AIResponse

@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'developer', 'is_active')
    list_filter = ('is_active', 'developer')

admin.site.register(ConsensusRun)
admin.site.register(AIResponse)