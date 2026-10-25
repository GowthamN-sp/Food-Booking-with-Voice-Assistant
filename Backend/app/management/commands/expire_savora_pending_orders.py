"""Expire Razorpay orders left pending for more than the chosen number of minutes.

Schedule this command every 10 minutes in production so abandoned checkouts release
tracked stock: python manage.py expire_savora_pending_orders --minutes 30
"""
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from app.views import _load_order_items, _release_reserved_stock
import json

class Command(BaseCommand):
    help = "Expire abandoned pending Razorpay orders and release reserved stock."

    def add_arguments(self, parser):
        parser.add_argument("--minutes", type=int, default=30, help="Pending age before release; minimum 10 minutes.")

    def handle(self, *args, **options):
        minutes = max(10, min(1440, int(options["minutes"])))
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT order_id, items FROM orders
                   WHERE payment_method = 'RAZORPAY' AND payment_status = 'pending'
                     AND order_status = 'awaiting_payment'
                     AND created_at < DATE_SUB(CURRENT_TIMESTAMP, INTERVAL %s MINUTE)""",
                [minutes],
            )
            candidates = cursor.fetchall()
        expired = 0
        for order_id, _items in candidates:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT items, payment_status, order_status FROM orders WHERE order_id = %s FOR UPDATE",
                        [order_id],
                    )
                    row = cursor.fetchone()
                    if not row:
                        continue
                    raw_items, payment_status, order_status = row
                    if payment_status != "pending" or order_status != "awaiting_payment":
                        continue
                    released = _release_reserved_stock(_load_order_items(raw_items))
                    cursor.execute(
                        """UPDATE orders SET items = %s, payment_status = 'expired',
                           order_status = 'cancelled', status = 'cancelled', updated_at = CURRENT_TIMESTAMP
                           WHERE order_id = %s AND payment_status = 'pending' AND order_status = 'awaiting_payment'""",
                        [json.dumps(released, ensure_ascii=False), order_id],
                    )
                    if cursor.rowcount == 1:
                        expired += 1
        self.stdout.write(self.style.SUCCESS(f"Expired {expired} pending order(s); their tracked stock reservations were released."))
