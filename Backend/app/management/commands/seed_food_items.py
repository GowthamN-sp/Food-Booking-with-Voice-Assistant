from django.core.management.base import BaseCommand
from django.db import connection

FOOD_ITEMS = [
    {
        "name": "Paneer Tikka Pizza",
        "description": "Charred paneer, onions, peppers and smoky tikka sauce.",
        "price": 279,
        "category": "Pizza",
        "image": "/food/paneer-tikka-pizza.svg",
    },
    {
        "name": "BBQ Chicken Pizza",
        "description": "Smoky BBQ chicken, mozzarella and caramelized onions.",
        "price": 319,
        "category": "Pizza",
        "image": "/food/bbq-chicken-pizza.svg",
    },
    {
        "name": "Mexican Green Wave Pizza",
        "description": "Jalapeño, capsicum, onion, corn and spicy salsa.",
        "price": 259,
        "category": "Pizza",
        "image": "/food/mexican-pizza.svg",
    },
    {
        "name": "Veggie Supreme Burger",
        "description": "Crispy veggie patty, lettuce, tomato and house sauce.",
        "price": 149,
        "category": "Burger",
        "image": "/food/veggie-supreme-burger.svg",
    },
    {
        "name": "Classic Cheese Burger",
        "description": "Juicy patty, cheddar, onion, pickles and burger sauce.",
        "price": 169,
        "category": "Burger",
        "image": "/food/classic-cheese-burger.svg",
    },
    {
        "name": "Crispy Chicken Burger",
        "description": "Crunchy chicken fillet, lettuce and creamy mayo.",
        "price": 199,
        "category": "Burger",
        "image": "/food/crispy-chicken-burger.svg",
    },
    {
        "name": "Mutton Biryani",
        "description": "Fragrant basmati rice layered with tender mutton and spices.",
        "price": 329,
        "category": "Main Course",
        "image": "/food/mutton-biryani.svg",
    },
    {
        "name": "Paneer Butter Masala",
        "description": "Soft paneer cubes in a rich tomato-butter gravy.",
        "price": 229,
        "category": "Main Course",
        "image": "/food/paneer-butter-masala.svg",
    },
    {
        "name": "Butter Chicken",
        "description": "Creamy tomato gravy with tender tandoori chicken.",
        "price": 269,
        "category": "Main Course",
        "image": "/food/butter-chicken.svg",
    },
    {
        "name": "Chicken 65",
        "description": "Crispy South Indian chicken tossed with curry leaves and spices.",
        "price": 179,
        "category": "Snacks",
        "image": "/food/chicken-65.svg",
    },
    {
        "name": "Paneer Tikka",
        "description": "Tandoori paneer with peppers, onions and mint chutney.",
        "price": 169,
        "category": "Snacks",
        "image": "/food/paneer-tikka.svg",
    },
    {
        "name": "Gobi Manchurian",
        "description": "Crispy cauliflower in a tangy Indo-Chinese sauce.",
        "price": 139,
        "category": "Snacks",
        "image": "/food/gobi-manchurian.svg",
    },
    {
        "name": "Masala Dosa",
        "description": "Golden dosa stuffed with spiced potato masala and chutneys.",
        "price": 99,
        "category": "South Indian",
        "image": "/food/masala-dosa.svg",
    },
    {
        "name": "Idli Vada Combo",
        "description": "Steamed idlis and crispy vada served with sambar.",
        "price": 99,
        "category": "South Indian",
        "image": "/food/idli-vada.svg",
    },
    {
        "name": "Paneer Dosa",
        "description": "Crispy dosa filled with spiced paneer and vegetables.",
        "price": 139,
        "category": "South Indian",
        "image": "/food/paneer-dosa.svg",
    },
    {
        "name": "Gulab Jamun",
        "description": "Warm soft dumplings soaked in fragrant sugar syrup.",
        "price": 79,
        "category": "Dessert",
        "image": "/food/gulab-jamun.svg",
    },
    {
        "name": "Chocolate Brownie",
        "description": "Fudgy chocolate brownie with a rich cocoa finish.",
        "price": 109,
        "category": "Dessert",
        "image": "/food/brownie.svg",
    },
    {
        "name": "Mango Lassi",
        "description": "Chilled creamy yogurt blended with ripe mango.",
        "price": 89,
        "category": "Drinks",
        "image": "/food/mango-lassi.svg",
    },
    {
        "name": "Cold Coffee",
        "description": "Iced creamy coffee with a smooth chocolate finish.",
        "price": 99,
        "category": "Drinks",
        "image": "/food/cold-coffee.svg",
    },
    {
        "name": "Fresh Lime Soda",
        "description": "Refreshing lime, sparkling water and a hint of sweetness.",
        "price": 59,
        "category": "Drinks",
        "image": "/food/lime-soda.svg",
    }
]

class Command(BaseCommand):
    help = "Seed Savora with additional food items."

    def handle(self, *args, **options):
        inserted = 0
        skipped = 0

        with connection.cursor() as cursor:
            for item in FOOD_ITEMS:
                cursor.execute(
                    "SELECT FoodID FROM FoodItems WHERE FoodName = %s LIMIT 1",
                    [item["name"]],
                )
                if cursor.fetchone():
                    skipped += 1
                    continue

                cursor.execute(
                    """
                    INSERT INTO FoodItems
                        (FoodName, Description, Price, Category, ImageName,
                         IsAvailable, DateAdded, Quantity, Stock, TrackInventory)
                    VALUES (%s, %s, %s, %s, %s, 1, NOW(), 0, 100, 1)
                    """,
                    [
                        item["name"], item["description"], item["price"],
                        item["category"], item["image"]
                    ],
                )
                inserted += 1

        self.stdout.write(self.style.SUCCESS(
            f"Savora menu seed complete: {inserted} added, {skipped} already existed."
        ))
