"""
Seed the TNFarm database with sample data so the site is browsable immediately.
Run:  python seed.py
"""
from datetime import date, timedelta
from app import create_app
from models import db, User, Farm, Category, Product, Post, Review, Follow, Like, Comment

app = create_app()

CATEGORIES = ["Vegetables", "Fruits", "Seeds", "Flowers", "Milk & Dairy", "Organic Specials"]

FARMERS = [
    dict(name="Murugan Selvam", email="murugan@example.com", phone="9840000001",
         farm_name="Murugan Organic Farm", village="Thiruvallur", district="Tiruvallur",
         pincode="602001", description="Three generations growing organic vegetables and millets.",
         experience_years=15, organic_status="Certified", farm_area="4 acres"),
    dict(name="Lakshmi Devi", email="lakshmi@example.com", phone="9840000002",
         farm_name="Lakshmi Fruit Orchard", village="Dindigul", district="Dindigul",
         pincode="624001", description="Mango and guava orchard supplying fresh fruit to Madurai and Trichy.",
         experience_years=10, organic_status="In-Conversion", farm_area="6 acres"),
    dict(name="Karthik Raja", email="karthik@example.com", phone="9840000003",
         farm_name="Karthik Dairy & Greens", village="Erode", district="Erode",
         pincode="638001", description="Native cow milk and leafy greens, direct from farm to family.",
         experience_years=8, organic_status="Not Certified", farm_area="3 acres"),
]

CUSTOMERS = [
    dict(name="Priya Anand", email="priya@example.com", phone="9940000001"),
    dict(name="Ramesh Kumar", email="ramesh@example.com", phone="9940000002"),
]

PRODUCTS_BY_FARM = [
    # index matches FARMERS order
    [
        dict(name="Country Tomatoes", price=40, unit="kg", quantity_available=120, is_organic=True,
             description="Vine-ripened native tomatoes, harvested this week."),
        dict(name="Little Millet (Samai)", price=90, unit="kg", quantity_available=60, is_organic=True,
             description="Stone-ground little millet, chemical-free."),
        dict(name="Fresh Drumstick", price=60, unit="kg", quantity_available=40, is_organic=True,
             description="Nutrient-rich drumsticks picked fresh."),
    ],
    [
        dict(name="Alphonso Mangoes", price=150, unit="kg", quantity_available=200, is_organic=False,
             description="Sweet, fragrant mangoes at peak ripeness."),
        dict(name="Pink Guava", price=70, unit="kg", quantity_available=80, is_organic=False,
             description="Juicy pink guava, great for juices and salads."),
    ],
    [
        dict(name="A2 Cow Milk", price=80, unit="litre", quantity_available=50, is_organic=True,
             description="Fresh native breed cow milk delivered same-day."),
        dict(name="Organic Spinach", price=30, unit="kg", quantity_available=35, is_organic=True,
             description="Locally grown spinach, cut to order."),
    ],
]

POSTS = [
    (0, "Harvest day for our little millets! 🌾", "Tiruvallur"),
    (1, "Mango season has begun on the orchard 🥭", "Dindigul"),
    (2, "Morning milking with our native cows 🐄", "Erode"),
]


def run():
    with app.app_context():
        db.drop_all()
        db.create_all()

        categories = {}
        for c in CATEGORIES:
            cat = Category(name=c)
            db.session.add(cat)
            categories[c] = cat
        db.session.flush()

        farmers = []
        for f in FARMERS:
            user = User(name=f["name"], email=f["email"], phone=f["phone"], role="farmer")
            user.set_password("password123")
            db.session.add(user)
            db.session.flush()

            farm = Farm(
                owner_id=user.id, farm_name=f["farm_name"], village=f["village"],
                district=f["district"], pincode=f["pincode"], description=f["description"],
                experience_years=f["experience_years"], organic_status=f["organic_status"],
                farm_area=f["farm_area"], verified=True,
            )
            db.session.add(farm)
            db.session.flush()
            farmers.append((user, farm))

        customers = []
        for c in CUSTOMERS:
            user = User(name=c["name"], email=c["email"], phone=c["phone"], role="customer")
            user.set_password("password123")
            db.session.add(user)
            db.session.flush()
            customers.append(user)

        admin = User(name="TNFarm Admin", email="admin@tnfarm.local", role="admin")
        admin.set_password("admin123")
        db.session.add(admin)

        cat_cycle = list(categories.values())
        for idx, (user, farm) in enumerate(farmers):
            for j, p in enumerate(PRODUCTS_BY_FARM[idx]):
                product = Product(
                    farm_id=farm.id,
                    category_id=cat_cycle[(idx + j) % len(cat_cycle)].id,
                    name=p["name"], price=p["price"], unit=p["unit"],
                    quantity_available=p["quantity_available"],
                    harvest_date=date.today() - timedelta(days=j),
                    description=p["description"], is_organic=p["is_organic"],
                )
                db.session.add(product)

        db.session.flush()

        for farm_idx, caption, location in POSTS:
            user = farmers[farm_idx][0]
            post = Post(user_id=user.id, caption=caption, location=location)
            db.session.add(post)
            db.session.flush()
            db.session.add(Like(post_id=post.id, user_id=customers[0].id))
            db.session.add(Comment(post_id=post.id, user_id=customers[1].id, text="Looks wonderful! 🌿"))

        db.session.add(Follow(farm_id=farmers[0][1].id, customer_id=customers[0].id))
        db.session.add(Follow(farm_id=farmers[1][1].id, customer_id=customers[0].id))
        db.session.add(Review(farm_id=farmers[0][1].id, customer_id=customers[0].id, rating=5,
                               review_text="Best organic tomatoes I've had. Will order again!"))
        db.session.add(Review(farm_id=farmers[1][1].id, customer_id=customers[1].id, rating=4,
                               review_text="Great mangoes, visited the orchard with my family."))

        db.session.commit()
        print("Database seeded successfully.")
        print("Login as farmer: murugan@example.com / password123")
        print("Login as customer: priya@example.com / password123")
        print("Login as admin: admin@tnfarm.local / admin123")


if __name__ == "__main__":
    run()
