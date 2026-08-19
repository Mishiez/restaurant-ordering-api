from rest_framework import permissions


class IsOwnerOrStaff(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        if request.user.role == request.user.Role.STAFF:
            return True
        return obj.customer_id == request.user.id