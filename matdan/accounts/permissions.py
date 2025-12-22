from rest_framework import permissions

class IsAnonymousUser(permissions.BasePermission):
    """
    Custom permissions to only allow anonymous user to access a view
    """
    def has_permission(self, request, view):
        # The request is granted if the user is not authenticated
        return not request.user.is_authenticated