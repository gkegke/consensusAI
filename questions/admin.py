from django.contrib import admin
from .models import Question, HumanVote, AnonymousVote

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'status', 'is_featured', 'is_auto_poll')
    list_filter = ('status', 'is_featured', 'is_auto_poll')
    search_fields = ('text', 'slug')
    prepopulated_fields = {'slug': ('text',)}

admin.site.register(HumanVote)
admin.site.register(AnonymousVote)