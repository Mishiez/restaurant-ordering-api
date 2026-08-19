from django.db.models import ProtectedError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import MenuItem
from .permissions import IsStaffOrReadOnly
from .serializers import MenuItemSerializer


class MenuItemViewSet(viewsets.ModelViewSet):
    serializer_class = MenuItemSerializer
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['available']
    search_fields = ['name', 'description']

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and user.role == user.Role.STAFF:
            return MenuItem.objects.all().order_by('id')
        return MenuItem.objects.filter(available=True).order_by('id')

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            instance.delete()
        except ProtectedError:
            # Raised by on_delete=PROTECT on OrderItem.menu_item.
            # Without this catch, the exception propagates and DRF
            # returns a raw 500 — we want a clean 409 instead, per §9.
            return Response(
                {
                    "detail": (
                        f"Cannot delete '{instance.name}': it is referenced by "
                        "existing orders. Mark it unavailable instead."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)