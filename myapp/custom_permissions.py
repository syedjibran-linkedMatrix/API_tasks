from rest_framework import permissions

class IsProjectManagerOrReadOnly(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.manager == request.user or request.user.is_staff
