from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from menu.models import MenuItem

from .models import Order, OrderItem

User = get_user_model()


class OrderCreationTests(APITestCase):
    def setUp(self):
        self.customer_a = User.objects.create_user(username="customerA", password="pass12345")
        self.customer_b = User.objects.create_user(username="customerB", password="pass12345")
        self.staff_user = User.objects.create_user(username="staffuser", password="pass12345", role="STAFF")
        self.burger = MenuItem.objects.create(name="Burger", price=Decimal("8.50"), available=True)
        self.fries = MenuItem.objects.create(name="Fries", price=Decimal("3.00"), available=True)
        self.soup = MenuItem.objects.create(name="Soup", price=Decimal("5.00"), available=False)

    def test_create_order_with_items_computes_total_server_side(self):
        self.client.force_authenticate(self.customer_a)
        payload = {
            "items": [
                {"menu_item_id": self.burger.id, "quantity": 2},
                {"menu_item_id": self.fries.id, "quantity": 1},
            ]
        }
        response = self.client.post("/api/orders/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        order = Order.objects.get(id=response.data["id"])
        self.assertEqual(order.total, Decimal("20.00"))
        self.assertEqual(order.customer, self.customer_a)
        self.assertEqual(order.status, "PENDING_PAYMENT")
        self.assertTrue(order.order_number.startswith("ORD-"))

    def test_client_supplied_total_is_ignored(self):
        self.client.force_authenticate(self.customer_a)
        payload = {
            "total": "999999.00",
            "items": [{"menu_item_id": self.burger.id, "quantity": 1}],
        }
        response = self.client.post("/api/orders/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        order = Order.objects.get(id=response.data["id"])
        self.assertEqual(order.total, Decimal("8.50"))

    def test_client_supplied_status_is_ignored(self):
        self.client.force_authenticate(self.customer_a)
        payload = {
            "status": "COMPLETED",
            "items": [{"menu_item_id": self.burger.id, "quantity": 1}],
        }
        response = self.client.post("/api/orders/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        order = Order.objects.get(id=response.data["id"])
        self.assertEqual(order.status, "PENDING_PAYMENT")

    def test_cannot_add_unavailable_menu_item(self):
        self.client.force_authenticate(self.customer_a)
        payload = {"items": [{"menu_item_id": self.soup.id, "quantity": 1}]}
        response = self.client.post("/api/orders/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_quantity_must_be_at_least_one(self):
        self.client.force_authenticate(self.customer_a)
        payload = {"items": [{"menu_item_id": self.burger.id, "quantity": 0}]}
        response = self.client.post("/api/orders/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_price_change_after_order_does_not_alter_historical_order(self):
        self.client.force_authenticate(self.customer_a)
        payload = {"items": [{"menu_item_id": self.burger.id, "quantity": 1}]}
        response = self.client.post("/api/orders/", payload, format="json")
        order = Order.objects.get(id=response.data["id"])
        original_total = order.total

        self.burger.price = Decimal("50.00")
        self.burger.save()

        order.refresh_from_db()
        self.assertEqual(order.total, original_total)


class OrderOwnershipTests(APITestCase):

    def setUp(self):
        self.customer_a = User.objects.create_user(username="customerA", password="pass12345")
        self.customer_b = User.objects.create_user(username="customerB", password="pass12345")
        self.staff_user = User.objects.create_user(username="staffuser", password="pass12345", role="STAFF")
        self.burger = MenuItem.objects.create(name="Burger", price=Decimal("8.50"), available=True)

        self.client.force_authenticate(self.customer_a)
        response = self.client.post(
            "/api/orders/",
            {"items": [{"menu_item_id": self.burger.id, "quantity": 1}]},
            format="json",
        )
        self.order_id = response.data["id"]
        self.client.force_authenticate(user=None)

    def test_non_owner_cannot_view_order(self):
        self.client.force_authenticate(self.customer_b)
        response = self.client.get(f"/api/orders/{self.order_id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_owner_cannot_patch_order(self):
        self.client.force_authenticate(self.customer_b)
        response = self.client.patch(f"/api/orders/{self.order_id}/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_view_order(self):
        self.client.force_authenticate(self.customer_a)
        response = self.client.get(f"/api/orders/{self.order_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_staff_can_view_any_order(self):
        self.client.force_authenticate(self.staff_user)
        response = self.client.get(f"/api/orders/{self.order_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_customer_list_shows_only_own_orders(self):
        self.client.force_authenticate(self.customer_b)
        response = self.client.get("/api/orders/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_list_requires_authentication(self):
        response = self.client.get("/api/orders/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class OrderStateMachineTests(APITestCase):

    def setUp(self):
        self.customer = User.objects.create_user(username="customer", password="pass12345")
        self.other_customer = User.objects.create_user(username="other", password="pass12345")
        self.staff_user = User.objects.create_user(username="staff", password="pass12345", role="STAFF")
        self.burger = MenuItem.objects.create(name="Burger", price=Decimal("8.50"), available=True)

    def make_order(self, user=None):
        user = user or self.customer
        self.client.force_authenticate(user)
        response = self.client.post(
            "/api/orders/",
            {"items": [{"menu_item_id": self.burger.id, "quantity": 1}]},
            format="json",
        )
        order = Order.objects.get(id=response.data["id"])
        self.client.force_authenticate(user=None)
        return order

    # ---- legal transitions ----

    def test_pending_payment_to_paid_via_pay(self):
        order = self.make_order()
        self.client.force_authenticate(self.customer)
        response = self.client.post(f"/api/orders/{order.id}/pay/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        order.refresh_from_db()
        self.assertEqual(order.status, "PAID")

    def test_pending_payment_to_cancelled_via_cancel(self):
        order = self.make_order()
        self.client.force_authenticate(self.customer)
        response = self.client.post(f"/api/orders/{order.id}/cancel/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        order.refresh_from_db()
        self.assertEqual(order.status, "CANCELLED")

    def test_paid_to_received_via_advance(self):
        order = self.make_order()
        order.status = "PAID"
        order.save()
        self.client.force_authenticate(self.staff_user)
        response = self.client.post(f"/api/orders/{order.id}/advance/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        order.refresh_from_db()
        self.assertEqual(order.status, "RECEIVED")

    def test_received_to_preparing_via_advance(self):
        order = self.make_order()
        order.status = "RECEIVED"
        order.save()
        self.client.force_authenticate(self.staff_user)
        response = self.client.post(f"/api/orders/{order.id}/advance/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        order.refresh_from_db()
        self.assertEqual(order.status, "PREPARING")

    def test_preparing_to_ready_via_advance(self):
        order = self.make_order()
        order.status = "PREPARING"
        order.save()
        self.client.force_authenticate(self.staff_user)
        response = self.client.post(f"/api/orders/{order.id}/advance/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        order.refresh_from_db()
        self.assertEqual(order.status, "READY")

    def test_ready_to_completed_via_advance(self):
        order = self.make_order()
        order.status = "READY"
        order.save()
        self.client.force_authenticate(self.staff_user)
        response = self.client.post(f"/api/orders/{order.id}/advance/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        order.refresh_from_db()
        self.assertEqual(order.status, "COMPLETED")

    # ---- illegal transitions ----

    def test_cancelled_cannot_be_advanced(self):
        order = self.make_order()
        order.status = "CANCELLED"
        order.save()
        self.client.force_authenticate(self.staff_user)
        response = self.client.post(f"/api/orders/{order.id}/advance/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_completed_cannot_be_advanced_again(self):
        order = self.make_order()
        order.status = "COMPLETED"
        order.save()
        self.client.force_authenticate(self.staff_user)
        response = self.client.post(f"/api/orders/{order.id}/advance/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pending_payment_cannot_skip_straight_to_preparing(self):
        order = self.make_order()
        self.client.force_authenticate(self.staff_user)
        response = self.client.post(f"/api/orders/{order.id}/advance/")
        # PENDING_PAYMENT has no entry in NEXT_STAFF_STATUS at all —
        # staff can't advance an order that hasn't been paid for yet.
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_paid_order_cannot_be_paid_again(self):
        order = self.make_order()
        order.status = "PAID"
        order.save()
        self.client.force_authenticate(self.customer)
        response = self.client.post(f"/api/orders/{order.id}/pay/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_paid_order_cannot_be_cancelled(self):
        order = self.make_order()
        order.status = "PAID"
        order.save()
        self.client.force_authenticate(self.customer)
        response = self.client.post(f"/api/orders/{order.id}/cancel/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ---- §9 validation rules ----

    def test_cannot_pay_for_empty_order(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post("/api/orders/", {"items": []}, format="json")
        order_id = response.data["id"]
        response = self.client.post(f"/api/orders/{order_id}/pay/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ---- permission rules on the actions themselves ----

    def test_non_owner_cannot_pay_for_order(self):
        order = self.make_order()
        self.client.force_authenticate(self.other_customer)
        response = self.client.post(f"/api/orders/{order.id}/pay/")
        self.assertIn(response.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN))

    def test_customer_cannot_advance_order(self):
        order = self.make_order()
        order.status = "PAID"
        order.save()
        self.client.force_authenticate(self.customer)
        response = self.client.post(f"/api/orders/{order.id}/advance/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_staff_cannot_pay_for_customer_order(self):
        order = self.make_order()
        self.client.force_authenticate(self.staff_user)
        response = self.client.post(f"/api/orders/{order.id}/pay/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)