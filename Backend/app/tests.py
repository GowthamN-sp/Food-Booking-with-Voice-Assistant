"""Unit tests for Savora validation logic. Integration tests require MySQL/Razorpay test setup."""
from decimal import Decimal
from django.test import SimpleTestCase
from app.views import _fallback_voice_command, _is_configured_secret, _normalise_requested_items, _valid_guest_session_id, _valid_razorpay_webhook_signature, _validate_voice_command
from app.management.commands.update_savora_market_prices import suggest_price


class GuestSessionValidationTests(SimpleTestCase):
    def test_guest_session_cannot_impersonate_authenticated_cart_key(self):
        self.assertFalse(_valid_guest_session_id("user_42"))
        self.assertTrue(_valid_guest_session_id("b17f2e14-abcd-4aa2-9a40-2f44bc909abc"))


class OrderValidationTests(SimpleTestCase):
    def setUp(self):
        self.catalog = {
            1: {"FoodID": 1, "FoodName": "Margherita Pizza", "Price": Decimal("199.00"), "Category": "Pizza", "IsAvailable": 1, "Stock": 10, "TrackInventory": 1},
            2: {"FoodID": 2, "FoodName": "Chicken Burger", "Price": Decimal("179.00"), "Category": "Burger", "IsAvailable": 1, "Stock": 0, "TrackInventory": 0},
            3: {"FoodID": 3, "FoodName": "Sold Out Dosa", "Price": Decimal("99.00"), "Category": "South Indian", "IsAvailable": 0, "Stock": 0, "TrackInventory": 1},
        }

    def test_totals_use_catalogue_price_not_client_price(self):
        lines, total = _normalise_requested_items(
            [{"FoodID": 1, "Quantity": 2, "Price": "0.01", "amount": 0}], self.catalog
        )
        self.assertEqual(total, Decimal("398.00"))
        self.assertEqual(lines[0]["price"], "199.00")

    def test_duplicate_lines_are_combined(self):
        lines, total = _normalise_requested_items(
            [{"FoodID": 1, "Quantity": 1}, {"FoodID": 1, "Quantity": 2}], self.catalog
        )
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["quantity"], 3)
        self.assertEqual(total, Decimal("597.00"))

    def test_unavailable_and_out_of_stock_items_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "unavailable"):
            _normalise_requested_items([{"FoodID": 3, "Quantity": 1}], self.catalog)
        with self.assertRaisesRegex(ValueError, "Only 10"):
            _normalise_requested_items([{"FoodID": 1, "Quantity": 11}], self.catalog)

    def test_non_positive_price_is_rejected(self):
        catalog = {1: {**self.catalog[1], "Price": Decimal("0.00")}}
        with self.assertRaisesRegex(ValueError, "price.*verified"):
            _normalise_requested_items([{"FoodID": 1, "Quantity": 1}], catalog)

    def test_tracked_inventory_at_zero_is_not_treated_as_untracked(self):
        catalog = {3: {**self.catalog[3], "IsAvailable": 1, "Stock": 0, "TrackInventory": 1}}
        with self.assertRaisesRegex(ValueError, "Only 0 portion"):
            _normalise_requested_items([{"FoodID": 3, "Quantity": 1}], catalog)


class VoiceCommandTests(SimpleTestCase):
    def test_order_command_only_returns_catalogue_items(self):
        result = _validate_voice_command(
            {"command": "ORDER", "items": [{"name": "Margherita Pizza", "quantity": 2}]},
            ["Margherita Pizza", "Chicken Burger"], ["Pizza", "Burger"], False,
        )
        self.assertEqual(result["command"], "ORDER")
        self.assertEqual(result["items"], [{"name": "Margherita Pizza", "quantity": 2}])

    def test_unauthenticated_orders_navigation_redirects_to_login(self):
        result = _validate_voice_command({"command": "NAVIGATE", "page": "orders"}, [], [], False)
        self.assertEqual(result["path"], "/login")

    def test_invalid_category_is_rejected(self):
        result = _validate_voice_command({"command": "FILTER", "category": "Secrets"}, [], ["Pizza"], True)
        self.assertEqual(result["command"], "UNKNOWN")

    def test_fallback_matches_a_unique_menu_item(self):
        result = _fallback_voice_command("add two margherita pizzas", ["Margherita Pizza", "Chicken Burger"], [], False)
        self.assertEqual(result["command"], "ORDER")
        self.assertEqual(result["items"][0]["quantity"], 2)


class SuggestedPriceTests(SimpleTestCase):
    def test_known_menu_name_has_indicative_price(self):
        price, _ = suggest_price("Margherita Pizza", "Pizza")
        self.assertEqual(price, Decimal("199.00"))

    def test_unknown_category_requires_review(self):
        price, reason = suggest_price("Special Chef Bowl", "Chef Specials")
        self.assertIsNone(price)
        self.assertIn("manual review", reason)


class PaymentConfigurationTests(SimpleTestCase):
    def test_placeholder_razorpay_credentials_are_not_treated_as_configured(self):
        self.assertFalse(_is_configured_secret("rzp_test_replace_me"))
        self.assertFalse(_is_configured_secret("replace-with-test-secret"))
        self.assertTrue(_is_configured_secret("rzp_test_abc123"))

    def test_webhook_signature_is_hmac_verified(self):
        import hashlib
        import hmac
        body = b'{"event":"payment.captured"}'
        secret = "unit-test-webhook-secret"
        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        self.assertTrue(_valid_razorpay_webhook_signature(body, secret, signature))
        self.assertFalse(_valid_razorpay_webhook_signature(body + b" ", secret, signature))
        self.assertFalse(_valid_razorpay_webhook_signature(body, "replace-with-webhook-secret", signature))
