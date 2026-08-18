from decimal import Decimal

from rest_framework import serializers

from menu.models import MenuItem

from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    menu_item_id = serializers.PrimaryKeyRelatedField(
        source='menu_item', queryset=MenuItem.objects.all(), write_only=True
    )
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id', 'menu_item_id', 'menu_item_name', 'quantity', 'unit_price',
        ]
        read_only_fields = ['id', 'unit_price']

    def validate_menu_item_id(self, menu_item):
        if not menu_item.available:
            raise serializers.ValidationError(
                f"{menu_item.name} is currently unavailable."
            )
        return menu_item


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, required=False)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer', 'status', 'total',
            'items', 'created_at', 'updated_at',
        ]
        # total, status, order_number, customer are never client-writable
        # on create/update through this serializer — total is always
        # server-computed, status changes only via the dedicated action
        # endpoints (pay/cancel/advance) built in Phase 4, order_number
        # is auto-generated, and customer is set from the request user.
        read_only_fields = [
            'id', 'order_number', 'customer', 'status', 'total',
            'created_at', 'updated_at',
        ]

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        request = self.context['request']
        order = Order.objects.create(customer=request.user, **validated_data)

        for item_data in items_data:
            menu_item = item_data['menu_item']
            OrderItem.objects.create(
                order=order,
                menu_item=menu_item,
                quantity=item_data['quantity'],
                unit_price=menu_item.price,
            )

        order.recompute_total()
        return order