from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import MenuItem
from .permissions import IsStaffOrReadOnly
from .serializers import MenuItemSerializer


class MenuItemViewSet(viewsets.ModelViewSet):
    serializer_class = MenuItemSerializer
    # Both checks apply: must be authenticated at all, and if writing,
    # must be staff. Setting permission_classes here OVERRIDES the
    # global default from settings.py rather than adding to it, so
    # IsAuthenticated has to be listed explicitly here too — leaving
    # it out lets anonymous users slip through on GET requests.
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and user.is_staff:
            return MenuItem.objects.all()
        return MenuItem.objects.filter(available=True)