"""Idempotent schema preparation for Savora's existing MySQL database.

Create a database backup before running this command:
    python manage.py migrate_savora_schema

This is a deliberate compatibility migration for the existing unmanaged legacy
schema. It does not delete tables or food/user records.
"""
import json
import re
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.hashers import identify_hasher, make_password
from django.db import connection, transaction

ORDER_COLUMNS = {
    "razorpay_order_id": "VARCHAR(100) NULL",
    "currency": "VARCHAR(10) NOT NULL DEFAULT 'INR'",
    "payment_id": "VARCHAR(100) NULL",
    "signature": "VARCHAR(255) NULL",
    "status": "VARCHAR(50) NOT NULL DEFAULT 'placed'",
    "amount": "DECIMAL(10,2) NOT NULL DEFAULT 0.00",
    "payment_method": "VARCHAR(50) NULL",
    "items": "LONGTEXT NULL",
    "customer_details": "LONGTEXT NULL",
    "created_at": "DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)",
    "updated_at": "DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)",
    "user_id": "BIGINT NULL",
    "payment_status": "VARCHAR(32) NOT NULL DEFAULT 'pending'",
    "order_status": "VARCHAR(32) NOT NULL DEFAULT 'placed'",
    "delivery_address": "TEXT NULL",
    "customer_phone": "VARCHAR(30) NULL",
}

