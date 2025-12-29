from django.contrib import admin
from .models import User
import logging

logger = logging.getLogger('accounts')

class UserAdmin(admin.ModelAdmin):

    def has_add_permission(self, request):
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj = None):
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj = None):
        return request.user.is_superuser
    
    def has_view_permission(self, request, obj = None):
        return request.user.is_superuser or request.user.is_staff
    
    def save_model(self, request, obj, form, change):
        if change:
            logger.info(f'User updated by admin: {request.user.username} - {obj.username}')
        else:
            logger.info(f"User created by admin: {request.user.username}- {obj.username}")
        super().save_model(request, obj, form, change)

admin.site.register(User, UserAdmin)