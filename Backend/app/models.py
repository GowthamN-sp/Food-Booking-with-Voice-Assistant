"""Django model descriptions for Savora's legacy MySQL schema.

These tables predate Django's migration system, so Meta.managed remains False.
Use `manage.py migrate_savora_schema` for the documented, idempotent compatibility
changes; do not toggle managed=True without a full schema migration plan.
"""
from django.db import models


class FoodItems(models.Model):
    foodid = models.AutoField(primary_key=True, db_column="FoodID")
    foodname = models.CharField(max_length=100, db_column="FoodName")
    description = models.TextField(blank=True, null=True, db_column="Description")
    price = models.DecimalField(max_digits=10, decimal_places=2, db_column="Price")
    category = models.CharField(max_length=50, blank=True, null=True, db_column="Category")
    imagename = models.CharField(max_length=255, db_column="ImageName")
    isavailable = models.IntegerField(default=1, db_column="IsAvailable")
    rating = models.DecimalField(max_digits=3, decimal_places=1, blank=True, null=True, db_column="Rating")
    dateadded = models.DateTimeField(auto_now_add=True, db_column="DateAdded")
    quantity = models.IntegerField(default=0, db_column="Quantity", help_text="Legacy field; cart quantity now belongs in SessionCarts.")
    stock = models.IntegerField(default=0, db_column="Stock", help_text="Current stock count when TrackInventory is enabled.")
    trackinventory = models.IntegerField(default=0, db_column="TrackInventory", help_text="1 enables stock tracking, including when Stock reaches zero.")

    class Meta:
        managed = False
        db_table = "FoodItems"

    def __str__(self):
        return self.foodname


class Orders(models.Model):
    id = models.AutoField(primary_key=True)
    order_id = models.CharField(max_length=100, unique=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=50, default="pending")  # legacy-compatible status column
    payment_status = models.CharField(max_length=32, default="pending")
    order_status = models.CharField(max_length=32, default="placed")
    user_id = models.BigIntegerField(blank=True, null=True, db_index=True)
    delivery_address = models.TextField(blank=True, null=True)
    customer_phone = models.CharField(max_length=30, blank=True, null=True)
    items = models.TextField(blank=True, null=True)
    customer_details = models.TextField(blank=True, null=True)
    signature = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "orders"
        indexes = [models.Index(fields=["user_id"], name="ix_orders_user_id")]

    def __str__(self):
        return f"Order {self.order_id}"


class SessionCarts(models.Model):
    id = models.AutoField(primary_key=True)
    session_id = models.CharField(max_length=255)
    food_id = models.IntegerField()
    quantity = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "session_carts"
        indexes = [models.Index(fields=["session_id", "food_id"], name="ix_session_carts_session_food")]

    def __str__(self):
        return f"Session {self.session_id} - Food {self.food_id}"


class Users(models.Model):
    user_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    email = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=255)
    is_logged_in = models.IntegerField(default=0)
    token_version = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "users"

    def __str__(self):
        return self.name
