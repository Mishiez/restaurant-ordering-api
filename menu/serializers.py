from rest_framework import serializers

from .models import MenuItem


class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = [
            'id', 'name', 'description', 'price', 'available',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0.")
        return value