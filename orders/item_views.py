from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Order, OrderItem
from .serializers import OrderItemSerializer


def _get_owned_pending_order(order_id, user):
    order = get_object_or_404(Order, id=order_id)
    if order.customer_id != user.id:
        raise PermissionDenied("Only the order's owner can modify its items.")
    if order.status != Order.Status.PENDING_PAYMENT:
        raise ValidationError(
            f"Cannot modify items on an order with status {order.status}. "
            "Items can only be changed while PENDING_PAYMENT."
        )
    return order


class OrderItemListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        order = _get_owned_pending_order(order_id, request.user)
        serializer = OrderItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        menu_item = serializer.validated_data['menu_item']
        OrderItem.objects.create(
            order=order,
            menu_item=menu_item,
            quantity=serializer.validated_data['quantity'],
            unit_price=menu_item.price,
        )
        order.recompute_total()
        return Response(OrderItemSerializer(order.items.last()).data, status=status.HTTP_201_CREATED)


class OrderItemDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, order_id, item_id):
        order = _get_owned_pending_order(order_id, request.user)
        item = get_object_or_404(OrderItem, id=item_id, order=order)
        serializer = OrderItemSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if 'quantity' in serializer.validated_data:
            item.quantity = serializer.validated_data['quantity']
            item.save(update_fields=['quantity'])
        order.recompute_total()
        return Response(OrderItemSerializer(item).data)

    def delete(self, request, order_id, item_id):
        order = _get_owned_pending_order(order_id, request.user)
        item = get_object_or_404(OrderItem, id=item_id, order=order)
        item.delete()
        order.recompute_total()
        return Response(status=status.HTTP_204_NO_CONTENT)