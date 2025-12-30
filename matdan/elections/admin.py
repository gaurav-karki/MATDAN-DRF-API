import logging

from django.contrib import admin

from .models import Candidate, Election

logger = logging.getLogger("elections")


class ElectionAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return super().has_add_permission(request)

    def has_change_permisssion(self, request, obj=None):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_staff or request.user.is_superuser

    def save_model(self, request, obj, form, change):
        if change:
            logger.info(
                f"Election updated by admin : {request.user.username} - {obj.id}"
            )
        else:
            logger.info(
                f"Election created by admin: {request.user.username} - {obj.id}"
            )
        super().save_model(request, obj, form, change)


class CandidateAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_staff or request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj)

    def save_model(self, request, obj, form, change):
        if change:
            logger.info(
                f"Candidate updated by admin: {request.user.username} - {obj.id}"
            )
        else:
            logger.info(
                f"Candidate added by admin : {request.user.username} - {obj.id}"
            )
        super().save_model(request, obj, form, change)


admin.site.register(Election, ElectionAdmin)
admin.site.register(Candidate)
