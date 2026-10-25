"""Savora API views.

The legacy schema uses unmanaged MySQL tables, so all SQL is parameterized and
schema additions live in the explicit `migrate_savora_schema` management command.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import secrets
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from functools import wraps

import razorpay
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core import signing
from django.db import connection, transaction
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from openai import OpenAI

logger = logging.getLogger(__name__)
TOKEN_SALT = "savora-api-token-v1"
TOKEN_MAX_AGE_SECONDS = 60 * 60 * 12
MAX_CART_QUANTITY = 25
MAX_ORDER_LINES = 30
MAX_ORDER_ITEMS = 80
VALID_ORDER_STATUSES = {"placed", "confirmed", "preparing", "out-for-delivery", "delivered", "cancelled"}
VALID_STATUS_TRANSITIONS = {
    "awaiting_payment": {"cancelled"},
    "placed": {"confirmed", "cancelled"},
    "confirmed": {"preparing", "cancelled"},
    "preparing": {"out-for-delivery", "delivered", "cancelled"},
    "out-for-delivery": {"delivered"},
    "delivered": set(),
    "cancelled": set(),
}


def _json_body(request):
    try:
        if not request.body:
            return {}
        data = json.loads(request.body.decode("utf-8"))
        return data if isinstance(data, dict) else None
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _error(message, status=400, **extra):
    return JsonResponse({"success": False, "error": message, **extra}, status=status)


def _issue_token(user_id, token_version=0):
    return signing.dumps({"uid": int(user_id), "ver": int(token_version or 0)}, salt=TOKEN_SALT, compress=True)


def _is_configured_secret(value):
    value = str(value or "").strip()
    lowered = value.lower()
    return bool(value) and not any(marker in lowered for marker in ("replace-with", "replace_me", "placeholder", "your-secret", "your-key"))


def _valid_razorpay_webhook_signature(body, secret, received_signature):
    if not _is_configured_secret(secret) or not received_signature:
        return False
    expected = hmac.new(str(secret).encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, str(received_signature))


def _user_from_token(request):
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    token = header[7:].strip()
    if not token or len(token) > 4096:
        return None
    try:
        payload = signing.loads(token, salt=TOKEN_SALT, max_age=TOKEN_MAX_AGE_SECONDS)
        user_id = int(payload.get("uid"))
        token_version = int(payload.get("ver", 0))
    except (signing.BadSignature, signing.SignatureExpired, TypeError, ValueError, AttributeError):
        return None
    with connection.cursor() as cursor:
        cursor.execute("SELECT user_id, name, email, token_version FROM users WHERE user_id = %s LIMIT 1", [user_id])
        row = cursor.fetchone()
    if not row or int(row[3] or 0) != token_version:
        return None
    return {"user_id": int(row[0]), "name": row[1], "email": row[2]}


def _require_user(request):
    user = _user_from_token(request)
    if not user:
        return None, _error("Sign in to continue. Your session may have expired.", 401, code="authentication_required")
    return user, None


def _valid_session_id(value):
    return isinstance(value, str) and 8 <= len(value) <= 128 and re.fullmatch(r"[A-Za-z0-9_.:-]+", value) is not None


def _valid_guest_session_id(value):
    # Authenticated cart keys are predictable (`user_<id>`) and must never be
    # accepted as guest-supplied IDs; otherwise catalogue quantities could leak.
    return _valid_session_id(value) and not value.startswith("user_")


def _user_cart_key(user_id):
    return f"user_{int(user_id)}"


def _food_row_to_json(columns, row):
    item = dict(zip(columns, row))
    # Keep API casing compatible with the existing React code.
    aliases = {
        "FoodID": ("FoodID", "foodid", "food_id"),
        "FoodName": ("FoodName", "foodname", "food_name"),
        "Description": ("Description", "description"),
        "Price": ("Price", "price"),
        "Category": ("Category", "category"),
        "ImageName": ("ImageName", "imagename", "image_name"),
        "IsAvailable": ("IsAvailable", "isavailable", "is_available"),
        "Rating": ("Rating", "rating"),
        "Stock": ("Stock", "stock"),
        "TrackInventory": ("TrackInventory", "trackinventory", "track_inventory"),
        "DateAdded": ("DateAdded", "dateadded", "date_added"),
    }
    result = {}
    for api_name, candidates in aliases.items():
        for candidate in candidates:
            if candidate in item:
                result[api_name] = item[candidate]
                break
    result["FoodID"] = int(result.get("FoodID") or 0)
    result["FoodName"] = str(result.get("FoodName") or "")
    result["Price"] = str(result.get("Price") if result.get("Price") is not None else "")
    result["Quantity"] = 0
    if result.get("IsAvailable") is None:
        result["IsAvailable"] = 1
    return result


def _get_cart_quantities(cursor, session_key):
    cursor.execute(
        "SELECT food_id, SUM(quantity) FROM session_carts WHERE session_id = %s GROUP BY food_id",
        [session_key],
    )
    return {int(food_id): max(0, int(quantity or 0)) for food_id, quantity in cursor.fetchall()}


@csrf_exempt
@require_http_methods(["GET"])
def get_food_items(request):
    """Return catalogue data with per-user or per-guest cart quantities merged in."""
    try:
        user = _user_from_token(request)
        if request.headers.get("Authorization") and not user:
            return _error("Your session has expired. Please sign in again.", 401)
        session_key = _user_cart_key(user["user_id"]) if user else request.GET.get("sessionId", "")
        if not user and session_key and not _valid_guest_session_id(session_key):
            return _error("Invalid guest session.", 400)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT FoodID, FoodName, Description, Price, Category, ImageName, IsAvailable, Rating, Stock, TrackInventory, DateAdded FROM FoodItems ORDER BY Category, FoodName"
            )
            columns = [col[0] for col in cursor.description]
            result = [_food_row_to_json(columns, row) for row in cursor.fetchall()]
            quantities = _get_cart_quantities(cursor, session_key) if session_key else {}
        for item in result:
            item["Quantity"] = quantities.get(item["FoodID"], 0)
        return JsonResponse(result, safe=False)
    except Exception:
        logger.exception("Food catalogue request failed")
        return _error("The menu is temporarily unavailable.", 500)


def _read_food_catalogue():
    with connection.cursor() as cursor:
        cursor.execute("SELECT FoodID, FoodName, Price, Category, IsAvailable, Stock, TrackInventory FROM FoodItems")
        rows = cursor.fetchall()
    catalog = {}
    for row in rows:
        food_id, name, price, category, available, stock, track_inventory = row
        catalog[int(food_id)] = {
            "FoodID": int(food_id), "FoodName": str(name), "Price": Decimal(str(price)),
            "Category": category, "IsAvailable": int(available or 0), "Stock": int(stock or 0),
            "TrackInventory": int(track_inventory or 0),
        }
    return catalog


def _normalise_requested_items(items, catalog):
    if not isinstance(items, list) or not items or len(items) > MAX_ORDER_LINES:
        raise ValueError("Your cart is empty or contains too many different items.")
    combined = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Invalid cart item.")
        raw_id = item.get("FoodID", item.get("food_id", item.get("foodId")))
        raw_quantity = item.get("Quantity", item.get("quantity"))
        try:
            food_id = int(raw_id)
            quantity = int(raw_quantity)
        except (TypeError, ValueError):
            raise ValueError("Every cart item needs a valid product ID and quantity.")
        if quantity < 1 or quantity > MAX_CART_QUANTITY:
            raise ValueError(f"Quantity must be between 1 and {MAX_CART_QUANTITY}.")
        combined[food_id] = combined.get(food_id, 0) + quantity
    if sum(combined.values()) > MAX_ORDER_ITEMS:
        raise ValueError(f"An order cannot contain more than {MAX_ORDER_ITEMS} items.")
    lines = []
    total = Decimal("0.00")
    for food_id, quantity in combined.items():
        food = catalog.get(food_id)
        if not food:
            raise ValueError("One of the selected menu items no longer exists.")
        if not food["IsAvailable"]:
            raise ValueError(f"{food['FoodName']} is currently unavailable.")
        tracks_inventory = bool(food.get("TrackInventory", food["Stock"] > 0))
        if tracks_inventory and quantity > food["Stock"]:
            raise ValueError(f"Only {food['Stock']} portion(s) of {food['FoodName']} are currently available.")
        unit_price = food["Price"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if unit_price <= 0:
            raise ValueError(f"The listed price for {food['FoodName']} needs to be verified before checkout.")
        line_total = (unit_price * quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total += line_total
        lines.append({
            "food_id": food_id,
            "name": food["FoodName"],
            "quantity": quantity,
            "price": f"{unit_price:.2f}",
            "line_total": f"{line_total:.2f}",
            "stock_reserved": bool(food.get("TrackInventory", food["Stock"] > 0)),
        })
    return lines, total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _update_cart_quantity(session_key, food_id, delta=None, absolute=None):
    if delta is None and absolute is None:
        raise ValueError("A quantity change is required.")
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT FoodID, FoodName, IsAvailable, Stock, TrackInventory FROM FoodItems WHERE FoodID = %s FOR UPDATE",
                [food_id],
            )
            food = cursor.fetchone()
            if not food:
                raise LookupError("Menu item not found.")
            _, food_name, is_available, stock, track_inventory = food
            if not int(is_available or 0):
                raise ValueError(f"{food_name} is currently unavailable.")
            cursor.execute(
                "SELECT id, quantity FROM session_carts WHERE session_id = %s AND food_id = %s ORDER BY id",
                [session_key, food_id],
            )
            rows = cursor.fetchall()
            current = sum(int(row[1] or 0) for row in rows)
            desired = current + int(delta) if delta is not None else int(absolute)
            if desired < 0:
                desired = 0
            if desired > MAX_CART_QUANTITY:
                raise ValueError(f"You can add up to {MAX_CART_QUANTITY} of one item.")
            if int(track_inventory or 0) == 1 and desired > int(stock or 0):
                raise ValueError(f"Only {int(stock or 0)} portion(s) are available.")
            if rows:
                first_id = rows[0][0]
                cursor.execute("DELETE FROM session_carts WHERE session_id = %s AND food_id = %s", [session_key, food_id])
                if desired:
                    cursor.execute(
                        "INSERT INTO session_carts (session_id, food_id, quantity) VALUES (%s, %s, %s)",
                        [session_key, food_id, desired],
                    )
            elif desired:
                cursor.execute(
                    "INSERT INTO session_carts (session_id, food_id, quantity) VALUES (%s, %s, %s)",
                    [session_key, food_id, desired],
                )
    return desired


@csrf_exempt
@require_http_methods(["POST"])
def update_quantity(request, food_id):
    user, error = _require_user(request)
    if error:
        return error
    data = _json_body(request)
    if data is None:
        return _error("Invalid JSON request.")
    try:
        delta = int(data.get("quantity", data.get("delta")))
    except (TypeError, ValueError):
        return _error("Quantity change must be an integer.")
    if delta == 0 or abs(delta) > MAX_CART_QUANTITY:
        return _error("Quantity change is outside the allowed range.")
    try:
        new_quantity = _update_cart_quantity(_user_cart_key(user["user_id"]), food_id, delta=delta)
        return JsonResponse({"success": True, "newQuantity": new_quantity})
    except LookupError as exc:
        return _error(str(exc), 404)
    except ValueError as exc:
        return _error(str(exc), 409)
    except Exception:
        logger.exception("Authenticated cart update failed")
        return _error("Unable to update your cart right now.", 500)


def _legacy_password_check(raw_password, stored_password):
    """Support one-time migration of legacy plain-text passwords on successful login."""
    try:
        if check_password(raw_password, stored_password):
            return True, False
    except (ValueError, TypeError):
        pass
    if isinstance(stored_password, str) and hmac.compare_digest(raw_password, stored_password):
        return True, True
    return False, False


@csrf_exempt
@require_http_methods(["POST"])
def login_user(request):
    data = _json_body(request)
    if data is None:
        return _error("Invalid JSON request.")
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password")
    if not email or not isinstance(password, str) or not password:
        return _error("Email and password are required.")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT user_id, name, email, password, token_version FROM users WHERE LOWER(email) = %s LIMIT 1", [email])
            row = cursor.fetchone()
            if not row:
                return _error("Invalid email or password.", 401)
            user_id, name, stored_email, stored_password, token_version = row
            valid, was_legacy = _legacy_password_check(password, stored_password)
            if not valid:
                return _error("Invalid email or password.", 401)
            if was_legacy:
                cursor.execute("UPDATE users SET password = %s WHERE user_id = %s", [make_password(password), user_id])
            cursor.execute("UPDATE users SET is_logged_in = 1 WHERE user_id = %s", [user_id])
        user = {"user_id": int(user_id), "name": name, "email": stored_email}
        return JsonResponse({"success": True, "user": user, "token": _issue_token(user_id, token_version)})
    except Exception:
        logger.exception("Login failed")
        return _error("Unable to sign in right now.", 500)


@csrf_exempt
@require_http_methods(["POST"])
def signup_user(request):
    data = _json_body(request)
    if data is None:
        return _error("Invalid JSON request.")
    name = " ".join(str(data.get("name", "")).strip().split())
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password")
    if len(name) < 2 or len(name) > 100:
        return _error("Enter a name between 2 and 100 characters.")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or len(email) > 100:
        return _error("Enter a valid email address.")
    if not isinstance(password, str) or len(password) < 8 or len(password) > 128:
        return _error("Password must be between 8 and 128 characters.")
    try:
        validate_password(password)
    except ValidationError as exc:
        return _error(" ".join(exc.messages))
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SELECT user_id FROM users WHERE LOWER(email) = %s LIMIT 1", [email])
                if cursor.fetchone():
                    return _error("An account with this email already exists.", 409)
                cursor.execute(
                    "INSERT INTO users (name, email, password, is_logged_in, token_version) VALUES (%s, %s, %s, 1, 0)",
                    [name, email, make_password(password)],
                )
                user_id = cursor.lastrowid
        user = {"user_id": int(user_id), "name": name, "email": email}
        return JsonResponse({"success": True, "user": user, "token": _issue_token(user_id, 0)}, status=201)
    except Exception:
        logger.exception("Signup failed")
        return _error("Unable to create your account right now.", 500)


@csrf_exempt
@require_http_methods(["POST"])
def logout_user(request, user_id=None):
    user, error = _require_user(request)
    if error:
        return error
    if user_id is not None and int(user_id) != user["user_id"]:
        return _error("You cannot sign out another user.", 403)
    try:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE users SET is_logged_in = 0, token_version = token_version + 1 WHERE user_id = %s", [user["user_id"]])
        return JsonResponse({"success": True})
    except Exception:
        logger.exception("Logout failed")
        return _error("Unable to sign out right now.", 500)


@csrf_exempt
@require_http_methods(["POST"])
def create_order(request):
    user, error = _require_user(request)
    if error:
        return error
    data = _json_body(request)
    if data is None:
        return _error("Invalid JSON request.")
    requested_items = data.get("items")
    payment_method = str(data.get("paymentMethod", "COD")).strip().upper()
    if payment_method == "UPI":
        payment_method = "RAZORPAY"
    if payment_method not in {"COD", "RAZORPAY"}:
        return _error("Choose Cash on Delivery or Razorpay online payment.")
    address = " ".join(str(data.get("deliveryAddress", "")).strip().split())
    phone = re.sub(r"[\s-]", "", str(data.get("phone", "")))
    if len(address) < 10 or len(address) > 500:
        return _error("Enter a delivery address between 10 and 500 characters.")
    if not re.fullmatch(r"[6-9]\d{9}", phone):
        return _error("Enter a valid 10-digit Indian mobile number.")

    key_id = os.getenv("RAZORPAY_KEY_ID", "").strip()
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
    if payment_method == "RAZORPAY" and (not _is_configured_secret(key_id) or not _is_configured_secret(key_secret)):
        return _error("Online payments are not configured. Set valid Razorpay TEST keys in the backend environment.", 503)

    order_id = f"SAV-{secrets.token_hex(6).upper()}"
    try:
        # Lock menu rows while validating prices/stock and reserving tracked stock.
        # TrackInventory distinguishes untracked legacy rows from tracked rows sold out at zero.
        with transaction.atomic():
            catalog = _read_food_catalogue_for_update()
            lines, total = _normalise_requested_items(requested_items, catalog)
            with connection.cursor() as cursor:
                for line in lines:
                    if line.get("stock_reserved"):
                        cursor.execute(
                            "UPDATE FoodItems SET Stock = Stock - %s WHERE FoodID = %s AND TrackInventory = 1 AND Stock >= %s",
                            [line["quantity"], line["food_id"], line["quantity"]],
                        )
                        if cursor.rowcount != 1:
                            raise ValueError(f"Stock changed for {line['name']}. Refresh your cart and try again.")
            amount_paise = int((total * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            payment_status = "cod_due" if payment_method == "COD" else "pending"
            order_status = "placed" if payment_method == "COD" else "awaiting_payment"
            customer_details = json.dumps({
                "user_id": user["user_id"], "name": user["name"], "email": user["email"],
                "delivery_address": address, "phone": phone,
            }, ensure_ascii=False)
            items_json = json.dumps(lines, ensure_ascii=False)
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO orders
                    (order_id, razorpay_order_id, amount, currency, payment_method, status,
                     items, customer_details, user_id, payment_status, order_status,
                     delivery_address, customer_phone)
                    VALUES (%s, NULL, %s, 'INR', %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    [order_id, f"{total:.2f}", payment_method, order_status,
                     items_json, customer_details, user["user_id"], payment_status, order_status, address, phone],
                )
    except (ValueError, InvalidOperation) as exc:
        return _error(str(exc), 409)
    except Exception:
        logger.exception("Saving order failed")
        return _error("Could not create your order. No payment has been started.", 500)

    gateway_order_id = None
    if payment_method == "RAZORPAY":
        try:
            gateway_order = razorpay.Client(auth=(key_id, key_secret)).order.create({
                "amount": amount_paise,
                "currency": "INR",
                "receipt": order_id,
                "notes": {"savora_order_id": order_id, "user_id": str(user["user_id"])},
            })
            gateway_order_id = gateway_order["id"]
            with connection.cursor() as cursor:
                cursor.execute("UPDATE orders SET razorpay_order_id = %s, updated_at = CURRENT_TIMESTAMP WHERE order_id = %s AND user_id = %s", [gateway_order_id, order_id, user["user_id"]])
                if cursor.rowcount != 1:
                    raise RuntimeError("Razorpay order could not be attached to the saved Savora order.")
        except Exception:
            logger.exception("Razorpay order creation failed; releasing inventory reservation for %s", order_id)
            _cancel_pending_order_and_release(order_id, "gateway_error")
            return _error("Razorpay could not create the payment order. Your stock reservation was released; please try again.", 502)

    payload = {
        "success": True, "orderId": order_id, "amount": f"{total:.2f}",
        "amountPaise": amount_paise, "currency": "INR", "orderStatus": order_status,
        "paymentStatus": payment_status,
    }
    if gateway_order_id:
        payload.update({"razorpayOrderId": gateway_order_id, "keyId": key_id})
    return JsonResponse(payload, status=201)


def _read_food_catalogue_for_update():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT FoodID, FoodName, Price, Category, IsAvailable, Stock, TrackInventory FROM FoodItems ORDER BY FoodID FOR UPDATE"
        )
        rows = cursor.fetchall()
    return {
        int(row[0]): {
            "FoodID": int(row[0]), "FoodName": str(row[1]), "Price": Decimal(str(row[2])),
            "Category": row[3], "IsAvailable": int(row[4] or 0), "Stock": int(row[5] or 0),
            "TrackInventory": int(row[6] or 0),
        }
        for row in rows
    }


def _load_order_items(raw_items):
    try:
        items = json.loads(raw_items or "[]")
        return items if isinstance(items, list) else []
    except (TypeError, ValueError):
        return []


def _release_reserved_stock(items):
    """Return tracked stock once; caller must persist returned flags before reprocessing."""
    updated_items = []
    with connection.cursor() as cursor:
        for line in items:
            if not isinstance(line, dict):
                continue
            if line.get("stock_reserved"):
                try:
                    food_id = int(line.get("food_id"))
                    quantity = int(line.get("quantity"))
                except (TypeError, ValueError):
                    food_id = quantity = 0
                if food_id > 0 and quantity > 0:
                    cursor.execute("UPDATE FoodItems SET Stock = Stock + %s WHERE FoodID = %s", [quantity, food_id])
                line = {**line, "stock_reserved": False}
            updated_items.append(line)
    return updated_items


def _cancel_pending_order_and_release(order_id, payment_status="failed"):
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT items, order_status, payment_status FROM orders WHERE order_id = %s FOR UPDATE", [order_id])
            row = cursor.fetchone()
            if not row:
                return
            raw_items, order_status, saved_payment_status = row
            if saved_payment_status == "paid" or order_status != "awaiting_payment":
                return
            items = _release_reserved_stock(_load_order_items(raw_items))
            cursor.execute(
                "UPDATE orders SET items = %s, payment_status = %s, order_status = 'cancelled', status = 'cancelled', updated_at = CURRENT_TIMESTAMP WHERE order_id = %s",
                [json.dumps(items, ensure_ascii=False), payment_status, order_id],
            )


@csrf_exempt
@require_http_methods(["POST"])
def verify_payment(request):
    user, error = _require_user(request)
    if error:
        return error
    data = _json_body(request)
    if data is None:
        return _error("Invalid JSON request.")
    payment_id = str(data.get("razorpay_payment_id", "")).strip()
    gateway_order_id = str(data.get("razorpay_order_id", "")).strip()
    signature = str(data.get("razorpay_signature", "")).strip()
    order_id = str(data.get("orderId", "")).strip()
    if not all([payment_id, gateway_order_id, signature, order_id]):
        return _error("Payment verification details are incomplete.")
    key_id = os.getenv("RAZORPAY_KEY_ID", "").strip()
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
    if not _is_configured_secret(key_id) or not _is_configured_secret(key_secret):
        return _error("Payment verification is not configured.", 503)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT amount, razorpay_order_id, payment_id, payment_status, user_id, order_status FROM orders WHERE order_id = %s LIMIT 1",
                [order_id],
            )
            saved = cursor.fetchone()
        if not saved:
            return _error("Order not found.", 404)
        amount, saved_gateway_order_id, saved_payment_id, saved_payment_status, owner_id, saved_order_status = saved
        if int(owner_id or 0) != user["user_id"]:
            return _error("You cannot verify payment for another user's order.", 403)
        if saved_gateway_order_id != gateway_order_id:
            return _error("The payment does not match this order.", 400)
        if saved_payment_status == "paid" and saved_payment_id == payment_id:
            return JsonResponse({"success": True, "orderId": order_id, "paymentStatus": "paid", "message": "Payment was already verified."})
        client = razorpay.Client(auth=(key_id, key_secret))
        client.utility.verify_payment_signature({
            "razorpay_order_id": gateway_order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        })
        payment = client.payment.fetch(payment_id)
        expected_paise = int((Decimal(str(amount)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        if payment.get("order_id") != gateway_order_id:
            return _error("The gateway payment belongs to a different order.", 400)
        if int(payment.get("amount", -1)) != expected_paise or payment.get("currency") != "INR":
            return _error("The verified payment amount does not match the order.", 400)
        if payment.get("status") != "captured":
            return _error("Payment has not been captured yet. Please wait and refresh your orders.", 409)
        if saved_order_status in {"cancelled", "delivered"} and saved_payment_status != "paid":
            # Funds may have been captured after an expired/cancelled reservation. Record reality and
            # flag manual refund/reconciliation instead of pretending the order can still be fulfilled.
            logger.error("Captured payment for non-fulfillable Savora order %s; manual refund/review required", order_id)
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE orders SET payment_id = %s, signature = %s, payment_status = 'paid', updated_at = CURRENT_TIMESTAMP WHERE order_id = %s AND user_id = %s",
                    [payment_id, signature, order_id, user["user_id"]],
                )
            return JsonResponse({"success": True, "orderId": order_id, "paymentStatus": "paid", "orderStatus": saved_order_status, "manualRefundReview": True})
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    """UPDATE orders SET payment_id = %s, signature = %s,
                       payment_status = 'paid', order_status = 'placed', status = 'placed',
                       updated_at = CURRENT_TIMESTAMP WHERE order_id = %s AND user_id = %s""",
                    [payment_id, signature, order_id, user["user_id"]],
                )
        return JsonResponse({"success": True, "orderId": order_id, "paymentStatus": "paid", "orderStatus": "placed"})
    except razorpay.errors.SignatureVerificationError:
        return _error("Payment signature verification failed.", 400)
    except Exception:
        logger.exception("Payment verification failed")
        return _error("Payment could not be verified. Check your order status before retrying.", 502)


@csrf_exempt
@require_http_methods(["POST"])
def razorpay_webhook(request):
    """Verify Razorpay's webhook HMAC and idempotently reconcile captured/failed payments."""
    webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "").strip()
    received_signature = request.headers.get("X-Razorpay-Signature", "")
    if not _valid_razorpay_webhook_signature(request.body, webhook_secret, received_signature):
        return HttpResponse(status=400)
    event_id = request.headers.get("X-Razorpay-Event-Id", "")
    try:
        data = json.loads(request.body.decode("utf-8"))
        event = data.get("event")
        entity = data.get("payload", {}).get("payment", {}).get("entity", {})
        if event not in {"payment.captured", "payment.failed"} or not isinstance(entity, dict):
            return HttpResponse(status=200)
        gateway_order_id = entity.get("order_id")
        payment_id = entity.get("id")
        gateway_amount = entity.get("amount")
        gateway_currency = entity.get("currency")
        gateway_status = entity.get("status")
        if not gateway_order_id or not payment_id:
            return HttpResponse(status=200)
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT order_id, amount, payment_status, order_status, items FROM orders WHERE razorpay_order_id = %s LIMIT 1 FOR UPDATE",
                    [gateway_order_id],
                )
                saved = cursor.fetchone()
                if not saved:
                    return HttpResponse(status=200)
                order_id, amount, saved_payment_status, saved_order_status, raw_items = saved
                expected_paise = int((Decimal(str(amount)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
                if gateway_currency != "INR" or int(gateway_amount or -1) != expected_paise:
                    logger.warning("Razorpay webhook amount/currency mismatch for %s (event=%s)", order_id, event_id or "unknown")
                    return HttpResponse(status=200)
                if event == "payment.captured" and gateway_status == "captured":
                    if saved_order_status in {"cancelled", "delivered"} and saved_payment_status != "paid":
                        logger.error("Late captured payment for order %s; manual refund/reconciliation is required", order_id)
                        cursor.execute("UPDATE orders SET payment_id = %s, payment_status = 'paid', updated_at = CURRENT_TIMESTAMP WHERE order_id = %s AND payment_status <> 'paid'", [payment_id, order_id])
                    else:
                        cursor.execute(
                            """UPDATE orders SET payment_id = %s, payment_status = 'paid',
                               order_status = CASE WHEN order_status = 'awaiting_payment' THEN 'placed' ELSE order_status END,
                               status = CASE WHEN status = 'awaiting_payment' THEN 'placed' ELSE status END,
                               updated_at = CURRENT_TIMESTAMP
                               WHERE order_id = %s AND payment_status <> 'paid'""",
                            [payment_id, order_id],
                        )
                elif event == "payment.failed" and saved_payment_status != "paid" and saved_order_status == "awaiting_payment":
                    released_items = _release_reserved_stock(_load_order_items(raw_items))
                    cursor.execute(
                        """UPDATE orders SET items = %s, payment_id = %s, payment_status = 'failed',
                           order_status = 'cancelled', status = 'cancelled', updated_at = CURRENT_TIMESTAMP
                           WHERE order_id = %s AND payment_status <> 'paid' AND order_status = 'awaiting_payment'""",
                        [json.dumps(released_items, ensure_ascii=False), payment_id, order_id],
                    )
        return HttpResponse(status=200)
    except Exception:
        logger.exception("Razorpay webhook processing failed; event=%s", event_id or "unknown")
        return HttpResponse(status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_user_orders(request, user_id=None):
    user, error = _require_user(request)
    if error:
        return error
    if user_id is not None and int(user_id) != user["user_id"]:
        return _error("You can only view your own orders.", 403)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT order_id, created_at, amount, payment_method, payment_id,
                   status, items, customer_details, order_status, payment_status,
                   delivery_address, customer_phone FROM orders WHERE user_id = %s
                   ORDER BY created_at DESC LIMIT 100""",
                [user["user_id"]],
            )
            rows = cursor.fetchall()
        result = []
        for row in rows:
            (order_id, created_at, amount, payment_method, payment_id, legacy_status,
             raw_items, raw_customer, order_status, payment_status, address, phone) = row
            try:
                items = json.loads(raw_items or "[]")
                if not isinstance(items, list): items = []
            except (ValueError, TypeError): items = []
            try:
                customer = json.loads(raw_customer or "{}")
                if not isinstance(customer, dict): customer = {}
            except (ValueError, TypeError): customer = {}
            result.append({
                "order_id": order_id,
                "order_date": created_at.isoformat() if created_at else None,
                "total_amount": str(amount),
                "payment_method": payment_method,
                "payment_id": payment_id,
                "payment_status": payment_status or ("paid" if payment_id else ("cod_due" if payment_method == "COD" else "pending")),
                "order_status": order_status or legacy_status or "placed",
                "items": items,
                "delivery_address": address or customer.get("delivery_address", ""),
                "phone": phone or customer.get("phone", ""),
            })
        return JsonResponse(result, safe=False)
    except Exception:
        logger.exception("Order history request failed")
        return _error("Unable to load orders right now.", 500)


@csrf_exempt
@require_http_methods(["POST"])
def update_order_status(request, order_id):
    user, error = _require_user(request)
    if error:
        return error
    admins = {email.strip().lower() for email in os.getenv("SAVORA_ADMIN_EMAILS", "").split(",") if email.strip()}
    if user["email"].lower() not in admins:
        return _error("Only configured Savora administrators can update order status.", 403)
    data = _json_body(request)
    if data is None:
        return _error("Invalid JSON request.")
    status = str(data.get("status", "")).strip().lower()
    if status not in VALID_ORDER_STATUSES:
        return _error("Invalid order status.")
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT payment_status, payment_method, order_status, items FROM orders WHERE order_id = %s LIMIT 1 FOR UPDATE",
                    [order_id],
                )
                row = cursor.fetchone()
                if not row:
                    return _error("Order not found.", 404)
                payment_status, payment_method, current_status, raw_items = row
                if status != current_status and status not in VALID_STATUS_TRANSITIONS.get(str(current_status or "placed"), set()):
                    return _error(f"Order cannot move from {current_status} to {status}.", 409)
                if status in {"confirmed", "preparing", "out-for-delivery", "delivered"} and payment_method != "COD" and payment_status != "paid":
                    return _error("An online order cannot progress until payment is captured.", 409)
                if status == "cancelled" and payment_status == "paid" and payment_method != "COD":
                    return _error("This online order has a captured payment. Complete a refund through Razorpay before cancelling it.", 409)
                if status == "cancelled" and current_status != "cancelled":
                    released_items = _release_reserved_stock(_load_order_items(raw_items))
                    cursor.execute("UPDATE orders SET items = %s WHERE order_id = %s", [json.dumps(released_items, ensure_ascii=False), order_id])
                if status == "delivered" and payment_method == "COD" and payment_status == "cod_due":
                    cursor.execute("UPDATE orders SET order_status = %s, status = %s, payment_status = 'paid', updated_at = CURRENT_TIMESTAMP WHERE order_id = %s", [status, status, order_id])
                else:
                    cursor.execute("UPDATE orders SET order_status = %s, status = %s, updated_at = CURRENT_TIMESTAMP WHERE order_id = %s", [status, status, order_id])
        return JsonResponse({"success": True, "orderId": order_id, "orderStatus": status})
    except Exception:
        logger.exception("Order status update failed")
        return _error("Unable to update the order status.", 500)


@csrf_exempt
@require_http_methods(["POST"])
def session_cart_operations(request):
    data = _json_body(request)
    if data is None:
        return _error("Invalid JSON request.")
    session_id = data.get("sessionId")
    try:
        food_id = int(data.get("foodId"))
    except (TypeError, ValueError):
        return _error("Invalid menu item.")
    if not _valid_guest_session_id(session_id):
        return _error("Invalid guest session.")
    try:
        if "delta" in data:
            delta = int(data.get("delta"))
            if delta == 0 or abs(delta) > MAX_CART_QUANTITY:
                return _error("Invalid quantity change.")
            new_quantity = _update_cart_quantity(session_id, food_id, delta=delta)
        else:
            absolute = int(data.get("quantity"))
            if absolute < 0 or absolute > MAX_CART_QUANTITY:
                return _error("Quantity must be between 0 and 25.")
            new_quantity = _update_cart_quantity(session_id, food_id, absolute=absolute)
        return JsonResponse({"success": True, "newQuantity": new_quantity})
    except LookupError as exc:
        return _error(str(exc), 404)
    except ValueError as exc:
        return _error(str(exc), 409)
    except Exception:
        logger.exception("Guest cart update failed")
        return _error("Unable to update your guest cart.", 500)


@csrf_exempt
@require_http_methods(["POST"])
def transfer_session_cart(request):
    """Atomically merge a guest cart into the authenticated user's cart."""
    user, error = _require_user(request)
    if error:
        return error
    data = _json_body(request)
    if data is None:
        return _error("Invalid JSON request.")
    session_id = data.get("sessionId")
    if not _valid_guest_session_id(session_id):
        return _error("Invalid guest session.")
    target_key = _user_cart_key(user["user_id"])
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SELECT food_id, quantity FROM session_carts WHERE session_id = %s ORDER BY food_id FOR UPDATE", [session_id])
                guest_rows = cursor.fetchall()
            for food_id, quantity in guest_rows:
                quantity = max(0, int(quantity or 0))
                if quantity:
                    _update_cart_quantity(target_key, int(food_id), delta=quantity)
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM session_carts WHERE session_id = %s", [session_id])
        return JsonResponse({"success": True, "transferred": len(guest_rows)})
    except (ValueError, LookupError) as exc:
        return _error(str(exc), 409)
    except Exception:
        logger.exception("Guest cart transfer failed")
        return _error("Could not safely transfer the guest cart. The saved guest cart remains available.", 500)


@csrf_exempt
@require_http_methods(["GET"])
def get_session_cart(request, session_id):
    user = _user_from_token(request)
    if session_id.startswith("user_"):
        try:
            owner_id = int(session_id.removeprefix("user_"))
        except ValueError:
            return _error("Invalid cart session.", 400)
        if not user or user["user_id"] != owner_id:
            return _error("You cannot access another user's cart.", 403)
    elif not _valid_guest_session_id(session_id):
        return _error("Invalid guest session.", 400)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT sc.id, sc.session_id, sc.food_id, sc.quantity, f.FoodName, f.Price, f.ImageName
                   FROM session_carts sc JOIN FoodItems f ON sc.food_id = f.FoodID
                   WHERE sc.session_id = %s ORDER BY sc.id""",
                [session_id],
            )
            rows = cursor.fetchall()
            columns = [col[0] for col in cursor.description]
        return JsonResponse([dict(zip(columns, row)) for row in rows], safe=False)
    except Exception:
        logger.exception("Session cart retrieval failed")
        return _error("Unable to load cart.", 500)


@csrf_exempt
@require_http_methods(["DELETE"])
def clear_session_cart(request, session_id):
    user = _user_from_token(request)
    if session_id.startswith("user_"):
        try:
            owner_id = int(session_id.removeprefix("user_"))
        except ValueError:
            return _error("Invalid cart session.", 400)
        if not user or user["user_id"] != owner_id:
            return _error("You cannot clear another user's cart.", 403)
    elif not _valid_guest_session_id(session_id):
        return _error("Invalid guest session.", 400)
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM session_carts WHERE session_id = %s", [session_id])
        return JsonResponse({"success": True})
    except Exception:
        logger.exception("Cart clear failed")
        return _error("Unable to clear cart.", 500)


@csrf_exempt
@require_http_methods(["POST"])
def process_voice(request):
    data = _json_body(request)
    if data is None:
        return _error("Invalid JSON request.")
    transcript = str(data.get("transcript", "")).strip()
    if not transcript or len(transcript) > 500:
        return _error("Voice transcript must contain between 1 and 500 characters.")
    foods = []
    categories = []
    authenticated = bool(_user_from_token(request))
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT FoodName, Category FROM FoodItems WHERE IsAvailable = 1")
            menu_rows = cursor.fetchall()
        foods = [str(row[0]) for row in menu_rows]
        categories = sorted({str(row[1]) for row in menu_rows if row[1]})
        fallback = _fallback_voice_command(transcript, foods, categories, authenticated)
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            return JsonResponse({"status": "ok", "transcript": transcript, "aiResponse": fallback})
        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1", timeout=15.0, max_retries=1)
        system_prompt = (
            "You are Echo, a food-ordering command parser. Return one JSON object only. "
            "Allowed command values: FILTER, NAVIGATE, ORDER, REMOVE, CART_SUMMARY, ORDER_STATUS, LOGOUT, UNKNOWN. "
            "Never authenticate a user, request passwords, calculate prices, or claim an action succeeded. "
            "Use only exact food names from the supplied menu. Quantity must be an integer 1 through 10. "
            "For uncertain item names, return UNKNOWN and ask a short clarification. "
            "For NAVIGATE use only home, about, login, cart, orders, profile, menu. "
            "For FILTER use only the supplied categories. For ORDER/REMOVE output items with name and quantity; do not include price."
        )
        user_prompt = json.dumps({"transcript": transcript, "food_names": foods, "categories": categories}, ensure_ascii=False)
        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            response_format={"type": "json_object"}, temperature=0.1, max_tokens=350,
        )
        parsed = json.loads(response.choices[0].message.content or "{}")
        validated = _validate_voice_command(parsed, foods, categories, authenticated)
        return JsonResponse({"status": "ok", "transcript": transcript, "aiResponse": validated})
    except Exception:
        logger.exception("Voice command processing failed")
        return JsonResponse({"status": "ok", "transcript": transcript, "aiResponse": _fallback_voice_command(transcript, foods, categories, authenticated)})


def _validate_voice_command(command, foods, categories, authenticated):
    if not isinstance(command, dict):
        return {"command": "UNKNOWN", "response": "I couldn't understand that. Please try again."}
    kind = str(command.get("command", "UNKNOWN")).upper()
    response = str(command.get("response", "")).strip()[:240]
    if kind == "FILTER":
        requested = str(command.get("category", ""))
        found = next((cat for cat in categories if cat.lower() == requested.lower()), None)
        return {"command": "FILTER", "category": found, "response": response or (f"Showing {found} items." if found else "Please choose a menu category.")} if found else {"command": "UNKNOWN", "response": "I couldn't match that food category."}
    if kind == "NAVIGATE":
        page = str(command.get("page", "")).lower()
        allowed = {"home": "/", "about": "/about", "login": "/login", "cart": "/cart", "orders": "/orders", "profile": "/profile", "menu": "/#items"}
        if page not in allowed or (page in {"orders", "profile"} and not authenticated):
            if page in {"orders", "profile"} and not authenticated:
                return {"command": "NAVIGATE", "page": "login", "path": "/login", "response": "Please sign in first."}
            return {"command": "UNKNOWN", "response": "That page isn't available."}
        return {"command": "NAVIGATE", "page": page, "path": allowed[page], "response": response or f"Opening {page}."}
    if kind in {"ORDER", "REMOVE"}:
        if not isinstance(command.get("items"), list) or not command["items"]:
            return {"command": "UNKNOWN", "response": "Tell me the food name and quantity, for example, add two masala dosas."}
        clean_items = []
        for item in command["items"][:8]:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            match = next((food for food in foods if food.lower() == name.lower()), None)
            if not match:
                matches = [food for food in foods if name and (name.lower() in food.lower() or food.lower() in name.lower())]
                if len(matches) == 1:
                    match = matches[0]
            try:
                quantity = int(item.get("quantity", 1))
            except (TypeError, ValueError):
                quantity = 0
            if match and 1 <= quantity <= 10:
                clean_items.append({"name": match, "quantity": quantity})
        if not clean_items:
            return {"command": "UNKNOWN", "response": "I couldn't match that to an available menu item. Please say the exact dish name."}
        return {"command": kind, "items": clean_items, "response": response or ("I'll update your cart." if kind == "ORDER" else "I'll update those cart quantities.")}
    if kind == "CART_SUMMARY":
        return {"command": "CART_SUMMARY", "response": response or "Here is your cart summary."}
    if kind == "ORDER_STATUS":
        if not authenticated:
            return {"command": "NAVIGATE", "page": "login", "path": "/login", "response": "Please sign in to check your orders."}
        return {"command": "ORDER_STATUS", "response": response or "I'll check your latest order."}
    if kind == "LOGOUT":
        return {"command": "LOGOUT", "response": response or "Signing you out."} if authenticated else {"command": "UNKNOWN", "response": "You are not signed in."}
    return {"command": "UNKNOWN", "response": response or "I didn't understand. Please try a menu item, a category, or a page name."}


def _fallback_voice_command(transcript, foods, categories, authenticated):
    text = transcript.lower()
    if any(word in text for word in ("logout", "log out", "sign out")):
        return {"command": "LOGOUT", "response": "Signing you out."} if authenticated else {"command": "UNKNOWN", "response": "You are not signed in."}
    nav = [("about", "/about"), ("login", "/login"), ("sign in", "/login"), ("cart", "/cart"), ("orders", "/orders"), ("profile", "/profile"), ("home", "/"), ("menu", "/#items")]
    for phrase, path in nav:
        if phrase in text and any(w in text for w in ("go", "open", "show", "take", "navigate", "page", "my")):
            page = {"/": "home", "/about": "about", "/login": "login", "/cart": "cart", "/orders": "orders", "/profile": "profile", "/#items": "menu"}[path]
            if page in {"orders", "profile"} and not authenticated:
                return {"command": "NAVIGATE", "page": "login", "path": "/login", "response": "Please sign in first."}
            return {"command": "NAVIGATE", "page": page, "path": path, "response": f"Opening {page}."}
    for category in categories:
        if category.lower() in text and any(w in text for w in ("show", "filter", "find", "browse", "category")):
            return {"command": "FILTER", "category": category, "response": f"Showing {category} items."}
    if "cart" in text and any(w in text for w in ("total", "summary", "how much", "what is in")):
        return {"command": "CART_SUMMARY", "response": "I'll read your cart summary."}
    action = "ORDER" if any(w in text for w in ("add", "order", "buy", "get me")) else "REMOVE" if any(w in text for w in ("remove", "delete", "take out")) else None
    if action and foods:
        matches = [name for name in foods if name.lower() in text]
        if len(matches) == 1:
            numbers = re.findall(r"\b(?:one|two|three|four|five|\d+)\b", text)
            word_to_num = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
            quantity = word_to_num.get(numbers[0], int(numbers[0]) if numbers and numbers[0].isdigit() else 1)
            return {"command": action, "items": [{"name": matches[0], "quantity": min(10, max(1, quantity))}], "response": "I'll update your cart."}
    return {"command": "UNKNOWN", "response": "Voice AI isn't configured or I couldn't match that command. You can still browse and order using the menu."}


@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """Non-sensitive deploy probe: reports database connectivity and schema readiness only."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.execute("SHOW COLUMNS FROM orders")
            columns = {row[0].lower() for row in cursor.fetchall()}
            cursor.execute("SHOW COLUMNS FROM users")
            user_columns = {row[0].lower() for row in cursor.fetchall()}
            cursor.execute("SHOW COLUMNS FROM session_carts")
            cart_columns = {row[0].lower() for row in cursor.fetchall()}
            cursor.execute("SHOW COLUMNS FROM FoodItems")
            food_columns = {row[0].lower() for row in cursor.fetchall()}
        required = {"user_id", "payment_status", "order_status", "delivery_address", "customer_phone", "razorpay_order_id", "currency"}
        missing = sorted(required - columns)
        if "token_version" not in user_columns:
            missing.append("users.token_version")
        if not {"session_id", "food_id", "quantity", "id"}.issubset(cart_columns):
            missing.append("session_carts columns")
        if not {"foodid", "foodname", "price", "stock", "trackinventory"}.issubset(food_columns):
            missing.append("FoodItems inventory/catalogue columns")
        if missing:
            return JsonResponse({"status": "degraded", "database": "connected", "schemaReady": False, "missingSchema": missing}, status=503)
        return JsonResponse({"status": "ok", "database": "connected", "schemaReady": True})
    except Exception:
        logger.exception("Health check failed")
        return JsonResponse({"status": "degraded", "database": "unavailable", "schemaReady": False}, status=503)
