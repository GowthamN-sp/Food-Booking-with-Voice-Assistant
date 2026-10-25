USE voiceassistant;

-- EchoEats realistic food image paths
UPDATE fooditems SET ImageName = '/food/margherita-pizza.jpg' WHERE FoodName = 'Margherita Pizza';
UPDATE fooditems SET ImageName = '/food/farmhouse-pizza.jpg' WHERE FoodName = 'Farmhouse Pizza';
UPDATE fooditems SET ImageName = '/food/pepperoni-pizza.jpg' WHERE FoodName = 'Pepperoni Pizza';
UPDATE fooditems SET ImageName = '/food/veggie-burger.jpg' WHERE FoodName = 'Veggie Burger';
UPDATE fooditems SET ImageName = '/food/chicken-burger.jpg' WHERE FoodName = 'Chicken Burger';
UPDATE fooditems SET ImageName = '/food/cheese-burst-burger.jpg' WHERE FoodName = 'Cheese Burst Burger';
UPDATE fooditems SET ImageName = '/food/chicken-biryani.jpg' WHERE FoodName = 'Chicken Biryani';
UPDATE fooditems SET ImageName = '/food/south-indian-thali.jpg' WHERE FoodName = 'South Indian Thali';
UPDATE fooditems SET ImageName = '/food/masala-dosa.jpg' WHERE FoodName = 'Masala Dosa';
UPDATE fooditems SET ImageName = '/food/obbattu.jpg' WHERE FoodName = 'Obbattu';
UPDATE fooditems SET ImageName = '/food/vangibath.jpg' WHERE FoodName = 'Vangibath';
UPDATE fooditems SET ImageName = '/food/paneer-tikka-pizza.jpg' WHERE FoodName = 'Paneer Tikka Pizza';
UPDATE fooditems SET ImageName = '/food/bbq-chicken-pizza.jpg' WHERE FoodName = 'BBQ Chicken Pizza';
UPDATE fooditems SET ImageName = '/food/mexican-green-wave-pizza.jpg' WHERE FoodName = 'Mexican Green Wave Pizza';
UPDATE fooditems SET ImageName = '/food/veggie-supreme-burger.jpg' WHERE FoodName = 'Veggie Supreme Burger';
UPDATE fooditems SET ImageName = '/food/classic-cheese-burger.jpg' WHERE FoodName = 'Classic Cheese Burger';
UPDATE fooditems SET ImageName = '/food/crispy-chicken-burger.jpg' WHERE FoodName = 'Crispy Chicken Burger';
UPDATE fooditems SET ImageName = '/food/mutton-biryani.jpg' WHERE FoodName = 'Mutton Biryani';
UPDATE fooditems SET ImageName = '/food/paneer-butter-masala.jpg' WHERE FoodName = 'Paneer Butter Masala';
UPDATE fooditems SET ImageName = '/food/butter-chicken.jpg' WHERE FoodName = 'Butter Chicken';
UPDATE fooditems SET ImageName = '/food/chicken-65.jpg' WHERE FoodName = 'Chicken 65';
UPDATE fooditems SET ImageName = '/food/paneer-tikka.jpg' WHERE FoodName = 'Paneer Tikka';
UPDATE fooditems SET ImageName = '/food/gobi-manchurian.jpg' WHERE FoodName = 'Gobi Manchurian';
UPDATE fooditems SET ImageName = '/food/idli-vada-combo.jpg' WHERE FoodName = 'Idli Vada Combo';
UPDATE fooditems SET ImageName = '/food/paneer-dosa.jpg' WHERE FoodName = 'Paneer Dosa';
UPDATE fooditems SET ImageName = '/food/gulab-jamun.jpg' WHERE FoodName = 'Gulab Jamun';
UPDATE fooditems SET ImageName = '/food/chocolate-brownie.jpg' WHERE FoodName = 'Chocolate Brownie';
UPDATE fooditems SET ImageName = '/food/mango-lassi.jpg' WHERE FoodName = 'Mango Lassi';
UPDATE fooditems SET ImageName = '/food/cold-coffee.jpg' WHERE FoodName = 'Cold Coffee';
UPDATE fooditems SET ImageName = '/food/fresh-lime-soda.jpg' WHERE FoodName = 'Fresh Lime Soda';

SELECT FoodID, FoodName, ImageName FROM fooditems ORDER BY FoodID;