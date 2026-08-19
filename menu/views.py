from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated

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