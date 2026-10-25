"""Preview/apply suggested mid-range Bengaluru menu prices in INR.

Dry run (default): python manage.py update_savora_market_prices
Apply after reviewing: python manage.py update_savora_market_prices --apply

These are illustrative demo prices, not live quotes or a margin/cost study.
Check portion size, supplier cost, tax, delivery commissions and nearby menus before
using this as a real business price list. The command never changes rows in dry-run mode.
"""
from decimal import Decimal
import re
from django.core.management.base import BaseCommand
from django.db import connection, transaction

EXACT_PRICES = {
    "margherita pizza": Decimal("199.00"),
    "farmhouse pizza": Decimal("249.00"),
    "pepperoni pizza": Decimal("299.00"),
    "veggie burger": Decimal("129.00"),
    "chicken burger": Decimal("179.00"),
    "cheese burger": Decimal("149.00"),
    "chicken biryani": Decimal("219.00"),
    "thali": Decimal("189.00"),
    "south indian thali": Decimal("189.00"),
    "masala dosa": Decimal("99.00"),
    "obbattu": Decimal("79.00"),
    "vangi bath": Decimal("99.00"),
    "paneer tikka pizza": Decimal("279.00"),
    "bbq chicken pizza": Decimal("319.00"),
    "mexican green wave pizza": Decimal("259.00"),
    "veggie supreme burger": Decimal("149.00"),
    "classic cheese burger": Decimal("169.00"),
    "crispy chicken burger": Decimal("199.00"),
    "mutton biryani": Decimal("329.00"),
    "paneer butter masala": Decimal("229.00"),
    "butter chicken": Decimal("269.00"),
    "chicken 65": Decimal("179.00"),
    "paneer tikka": Decimal("169.00"),
    "gobi manchurian": Decimal("139.00"),
    "idli vada combo": Decimal("99.00"),
    "paneer dosa": Decimal("139.00"),
    "gulab jamun": Decimal("79.00"),
    "chocolate brownie": Decimal("109.00"),
    "mango lassi": Decimal("89.00"),
    "cold coffee": Decimal("99.00"),
    "fresh lime soda": Decimal("59.00"),
}


def suggest_price(name, category):
    key = re.sub(r"\s+", " ", str(name or "").strip().lower())
    cat = re.sub(r"\s+", " ", str(category or "").strip().lower())
    if key in EXACT_PRICES:
        return EXACT_PRICES[key], "exact menu benchmark"
    if "pizza" in cat or "pizza" in key:
        if any(w in key for w in ("pepperoni", "bbq", "barbecue", "chicken", "meat", "non veg", "non-veg")):
            return Decimal("299.00"), "pizza category + meat/premium name"
        if any(w in key for w in ("paneer", "supreme", "special", "premium")):
            return Decimal("279.00"), "pizza category + premium name"
        if any(w in key for w in ("margherita", "plain", "classic")):
            return Decimal("199.00"), "pizza category + simple name"
        return Decimal("249.00"), "pizza category default"
    if "burger" in cat or "burger" in key:
        if any(w in key for w in ("chicken", "crispy", "meat")):
            return Decimal("189.00"), "burger category + chicken/meat name"
        if any(w in key for w in ("cheese", "double", "special", "supreme")):
            return Decimal("159.00"), "burger category + premium name"
        if any(w in key for w in ("veg", "veggie", "aloo", "potato")):
            return Decimal("129.00"), "burger category + vegetarian name"
        return Decimal("149.00"), "burger category default"
    if any(w in cat or w in key for w in ("south indian", "dosa", "idli", "vada", "uttapam", "upma")):
        if "paneer" in key or "ghee" in key or "special" in key:
            return Decimal("139.00"), "South Indian category + premium name"
        if "idli" in key or "vada" in key or "plain dosa" in key:
            return Decimal("79.00"), "South Indian category + basic name"
        if "thali" in key:
            return Decimal("189.00"), "thali name"
        return Decimal("99.00"), "South Indian category default"
    if any(w in cat or w in key for w in ("biryani", "main course", "curry", "gravy", "thali", "rice")):
        if "mutton" in key:
            return Decimal("329.00"), "main course + mutton name"
        if "chicken" in key or "egg" in key:
            return Decimal("239.00"), "main course + chicken/egg name"
        if "paneer" in key:
            return Decimal("229.00"), "main course + paneer name"
        if "thali" in key:
            return Decimal("189.00"), "thali name"
        return Decimal("199.00"), "main course category default"
    if any(w in cat or w in key for w in ("drink", "beverage", "coffee", "lassi", "soda", "juice", "shake", "tea")):
        if "lime" in key or "soda" in key:
            return Decimal("59.00"), "drink name"
        if "coffee" in key or "shake" in key:
            return Decimal("99.00"), "drink name"
        return Decimal("89.00"), "drinks category default"
    if any(w in cat or w in key for w in ("dessert", "sweet", "brownie", "jamun", "ice cream", "cake", "obbattu")):
        if "brownie" in key or "cake" in key:
            return Decimal("109.00"), "dessert name"
        return Decimal("79.00"), "dessert category default"
    if any(w in cat or w in key for w in ("snack", "starter", "tikka", "manchurian", "fries", "65")):
        if "chicken" in key or "paneer" in key:
            return Decimal("179.00"), "snack category + protein name"
        return Decimal("139.00"), "snacks category default"
    return None, "unclassified; left unchanged for manual review"


class Command(BaseCommand):
    help = "Preview/apply suggested INR menu prices for all classifiable menu rows."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Write the proposed prices to MySQL; default is preview only.")

    def handle(self, *args, **options):
        apply = bool(options["apply"])
        with connection.cursor() as cursor:
            cursor.execute("SELECT FoodID, FoodName, Category, Price FROM FoodItems ORDER BY Category, FoodName")
            rows = cursor.fetchall()
        proposals = []
        skipped = []
        for food_id, name, category, old_raw in rows:
            suggested, reason = suggest_price(name, category)
            if suggested is None:
                skipped.append((food_id, name, category, old_raw))
                continue
            old = Decimal(str(old_raw))
            proposals.append((int(food_id), str(name), old, suggested, reason))
        for food_id, name, old, new, reason in proposals:
            if old == new:
                state = "UNCHANGED"
            else:
                state = "UPDATE" if apply else "PREVIEW"
            self.stdout.write(f"{state}: #{food_id} {name}: ₹{old:.2f} -> ₹{new:.2f} ({reason})")
        if apply:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    for food_id, _name, _old, new, _reason in proposals:
                        cursor.execute("UPDATE FoodItems SET Price = %s WHERE FoodID = %s", [f"{new:.2f}", food_id])
        self.stdout.write(self.style.SUCCESS(f"Classified {len(proposals)} of {len(rows)} current menu items."))
        if skipped:
            self.stdout.write(self.style.WARNING("Manual pricing needed for: " + ", ".join(f"#{i} {n} [{c}]" for i, n, c, _p in skipped)))
        if not apply:
            self.stdout.write(self.style.WARNING("DRY RUN ONLY: no database prices were changed. Review every proposal, back up MySQL, then use --apply if these demo prices suit your portions and costs."))
        else:
            self.stdout.write(self.style.SUCCESS("Suggested prices committed. Verify the menu in the app before enabling real payments."))
