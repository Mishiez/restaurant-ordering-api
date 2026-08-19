from django.urls import path
from rest_framework.routers import DefaultRouter

from .item_views import OrderItemDetailView, OrderItemListCreateView
from .views import OrderViewSet

router = DefaultRouter()
router.register('orders', OrderViewSet, basename='order')

urlpatterns = router.urls + [
    path('orders/<int:order_id>/items/', OrderItemListCreateView.as_view(), name='order-item-list'),
    path('orders/<int:order_id>/items/<int:item_id>/', OrderItemDetailView.as_view(), name='order-item-detail'),
]