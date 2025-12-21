from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminOrReadOnly(BasePermission):
    """
    Allow access to only admin user
    """
    def has_permission(self, request, view):
        # allow read-only methods for any user.
        if request.method in SAFE_METHODS:
            return True
        # for write methods, check if the user id authenticated and an admin
        return bool(request.user and request.user.is_staff)