class Command(BaseCommand):
    help = "Safely prepare legacy MySQL tables for Savora auth, cart, orders and payments."

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE 'users'")
            if not cursor.fetchone():
                raise CommandError("Required MySQL table 'users' was not found. Verify DB_NAME/DB_HOST settings.")
            cursor.execute("SHOW TABLES LIKE 'FoodItems'")
            if not cursor.fetchone():
                raise CommandError("Required MySQL table 'FoodItems' was not found. Verify your existing menu table.")
            # Inventory must be separate from stock count: Stock=0 can mean either no
            # stock or an old untracked row, so TrackInventory disambiguates the two.
            cursor.execute("SHOW COLUMNS FROM FoodItems")
            food_columns = {row[0].lower() for row in cursor.fetchall()}
            if "stock" not in food_columns:
                raise CommandError("FoodItems is missing Stock. Inspect the legacy table before continuing.")
            if "trackinventory" not in food_columns:
                cursor.execute("ALTER TABLE FoodItems ADD COLUMN TrackInventory TINYINT NOT NULL DEFAULT 0")
                added_inventory_column = True
            else:
                added_inventory_column = False
            # Always keep rows with a positive stock count tracked, including rows
            # inserted by an older seed script after an earlier migration run.
            cursor.execute("UPDATE FoodItems SET TrackInventory = 1 WHERE Stock > 0 AND TrackInventory = 0")

            cursor.execute("SHOW TABLES LIKE 'orders'")
            if not cursor.fetchone():
                raise CommandError("Required MySQL table 'orders' was not found. Create/restore the legacy orders table before continuing.")

            # Add a revocation version so logout invalidates previously issued signed API tokens.
            cursor.execute("SHOW COLUMNS FROM users")
            user_column_rows = cursor.fetchall()
            user_column_details = {row[0].lower(): row for row in user_column_rows}
            user_columns = set(user_column_details)
            added = ["FoodItems.TrackInventory (existing positive-stock rows marked tracked)"] if added_inventory_column else []
            if "password" not in user_columns:
                raise CommandError("The users table has no password column; inspect the legacy schema before migrating.")
            # Django password hashes may be longer than the legacy plain-text column.
            password_type = str(user_column_details["password"][1] or "").lower()
            varchar_match = re.fullmatch(r"(?:var)?char\((\d+)\)", password_type)
            if varchar_match and int(varchar_match.group(1)) < 255:
                cursor.execute("ALTER TABLE users MODIFY COLUMN password VARCHAR(255) NULL")
                added.append("users.password width (VARCHAR(255))")
            if "token_version" not in user_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN token_version INT NOT NULL DEFAULT 0")
                added.append("users.token_version")

            # Hash legacy plain-text passwords in place so the migration does not leave
            # existing accounts storing clear-text credentials. Existing Django hashes
            # are detected and left unchanged; rerunning this command is safe.
            cursor.execute("SELECT user_id, password FROM users")
            password_rows = cursor.fetchall()
            passwords_hashed = 0
            for user_id, stored_password in password_rows:
                if not isinstance(stored_password, str) or not stored_password:
                    continue
                try:
                    identify_hasher(stored_password)
                except (ValueError, TypeError):
                    cursor.execute("UPDATE users SET password = %s WHERE user_id = %s", [make_password(stored_password), user_id])
                    passwords_hashed += 1

            cursor.execute("SHOW COLUMNS FROM orders")
            existing = {row[0].lower() for row in cursor.fetchall()}
            missing_core = {"order_id", "created_at"} - existing
            if missing_core:
                raise CommandError("The orders table is missing required legacy columns: " + ", ".join(sorted(missing_core)) + ". Restore/repair the old table before migrating.")
            for column, definition in ORDER_COLUMNS.items():
                if column.lower() not in existing:
                    cursor.execute(f"ALTER TABLE orders ADD COLUMN `{column}` {definition}")
                    added.append(f"orders.{column}")

            cursor.execute("SHOW INDEX FROM orders")
            indexes = {row[2].lower() for row in cursor.fetchall()}
            if "ix_orders_user_id" not in indexes:
                cursor.execute("CREATE INDEX ix_orders_user_id ON orders (user_id)")
                added.append("orders.ix_orders_user_id")

            cursor.execute("SHOW TABLES LIKE 'session_carts'")
            if not cursor.fetchone():
                cursor.execute("""CREATE TABLE session_carts (
                    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(255) NOT NULL,
                    food_id INT NOT NULL,
                    quantity INT NOT NULL DEFAULT 1,
                    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
                    INDEX ix_session_carts_session_food (session_id, food_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
                added.append("table session_carts")
            else:
                cursor.execute("SHOW COLUMNS FROM session_carts")
                cart_columns = {row[0].lower() for row in cursor.fetchall()}
                if "id" not in cart_columns:
                    cursor.execute("ALTER TABLE session_carts ADD COLUMN id BIGINT NOT NULL AUTO_INCREMENT UNIQUE FIRST")
                    added.append("session_carts.id")
                    cursor.execute("SHOW COLUMNS FROM session_carts")
                    cart_columns = {row[0].lower() for row in cursor.fetchall()}
                cart_definitions = {
                    "session_id": "VARCHAR(255) NOT NULL DEFAULT ''",
                    "food_id": "INT NOT NULL DEFAULT 0",
                    "quantity": "INT NOT NULL DEFAULT 1",
                    "created_at": "DATETIME(6) NULL",
                    "updated_at": "DATETIME(6) NULL",
                }
                for column, definition in cart_definitions.items():
                    if column not in cart_columns:
                        cursor.execute(f"ALTER TABLE session_carts ADD COLUMN `{column}` {definition}")
                        added.append(f"session_carts.{column}")
                cursor.execute("SHOW INDEX FROM session_carts")
                cart_indexes = {row[2].lower() for row in cursor.fetchall()}
                if "ix_session_carts_session_food" not in cart_indexes:
                    cursor.execute("CREATE INDEX ix_session_carts_session_food ON session_carts (session_id, food_id)")
                    added.append("session_carts.ix_session_carts_session_food")

            # Backfill order ownership from structured legacy customer_details JSON.
            cursor.execute("SELECT order_id, status, payment_method, payment_id, customer_details FROM orders")
            legacy_orders = cursor.fetchall()
            ownership_backfilled = 0
            with transaction.atomic():
                with connection.cursor() as update_cursor:
                    for order_id, status, method, payment_id, raw_details in legacy_orders:
                        try:
                            details = json.loads(raw_details or "{}")
                            uid = int(details.get("user_id")) if details.get("user_id") is not None else None
                        except (TypeError, ValueError, json.JSONDecodeError):
                            uid = None
                        old_status = str(status or "placed").strip().lower()
                        order_status = "placed" if old_status == "completed" else old_status
                        if order_status not in {"placed", "confirmed", "preparing", "out-for-delivery", "delivered", "cancelled", "awaiting_payment"}:
                            order_status = "placed"
                        update_cursor.execute(
                            """UPDATE orders SET user_id = COALESCE(user_id, %s),
                               payment_status = CASE WHEN payment_id IS NOT NULL THEN 'paid'
                                                     WHEN UPPER(COALESCE(payment_method,'')) = 'COD' THEN 'cod_due'
                                                     ELSE payment_status END,
                               order_status = CASE WHEN status = 'completed' THEN 'placed'
                                                   WHEN status IN ('placed','confirmed','preparing','out-for-delivery','delivered','cancelled','awaiting_payment') THEN status
                                                   ELSE order_status END
                               WHERE order_id = %s""",
                            [uid, order_id],
                        )
                        if uid is not None:
                            ownership_backfilled += 1

        self.stdout.write(self.style.SUCCESS(
            f"Schema check complete. Added: {', '.join(added) if added else 'none (already up to date)'}. "
            f"Legacy order ownership matched from customer_details: {ownership_backfilled}. "
            f"Legacy plaintext passwords converted to Django hashes: {passwords_hashed}."
        ))
        self.stdout.write(self.style.WARNING(
            "Review unowned legacy orders manually. Existing food prices are unchanged by this command. "
            "Run update_savora_market_prices first in dry-run mode to review demo pricing suggestions. "
            "Existing plaintext passwords were hashed; users can still sign in with their original passwords."
        ))
