from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Order
from .permissions import IsOwnerOrStaff
from .serializers import OrderSerializer
from .transitions import NEXT_STAFF_STATUS, validate_status_transition


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrStaff]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Order.objects.all()
        if self.action == 'list':
            return Order.objects.filter(customer=user)
        return Order.objects.all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        order = self.get_object()
        if order.customer_id != request.user.id:
            # Object-level permission already blocks non-owners from
            # reaching this point via get_object(), but staff *can*
            # reach it (IsOwnerOrStaff allows staff through) — and
            # paying isn't a staff action, so we explicitly exclude
            # staff here rather than relying on ownership alone.
            raise ValidationError("Only the order's owner can pay for it.")
        validate_status_transition(order.status, Order.Status.PAID)
        if not order.items.exists():
            raise ValidationError("Cannot pay for an empty order.")
        order.status = Order.Status.PAID
        order.save(update_fields=['status', 'updated_at'])
        return Response(OrderSerializer(order, context=self.get_serializer_context()).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.customer_id != request.user.id:
            raise ValidationError("Only the order's owner can cancel it.")
        validate_status_transition(order.status, Order.Status.CANCELLED)
        order.status = Order.Status.CANCELLED
        order.save(update_fields=['status', 'updated_at'])
        return Response(OrderSerializer(order, context=self.get_serializer_context()).data)

    @action(detail=True, methods=['post'])
    def advance(self, request, pk=None):
        order = self.get_object()
        if not request.user.is_staff:
            raise ValidationError("Only staff can advance order status.")
        next_status = NEXT_STAFF_STATUS.get(order.status)
        if next_status is None:
            raise ValidationError(
                f"Order in status {order.status} cannot be advanced further."
            )
        validate_status_transition(order.status, next_status)
        order.status = next_status
        order.save(update_fields=['status', 'updated_at'])
        return Response(OrderSerializer(order, context=self.get_serializer_context()).data)