# Restaurant Ordering API
 
A Django REST Framework API for a self-service restaurant ordering system.
Customers browse the menu, build an order, pay (simulated), and track its
status. Staff manage menu availability and move orders through the kitchen
workflow. There is no bundled frontend — this is a pure JSON API, and any
client that can send HTTP requests (a web app, a mobile app, Postman) can
use it identically.
 
## Tech stack
 
- Python 3.12, Django 6.1, Django REST Framework
- `django-filter` for query filtering
- Token authentication (`rest_framework.authtoken`)
- SQLite (development)
## Setup
 
```bash
git clone https://github.com/Mishiez/restaurant-ordering-api.git
cd restaurant-ordering-api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
 
cp .env.example .env
# then edit .env and set a real SECRET_KEY
 
python manage.py migrate
python manage.py createsuperuser   # for admin site / staff testing
python manage.py runserver
```
 
The API is now running at `http://127.0.0.1:8000/`.
 
## Running tests
 
```bash
python manage.py test
```
 
68 tests across `core`, `accounts`, `menu`, and `orders`, covering success,
validation, unauthorized, not-found, and ownership cases for every endpoint.

## Manual testing reference

For a full list of Postman requests (method, headers, body) demonstrating
every gate pass criterion — status codes, pagination, filtering, the
non-owner ownership test, and validation — see
[`docs/postman-testing-guide.md`](docs/postman-testing-guide.md).
 
## Roles
 
- **Customer** — default role on registration. Can browse available menu
  items, create and manage their own orders, pay, cancel.
- **Staff** — can manage the menu, view all orders, and advance orders
  through the kitchen workflow. Staff accounts are not self-registrable;
  create one via `createsuperuser` or the Django admin, then set their
  `role` to `STAFF` (via `/admin/` or the shell — see note below).
> `createsuperuser` sets Django's built-in `is_staff`/`is_superuser` flags
> (admin-site access) but does **not** set this project's own `role` field,
> which is what all API permission checks actually use. A superuser still
> needs `role=STAFF` set explicitly to pass as staff through the API.
 
## Health check
 
`GET /api/ping/` — no auth required, returns `{"status": "ok"}`. Useful
for confirming the API is up (load balancers, uptime checks, or a
frontend's initial connectivity check).
 
## Authentication
 
Token-based. Include the token on every authenticated request:
 
```
Authorization: Token <your-token>
```
 
| Endpoint | Method | Auth required | Description |
|---|---|---|---|
| `/api/auth/register/` | POST | No | Create a customer account, returns a token |
| `/api/auth/login/` | POST | No | Returns a token for existing credentials |
| `/api/auth/logout/` | POST | Yes | Deletes the current token (invalidates it immediately) |
 
## Menu endpoints
 
| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/menu-items/` | GET | Yes | List menu items (customers see only `available=true`; staff see all) |
| `/api/menu-items/` | POST | Staff | Create a menu item |
| `/api/menu-items/{id}/` | GET | Yes | Retrieve one item |
| `/api/menu-items/{id}/` | PATCH | Staff | Update an item |
| `/api/menu-items/{id}/` | DELETE | Staff | Delete an item — returns `409 Conflict` if it's referenced by any existing order (mark `available=false` instead) |
 
**Filtering & search:**
- `?available=true` / `?available=false`
- `?search=<text>` — matches name or description
## Order endpoints
 
| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/orders/` | GET | Yes | List orders (customers see only their own; staff see all) |
| `/api/orders/` | POST | Yes | Create an order, optionally with an initial list of items |
| `/api/orders/{id}/` | GET | Owner or staff | Retrieve one order |
 
`PATCH /api/orders/{id}/` does not exist. Every `Order` field is either
read-only or changed through one of the explicit actions below — see
"Design decisions" for why.
 
**Filtering & ordering:**
- `?status=PAID` (or any status value)
- `?ordering=created_at` / `?ordering=-total` etc.
### Order item endpoints
 
Manage the contents of an order while it's still `PENDING_PAYMENT`. Once
an order moves past that status, its items are locked.
 
| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/orders/{order_id}/items/` | POST | Owner | Add an item to the order |
| `/api/orders/{order_id}/items/{item_id}/` | PATCH | Owner | Change an item's quantity |
| `/api/orders/{order_id}/items/{item_id}/` | DELETE | Owner | Remove an item from the order |
 
### Order actions
 
| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/orders/{id}/pay/` | POST | Owner | `PENDING_PAYMENT → PAID`. Rejects an empty order. |
| `/api/orders/{id}/cancel/` | POST | Owner | `PENDING_PAYMENT → CANCELLED` |
| `/api/orders/{id}/advance/` | POST | Staff | Moves the order one step through the kitchen workflow |
 
### Order status flow
 
```
PENDING_PAYMENT --pay()--> PAID --advance()--> RECEIVED --advance()--> PREPARING --advance()--> READY --advance()--> COMPLETED
       |
       --cancel()--> CANCELLED
```
 
Any transition not shown above is rejected with `400 Bad Request`.
 
## Error responses
 
Consistent shape across the API:
 
```json
{ "detail": "Chicken Burger is currently unavailable." }
```
 
Field-level validation errors use DRF's default format:
 
```json
{ "quantity": ["Ensure this value is greater than or equal to 1."] }
```
 
| Status | Meaning |
|---|---|
| 400 | Validation failure or illegal state transition |
| 401 | No/invalid authentication token |
| 403 | Authenticated, but not permitted (wrong role, or not the resource owner) |
| 404 | Resource doesn't exist (or, for menu items, exists but isn't visible to this role) |
| 409 | Request conflicts with current state (e.g. deleting a referenced menu item) |
 
## Design decisions
 
A few choices worth explaining, since they came from working through
real tradeoffs rather than following CRUD conventions by default:
 
- **`total` and `order_number` are always server-computed**, never
  accepted from client input. `total` is recalculated from line items on
  every add/edit/remove while `PENDING_PAYMENT`.
- **`unit_price` on each order item is a snapshot** taken when the item
  is added, not a live reference to the menu item's current price — so a
  later price change never retroactively alters a past order's total.
- **Deleting a `MenuItem` is blocked if it's referenced by any order**
  (`on_delete=PROTECT`), returning a clean `409` rather than destroying
  order history. Staff use `available=false` to remove an item from the
  customer-facing menu while keeping historical orders intact.
- **`PATCH /api/orders/{id}/` doesn't exist.** Every `Order` field is
  either read-only or changed through an explicit action — `pay`,
  `cancel`, `advance`, or the order-item endpoints. Once `items` moved to
  its own resource, a generic order-level PATCH had nothing legitimate
  left to modify, so it was removed rather than kept as an unused stub.
- **Order items can only be added, changed, or removed while
  `PENDING_PAYMENT`.** Once paid, the order has entered the kitchen
  workflow and its contents are locked.
- **Non-owner access returns `403`, not `404`**, on order detail views —
  a deliberate choice not to hide the existence of another user's order
  behind a not-found response.
- **`is_staff` (Django's built-in flag) and `role` (this project's own
  field) are different things.** `is_staff` controls Django admin access;
  every permission check in this API uses `role` instead. A superuser
  still needs `role=STAFF` set explicitly to act as staff through the API.
## Out of scope
 
- Real payment integration — `pay()` is a pure state-machine transition,
  no gateway, no webhook.
- A frontend. This API is designed to be consumed by one (React, mobile,
  etc.) but none is included.
 
