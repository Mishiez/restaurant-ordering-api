from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Order
from .permissions import IsOwnerOrStaff
from .serializers import OrderSerializer


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrStaff]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Order.objects.all()
        if self.action == 'list':
            # Restrict the collection itself to "my orders" here.
            return Order.objects.filter(customer=user)
        # For retrieve/update/etc, return the full queryset and let
        # IsOwnerOrStaff.has_object_permission decide access. If we
        # filtered here too, a non-owner's order would never be found
        # in the queryset at all, and DRF would 404 before the
        # permission class gets a chance to run — silently turning
        # our intended 403 into a 404 (see design doc §8's note on
        # this exact ambiguity; we're deliberately choosing 403).
        return Order.objects.all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context