# Postman Testing Guide 

Manual request reference for demonstrating every pass criterion against a
running local server (`python manage.py runserver`, default
`http://127.0.0.1:8000`). Replace `<...>` placeholders with real tokens
and IDs from your own data.

## 1. Status codes — success, unauthorized, not found

### Success (200/201/204)

**GET menu list — 200**
```
GET http://127.0.0.1:8000/api/menu-items/
Authorization: Token <any valid token>
```

**Create menu item — 201**
```
POST http://127.0.0.1:8000/api/menu-items/
Authorization: Token <staff token>
Content-Type: application/json

{
  "name": "Status Code Test Item",
  "description": "",
  "price": "5.00",
  "available": true
}
```

**Create order — 201**
```
POST http://127.0.0.1:8000/api/orders/
Authorization: Token <customer token>
Content-Type: application/json

{
  "items": [
    {"menu_item_id": 1, "quantity": 2}
  ]
}
```

**Pay for order — 200**
```
POST http://127.0.0.1:8000/api/orders/{order_id}/pay/
Authorization: Token <customer token who owns this order>
```

**Delete an order item — 204**
```
DELETE http://127.0.0.1:8000/api/orders/{order_id}/items/{item_id}/
Authorization: Token <customer token who owns this order>
```

### Unauthorized — 401

Send with no `Authorization` header at all:
```
GET http://127.0.0.1:8000/api/orders/
```

### Not found — 404

```
GET http://127.0.0.1:8000/api/menu-items/999999/
Authorization: Token <any valid token>
```

## 2. Pagination

```
GET http://127.0.0.1:8000/api/menu-items/
Authorization: Token <any valid token>
```
Response includes `count`, `next`, `previous`, `results`. Needs 11+ menu
items in the database to see a second page.

```
GET http://127.0.0.1:8000/api/menu-items/?page=2
Authorization: Token <any valid token>
```

## 3. Filtering

```
GET http://127.0.0.1:8000/api/menu-items/?available=true
Authorization: Token <any valid token>
```
```
GET http://127.0.0.1:8000/api/menu-items/?search=burger
Authorization: Token <any valid token>
```
```
GET http://127.0.0.1:8000/api/orders/?status=PAID
Authorization: Token <staff token>
```

## 4. Non-owner cannot modify another user's object

Setup: create an order as customer A (see §1 "Create order" above), note
the `order_id`. Then switch to **customer B's** token for all of these:

```
GET http://127.0.0.1:8000/api/orders/{customer_A_order_id}/
Authorization: Token <customer B token>
```
→ 403

```
POST http://127.0.0.1:8000/api/orders/{customer_A_order_id}/items/
Authorization: Token <customer B token>
Content-Type: application/json

{
  "menu_item_id": 1,
  "quantity": 1
}
```
→ 403

```
POST http://127.0.0.1:8000/api/orders/{customer_A_order_id}/pay/
Authorization: Token <customer B token>
```
→ 403 (the object-level permission check blocks this before the
`pay()` method body's own ownership check ever runs)

```
GET http://127.0.0.1:8000/api/orders/
Authorization: Token <customer B token>
```
→ 200, and customer A's order does not appear in `results`

## 5. Validation — bad input

**Negative price — 400**
```
POST http://127.0.0.1:8000/api/menu-items/
Authorization: Token <staff token>
Content-Type: application/json

{
  "name": "Bad Price Item",
  "description": "",
  "price": "-1.00",
  "available": true
}
```

**Duplicate name — 400** (use a name that already exists in your menu)
```
POST http://127.0.0.1:8000/api/menu-items/
Authorization: Token <staff token>
Content-Type: application/json

{
  "name": "<an existing item's exact name>",
  "description": "",
  "price": "9.00",
  "available": true
}
```

**Unavailable item added to order — 400** (first create a menu item with
`"available": false`, note its id)
```
POST http://127.0.0.1:8000/api/orders/{order_id}/items/
Authorization: Token <customer token who owns this order>
Content-Type: application/json

{
  "menu_item_id": <unavailable item's id>,
  "quantity": 1
}
```

**Quantity zero — 400**
```
POST http://127.0.0.1:8000/api/orders/{order_id}/items/
Authorization: Token <customer token who owns this order>
Content-Type: application/json

{
  "menu_item_id": 1,
  "quantity": 0
}
```