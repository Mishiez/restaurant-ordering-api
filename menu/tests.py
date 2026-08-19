from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import MenuItem

User = get_user_model()


class MenuItemTests(APITestCase):

    def setUp(self):
        self.staff_user = User.objects.create_user(
            username="staffuser", password="pass12345", role="STAFF"
        )
        self.customer_user = User.objects.create_user(
            username="customeruser", password="pass12345", is_staff=False
        )
        self.available_item = MenuItem.objects.create(
            name="Chicken Burger", price=Decimal("8.50"), available=True
        )
        self.unavailable_item = MenuItem.objects.create(
            name="Seasonal Soup", price=Decimal("5.00"), available=False
        )

    # ---- list visibility ----

    def test_customer_sees_only_available_items(self):
        self.client.force_authenticate(self.customer_user)
        response = self.client.get("/api/menu-items/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [item["name"] for item in response.data["results"]]
        self.assertIn("Chicken Burger", names)
        self.assertNotIn("Seasonal Soup", names)

    def test_staff_sees_all_items(self):
        self.client.force_authenticate(self.staff_user)
        response = self.client.get("/api/menu-items/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [item["name"] for item in response.data["results"]]
        self.assertIn("Chicken Burger", names)
        self.assertIn("Seasonal Soup", names)

    # ---- unauthorized ----

    def test_list_requires_authentication(self):
        response = self.client.get("/api/menu-items/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ---- staff-only write ----

    def test_staff_can_create_menu_item(self):
        self.client.force_authenticate(self.staff_user)
        response = self.client.post(
            "/api/menu-items/",
            {"name": "Fries", "description": "", "price": "3.00", "available": True},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(MenuItem.objects.filter(name="Fries").exists())

    def test_customer_cannot_create_menu_item(self):
        self.client.force_authenticate(self.customer_user)
        response = self.client.post(
            "/api/menu-items/",
            {"name": "Fries", "description": "", "price": "3.00", "available": True},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_customer_cannot_update_menu_item(self):
        self.client.force_authenticate(self.customer_user)
        response = self.client.patch(
            f"/api/menu-items/{self.available_item.id}/", {"price": "9.99"}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_customer_cannot_delete_menu_item(self):
        self.client.force_authenticate(self.customer_user)
        response = self.client.delete(f"/api/menu-items/{self.available_item.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ---- validation ----

    def test_price_must_be_positive(self):
        self.client.force_authenticate(self.staff_user)
        response = self.client.post(
            "/api/menu-items/",
            {"name": "Bad Item", "description": "", "price": "-1.00", "available": True},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("price", response.data)

    def test_price_zero_is_rejected(self):
        self.client.force_authenticate(self.staff_user)
        response = self.client.post(
            "/api/menu-items/",
            {"name": "Bad Item", "description": "", "price": "0.00", "available": True},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ---- not found ----

    def test_retrieve_nonexistent_item_returns_404(self):
        self.client.force_authenticate(self.customer_user)
        response = self.client.get("/api/menu-items/99999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ---- customer cannot see unavailable item detail either ----

    def test_customer_cannot_retrieve_unavailable_item(self):
        self.client.force_authenticate(self.customer_user)
        response = self.client.get(f"/api/menu-items/{self.unavailable_item.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)




class MenuItemFilteringTests(APITestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(username="filterstaff", password="pass12345", role="STAFF")
        for i in range(15):
            MenuItem.objects.create(name=f"Item {i}", price=Decimal("5.00"), available=(i % 2 == 0))

    def test_filter_by_available(self):
        self.client.force_authenticate(self.staff_user)
        response = self.client.get("/api/menu-items/?available=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(all(item["available"] for item in response.data["results"]))

    def test_search_by_name(self):
        self.client.force_authenticate(self.staff_user)
        response = self.client.get("/api/menu-items/?search=Item 1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data["results"]) >= 1)

    def test_list_is_paginated(self):
        self.client.force_authenticate(self.staff_user)
        response = self.client.get("/api/menu-items/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)
        # 15 items created, PAGE_SIZE=10, so first page should have 10
        self.assertEqual(len(response.data["results"]), 10)
        self.assertEqual(response.data["count"], 15)




class MenuItemStaffActionTests(APITestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(username="actionstaff", password="pass12345", role="STAFF")
        self.customer = User.objects.create_user(username="actioncustomer", password="pass12345")
        self.item = MenuItem.objects.create(name="Salad", price=Decimal("6.00"), available=True)

    def test_staff_can_update_menu_item(self):
        self.client.force_authenticate(self.staff_user)
        response = self.client.patch(f"/api/menu-items/{self.item.id}/", {"price": "7.50"})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.item.refresh_from_db()
        self.assertEqual(self.item.price, Decimal("7.50"))

    def test_staff_can_delete_unreferenced_menu_item(self):
        self.client.force_authenticate(self.staff_user)
        response = self.client.delete(f"/api/menu-items/{self.item.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(MenuItem.objects.filter(id=self.item.id).exists())

    def test_cannot_delete_menu_item_referenced_by_order(self):
        from orders.models import Order, OrderItem
        order = Order.objects.create(customer=self.customer)
        OrderItem.objects.create(order=order, menu_item=self.item, quantity=1, unit_price=self.item.price)

        self.client.force_authenticate(self.staff_user)
        response = self.client.delete(f"/api/menu-items/{self.item.id}/")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT, response.data)
        self.assertTrue(MenuItem.objects.filter(id=self.item.id).exists())

    def test_update_nonexistent_menu_item_returns_404(self):
        self.client.force_authenticate(self.staff_user)
        response = self.client.patch("/api/menu-items/99999/", {"price": "1.00"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)