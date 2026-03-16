from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_onboarded', 'created_at')
    search_fields = ('user__username', 'user__email')
    list_filter = ('is_onboarded',)
    readonly_fields = ('id', 'created_at', 'updated_at')