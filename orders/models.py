import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT = 'PENDING_PAYMENT', 'Pending Payment'
        PAID = 'PAID', 'Paid'
        RECEIVED = 'RECEIVED', 'Received'
        PREPARING = 'PREPARING', 'Preparing'
        READY = 'READY', 'Ready'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='orders', on_delete=models.CASCADE
    )
    order_number = models.CharField(max_length=30, unique=True, editable=False)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING_PAYMENT
    )
    # Always server-computed from OrderItem lines, never accepted from
    # client input directly. Recomputed on every add/remove/quantity
    # change while status == PENDING_PAYMENT. Default 0 so a brand-new
    # order with no items yet still has a valid total.
    total = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self._generate_order_number()
        super().save(*args, **kwargs)

    def _generate_order_number(self):
        # ORD-<date>-<short unique suffix>. A uuid suffix rather than a
        # sequential counter avoids a race condition between two orders
        # created in the same request-second landing on the same
        # number, without needing a separate counter table.
        today = timezone.now().strftime('%Y%m%d')
        suffix = uuid.uuid4().hex[:6].upper()
        return f"ORD-{today}-{suffix}"

    def recompute_total(self):
        total = sum(
            (item.unit_price * item.quantity for item in self.items.all()),
            Decimal('0.00'),
        )
        self.total = total
        self.save(update_fields=['total', 'updated_at'])

    def __str__(self):
        return self.order_number


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    menu_item = models.ForeignKey('menu.MenuItem', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    # Snapshot of MenuItem.price at the moment this line was added, so a
    # later price change on the menu doesn't silently alter historical
    # orders that already included this item.
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)

    def save(self, *args, **kwargs):
        if self.unit_price is None:
            self.unit_price = self.menu_item.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity} x {self.menu_item.name} (Order {self.order.order_number})"