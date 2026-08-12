from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

TN_DISTRICTS = [
    "Ariyalur", "Chengalpattu", "Chennai", "Coimbatore", "Cuddalore", "Dharmapuri",
    "Dindigul", "Erode", "Kallakurichi", "Kanchipuram", "Kanyakumari", "Karur",
    "Krishnagiri", "Madurai", "Mayiladuthurai", "Nagapattinam", "Namakkal",
    "Nilgiris", "Perambalur", "Pudukkottai", "Ramanathapuram", "Ranipet", "Salem",
    "Sivaganga", "Tenkasi", "Thanjavur", "Theni", "Thoothukudi", "Tiruchirappalli",
    "Tirunelveli", "Tirupathur", "Tiruppur", "Tiruvallur", "Tiruvannamalai",
    "Tiruvarur", "Vellore", "Viluppuram", "Virudhunagar"
]


class User(UserMixin, db.Model):
    """Base account used for both Farmers and Customers (and Admin)."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="customer")  # farmer, customer, admin
    avatar = db.Column(db.String(255), default="default-avatar.png")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    farm = db.relationship("Farm", backref="owner", uselist=False, cascade="all, delete-orphan")
    posts = db.relationship("Post", backref="author", cascade="all, delete-orphan")
    comments = db.relationship("Comment", backref="author", cascade="all, delete-orphan")
    reviews_written = db.relationship("Review", backref="customer", foreign_keys="Review.customer_id")

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_farmer(self):
        return self.role == "farmer"

    @property
    def is_admin(self):
        return self.role == "admin"


class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    icon = db.Column(db.String(50), default="leaf")

    products = db.relationship("Product", backref="category", lazy=True)


class Farm(db.Model):
    __tablename__ = "farms"
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    farm_name = db.Column(db.String(150), nullable=False)
    village = db.Column(db.String(100))
    district = db.Column(db.String(100))
    pincode = db.Column(db.String(10))
    description = db.Column(db.Text)
    experience_years = db.Column(db.Integer, default=0)
    organic_status = db.Column(db.String(20), default="Not Certified")  # Certified / In-Conversion / Not Certified
    farm_area = db.Column(db.String(50))
    logo = db.Column(db.String(255), default="default-farm-logo.png")
    cover_photo = db.Column(db.String(255), default="default-cover.jpg")
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    map_url = db.Column(db.String(255))
    verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    products = db.relationship("Product", backref="farm", cascade="all, delete-orphan")
    reviews = db.relationship("Review", backref="farm", cascade="all, delete-orphan")
    followers = db.relationship("Follow", backref="farm", cascade="all, delete-orphan")

    @property
    def avg_rating(self):
        if not self.reviews:
            return 0
        return round(sum(r.rating for r in self.reviews) / len(self.reviews), 1)

    @property
    def follower_count(self):
        return len(self.followers)


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    farm_id = db.Column(db.Integer, db.ForeignKey("farms.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"))

    name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), default="kg")  # kg, dozen, litre, piece
    quantity_available = db.Column(db.Float, default=0)
    harvest_date = db.Column(db.Date)
    description = db.Column(db.Text)
    image = db.Column(db.String(255), default="default-product.jpg")
    is_organic = db.Column(db.Boolean, default=False)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Post(db.Model):
    __tablename__ = "posts"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    image = db.Column(db.String(255))
    caption = db.Column(db.Text)
    location = db.Column(db.String(150))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    comments = db.relationship("Comment", backref="post", cascade="all, delete-orphan")
    likes = db.relationship("Like", backref="post", cascade="all, delete-orphan")

    @property
    def like_count(self):
        return len(self.likes)

    @property
    def comment_count(self):
        return len(self.comments)


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    text = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Like(db.Model):
    __tablename__ = "likes"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    __table_args__ = (db.UniqueConstraint("post_id", "user_id", name="uq_like_once"),)


class Follow(db.Model):
    __tablename__ = "follows"
    id = db.Column(db.Integer, primary_key=True)
    farm_id = db.Column(db.Integer, db.ForeignKey("farms.id"), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint("farm_id", "customer_id", name="uq_follow_once"),)


class Review(db.Model):
    __tablename__ = "reviews"
    id = db.Column(db.Integer, primary_key=True)
    farm_id = db.Column(db.Integer, db.ForeignKey("farms.id"), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    review_text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Message(db.Model):
    __tablename__ = "messages"
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship("User", foreign_keys=[sender_id])
    receiver = db.relationship("User", foreign_keys=[receiver_id])


class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(150))
    description = db.Column(db.String(300))
    ntype = db.Column(db.String(50))  # follow, comment, review, message, product
    seen = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="notifications")
