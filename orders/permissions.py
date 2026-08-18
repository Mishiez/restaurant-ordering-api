from rest_framework import permissions


class IsOwnerOrStaff(permissions.BasePermission):
    """
    Object-level permission: the order's owning customer, or any staff
    user, can access/modify. Anyone else is refused.

    Returns 403, not 404, on mismatch — deliberately not hiding
    existence of other users' orders behind a 404, per design doc §8.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.customer_id == request.user.id