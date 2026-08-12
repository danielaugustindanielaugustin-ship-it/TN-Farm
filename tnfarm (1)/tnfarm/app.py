import os
from datetime import datetime, date, timezone
from functools import wraps

from flask import (
    Flask, render_template, redirect, url_for, flash, request, abort, jsonify
)
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from werkzeug.utils import secure_filename

from config import Config
from models import (
    db, User, Farm, Product, Category, Post, Comment, Like, Follow,
    Review, Message, Notification, TN_DISTRICTS
)
from ai_helper import chatbot_reply, suggest_product_description, suggest_post_caption

ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.login_message = "Please log in to continue."
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ---------- helpers ----------
    def allowed_file(filename):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

    def save_image(file_storage, subfolder=""):
        if not file_storage or file_storage.filename == "":
            return None
        if not allowed_file(file_storage.filename):
            flash("Unsupported image type.", "error")
            return None
        filename = secure_filename(file_storage.filename)
        unique_name = f"{datetime.now(timezone.utc).timestamp():.0f}_{filename}"
        folder = os.path.join(app.config["UPLOAD_FOLDER"], subfolder)
        os.makedirs(folder, exist_ok=True)
        file_storage.save(os.path.join(folder, unique_name))
        return f"{subfolder}/{unique_name}" if subfolder else unique_name

    def farmer_required(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.is_farmer:
                flash("Only farmers can access that page.", "error")
                return redirect(url_for("home"))
            return f(*args, **kwargs)
        return wrapper

    def notify(user_id, title, description, ntype):
        n = Notification(user_id=user_id, title=title, description=description, ntype=ntype)
        db.session.add(n)

    app.jinja_env.globals["TN_DISTRICTS"] = TN_DISTRICTS
    app.jinja_env.globals["current_year"] = datetime.now(timezone.utc).year

    # ---------- HOME ----------
    @app.route("/")
    def home():
        q = request.args.get("q", "").strip()
        district = request.args.get("district", "")

        featured_farms = Farm.query.order_by(Farm.verified.desc(), Farm.created_at.desc()).limit(6).all()
        trending_products = Product.query.filter_by(is_available=True).order_by(Product.created_at.desc()).limit(8).all()
        recent_posts = Post.query.order_by(Post.created_at.desc()).limit(6).all()
        categories = Category.query.all()

        if q or district:
            farm_q = Farm.query
            if q:
                like = f"%{q}%"
                farm_q = farm_q.filter(
                    db.or_(Farm.farm_name.ilike(like), Farm.village.ilike(like), Farm.district.ilike(like))
                )
            if district:
                farm_q = farm_q.filter(Farm.district == district)
            search_results = farm_q.all()
        else:
            search_results = None

        return render_template(
            "home.html",
            featured_farms=featured_farms,
            trending_products=trending_products,
            recent_posts=recent_posts,
            categories=categories,
            search_results=search_results,
            q=q,
            district=district,
        )

    # ---------- AUTH ----------
    @app.route("/register/<role>", methods=["GET", "POST"])
    def register(role):
        if role not in ("farmer", "customer"):
            abort(404)
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            phone = request.form.get("phone", "").strip()
            password = request.form.get("password", "")

            if not name or not email or not password:
                flash("Please fill in all required fields.", "error")
                return render_template("register.html", role=role)

            if User.query.filter_by(email=email).first():
                flash("An account with that email already exists.", "error")
                return render_template("register.html", role=role)

            user = User(name=name, email=email, phone=phone, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.flush()

            if role == "farmer":
                farm = Farm(
                    owner_id=user.id,
                    farm_name=request.form.get("farm_name", f"{name}'s Farm"),
                    village=request.form.get("village", ""),
                    district=request.form.get("district", ""),
                    pincode=request.form.get("pincode", ""),
                )
                db.session.add(farm)

            db.session.commit()
            login_user(user)
            flash(f"Welcome to TNFarm, {name}!", "success")
            if role == "farmer":
                return redirect(url_for("edit_farm"))
            return redirect(url_for("home"))

        return render_template("register.html", role=role)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                login_user(user)
                flash(f"Welcome back, {user.name}!", "success")
                return redirect(request.args.get("next") or url_for("home"))
            flash("Invalid email or password.", "error")
        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("You have been logged out.", "success")
        return redirect(url_for("home"))

    # ---------- FARM / FARMER PROFILE ----------
    @app.route("/farm/<int:farm_id>")
    def farm_profile(farm_id):
        farm = Farm.query.get_or_404(farm_id)
        products = Product.query.filter_by(farm_id=farm.id).all()
        posts = Post.query.filter_by(user_id=farm.owner_id).order_by(Post.created_at.desc()).all()
        reviews = Review.query.filter_by(farm_id=farm.id).order_by(Review.created_at.desc()).all()
        is_following = False
        if current_user.is_authenticated:
            is_following = Follow.query.filter_by(farm_id=farm.id, customer_id=current_user.id).first() is not None
        return render_template(
            "farm_profile.html", farm=farm, products=products, posts=posts,
            reviews=reviews, is_following=is_following
        )

    @app.route("/farm/edit", methods=["GET", "POST"])
    @login_required
    @farmer_required
    def edit_farm():
        farm = current_user.farm
        if request.method == "POST":
            farm.farm_name = request.form.get("farm_name", farm.farm_name)
            farm.village = request.form.get("village", farm.village)
            farm.district = request.form.get("district", farm.district)
            farm.pincode = request.form.get("pincode", farm.pincode)
            farm.description = request.form.get("description", farm.description)
            farm.experience_years = request.form.get("experience_years", 0, type=int)
            farm.organic_status = request.form.get("organic_status", farm.organic_status)
            farm.farm_area = request.form.get("farm_area", farm.farm_area)
            farm.latitude = request.form.get("latitude", type=float)
            farm.longitude = request.form.get("longitude", type=float)
            farm.map_url = request.form.get("map_url", farm.map_url)

            logo_file = request.files.get("logo")
            cover_file = request.files.get("cover_photo")
            logo_path = save_image(logo_file, "farms")
            cover_path = save_image(cover_file, "farms")
            if logo_path:
                farm.logo = logo_path
            if cover_path:
                farm.cover_photo = cover_path

            db.session.commit()
            flash("Farm profile updated.", "success")
            return redirect(url_for("farm_profile", farm_id=farm.id))
        return render_template("edit_farm.html", farm=farm)

    @app.route("/farm/<int:farm_id>/follow", methods=["POST"])
    @login_required
    def toggle_follow(farm_id):
        farm = Farm.query.get_or_404(farm_id)
        existing = Follow.query.filter_by(farm_id=farm.id, customer_id=current_user.id).first()
        if existing:
            db.session.delete(existing)
            following = False
        else:
            db.session.add(Follow(farm_id=farm.id, customer_id=current_user.id))
            notify(farm.owner_id, "New Follower", f"{current_user.name} started following your farm.", "follow")
            following = True
        db.session.commit()
        return jsonify({"following": following, "follower_count": farm.follower_count})

    @app.route("/farm/<int:farm_id>/review", methods=["POST"])
    @login_required
    def add_review(farm_id):
        farm = Farm.query.get_or_404(farm_id)
        rating = request.form.get("rating", 5, type=int)
        text = request.form.get("review_text", "").strip()
        review = Review(farm_id=farm.id, customer_id=current_user.id, rating=rating, review_text=text)
        db.session.add(review)
        notify(farm.owner_id, "New Review", f"{current_user.name} left a {rating}-star review.", "review")
        db.session.commit()
        flash("Thanks for your review!", "success")
        return redirect(url_for("farm_profile", farm_id=farm.id))

    # ---------- PRODUCTS ----------
    @app.route("/products")
    def products():
        q = request.args.get("q", "").strip()
        category_id = request.args.get("category", type=int)
        organic_only = request.args.get("organic") == "1"

        query = Product.query.filter_by(is_available=True)
        if q:
            query = query.filter(Product.name.ilike(f"%{q}%"))
        if category_id:
            query = query.filter_by(category_id=category_id)
        if organic_only:
            query = query.filter_by(is_organic=True)

        product_list = query.order_by(Product.created_at.desc()).all()
        categories = Category.query.all()
        return render_template(
            "products.html", products=product_list, categories=categories,
            q=q, category_id=category_id, organic_only=organic_only
        )

    @app.route("/product/<int:product_id>")
    def product_detail(product_id):
        product = Product.query.get_or_404(product_id)
        related = Product.query.filter(
            Product.farm_id == product.farm_id, Product.id != product.id
        ).limit(4).all()
        return render_template("product_detail.html", product=product, related=related)

    @app.route("/farm/products/new", methods=["GET", "POST"])
    @login_required
    @farmer_required
    def new_product():
        categories = Category.query.all()
        if request.method == "POST":
            image_path = save_image(request.files.get("image"), "products")
            harvest = request.form.get("harvest_date")
            product = Product(
                farm_id=current_user.farm.id,
                category_id=request.form.get("category_id", type=int),
                name=request.form.get("name"),
                price=request.form.get("price", type=float),
                unit=request.form.get("unit", "kg"),
                quantity_available=request.form.get("quantity_available", type=float),
                harvest_date=date.fromisoformat(harvest) if harvest else None,
                description=request.form.get("description"),
                is_organic=request.form.get("is_organic") == "on",
                image=image_path or "default-product.jpg",
            )
            db.session.add(product)
            db.session.commit()
            flash("Product added.", "success")
            return redirect(url_for("farm_profile", farm_id=current_user.farm.id))
        return render_template("product_form.html", categories=categories, product=None)

    @app.route("/farm/products/<int:product_id>/edit", methods=["GET", "POST"])
    @login_required
    @farmer_required
    def edit_product(product_id):
        product = Product.query.get_or_404(product_id)
        if product.farm_id != current_user.farm.id:
            abort(403)
        categories = Category.query.all()
        if request.method == "POST":
            product.name = request.form.get("name", product.name)
            product.price = request.form.get("price", product.price, type=float)
            product.unit = request.form.get("unit", product.unit)
            product.quantity_available = request.form.get("quantity_available", product.quantity_available, type=float)
            product.description = request.form.get("description", product.description)
            product.category_id = request.form.get("category_id", type=int)
            product.is_organic = request.form.get("is_organic") == "on"
            product.is_available = request.form.get("is_available") == "on"
            image_path = save_image(request.files.get("image"), "products")
            if image_path:
                product.image = image_path
            db.session.commit()
            flash("Product updated.", "success")
            return redirect(url_for("farm_profile", farm_id=current_user.farm.id))
        return render_template("product_form.html", categories=categories, product=product)

    @app.route("/farm/products/<int:product_id>/delete", methods=["POST"])
    @login_required
    @farmer_required
    def delete_product(product_id):
        product = Product.query.get_or_404(product_id)
        if product.farm_id != current_user.farm.id:
            abort(403)
        db.session.delete(product)
        db.session.commit()
        flash("Product deleted.", "success")
        return redirect(url_for("farm_profile", farm_id=current_user.farm.id))

    # ---------- SOCIAL FEED ----------
    @app.route("/feed")
    def feed():
        posts = Post.query.order_by(Post.created_at.desc()).all()
        return render_template("feed.html", posts=posts)

    @app.route("/post/new", methods=["GET", "POST"])
    @login_required
    @farmer_required
    def new_post():
        if request.method == "POST":
            image_path = save_image(request.files.get("image"), "posts")
            post = Post(
                user_id=current_user.id,
                image=image_path,
                caption=request.form.get("caption", ""),
                location=request.form.get("location", ""),
            )
            db.session.add(post)
            db.session.commit()
            flash("Post published.", "success")
            return redirect(url_for("feed"))
        return render_template("post_form.html")

    @app.route("/post/<int:post_id>/like", methods=["POST"])
    @login_required
    def toggle_like(post_id):
        post = Post.query.get_or_404(post_id)
        existing = Like.query.filter_by(post_id=post.id, user_id=current_user.id).first()
        if existing:
            db.session.delete(existing)
            liked = False
        else:
            db.session.add(Like(post_id=post.id, user_id=current_user.id))
            liked = True
            if post.user_id != current_user.id:
                notify(post.user_id, "New Like", f"{current_user.name} liked your post.", "like")
        db.session.commit()
        return jsonify({"liked": liked, "like_count": post.like_count})

    @app.route("/post/<int:post_id>/comment", methods=["POST"])
    @login_required
    def add_comment(post_id):
        post = Post.query.get_or_404(post_id)
        text = request.form.get("text", "").strip()
        if text:
            comment = Comment(post_id=post.id, user_id=current_user.id, text=text)
            db.session.add(comment)
            if post.user_id != current_user.id:
                notify(post.user_id, "New Comment", f"{current_user.name} commented on your post.", "comment")
            db.session.commit()
        return redirect(url_for("feed"))

    # ---------- CHAT (basic) ----------
    @app.route("/messages")
    @login_required
    def inbox():
        sent = db.session.query(Message.receiver_id).filter_by(sender_id=current_user.id)
        received = db.session.query(Message.sender_id).filter_by(receiver_id=current_user.id)
        partner_ids = {r[0] for r in sent.all()} | {r[0] for r in received.all()}
        partners = User.query.filter(User.id.in_(partner_ids)).all() if partner_ids else []
        return render_template("inbox.html", partners=partners)

    @app.route("/messages/<int:user_id>", methods=["GET", "POST"])
    @login_required
    def conversation(user_id):
        partner = User.query.get_or_404(user_id)
        if request.method == "POST":
            body = request.form.get("body", "").strip()
            if body:
                msg = Message(sender_id=current_user.id, receiver_id=partner.id, body=body)
                db.session.add(msg)
                notify(partner.id, "New Message", f"{current_user.name} sent you a message.", "message")
                db.session.commit()
            return redirect(url_for("conversation", user_id=partner.id))

        Message.query.filter_by(sender_id=partner.id, receiver_id=current_user.id, is_read=False).update({"is_read": True})
        db.session.commit()

        thread = Message.query.filter(
            db.or_(
                db.and_(Message.sender_id == current_user.id, Message.receiver_id == partner.id),
                db.and_(Message.sender_id == partner.id, Message.receiver_id == current_user.id),
            )
        ).order_by(Message.created_at.asc()).all()
        return render_template("conversation.html", partner=partner, thread=thread)

    # ---------- NOTIFICATIONS ----------
    @app.route("/notifications")
    @login_required
    def notifications():
        items = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
        Notification.query.filter_by(user_id=current_user.id, seen=False).update({"seen": True})
        db.session.commit()
        return render_template("notifications.html", items=items)

    # ---------- DASHBOARD ----------
    @app.route("/dashboard")
    @login_required
    def dashboard():
        if current_user.is_farmer:
            farm = current_user.farm
            my_products = Product.query.filter_by(farm_id=farm.id).order_by(Product.created_at.desc()).all()
            stats = {
                "products": len(my_products),
                "posts": Post.query.filter_by(user_id=current_user.id).count(),
                "followers": Follow.query.filter_by(farm_id=farm.id).count(),
                "reviews": Review.query.filter_by(farm_id=farm.id).count(),
                "avg_rating": farm.avg_rating,
                "unread_messages": Message.query.filter_by(receiver_id=current_user.id, is_read=False).count(),
            }
            return render_template("dashboard_farmer.html", farm=farm, stats=stats, my_products=my_products)
        else:
            following = Follow.query.filter_by(customer_id=current_user.id).all()
            farms = [f.farm for f in following]
            reviews = Review.query.filter_by(customer_id=current_user.id).all()
            return render_template("dashboard_customer.html", farms=farms, reviews=reviews)

    # ---------- ADMIN ----------
    @app.route("/admin")
    @login_required
    def admin_dashboard():
        if not current_user.is_admin:
            abort(403)
        stats = {
            "farmers": User.query.filter_by(role="farmer").count(),
            "customers": User.query.filter_by(role="customer").count(),
            "products": Product.query.count(),
            "posts": Post.query.count(),
            "categories": Category.query.count(),
            "reviews": Review.query.count(),
        }
        district_counts = db.session.query(Farm.district, db.func.count(Farm.id)).group_by(Farm.district).all()
        return render_template("admin_dashboard.html", stats=stats, district_counts=district_counts)

    # ---------- AI FEATURES ----------
    @app.route("/api/chatbot", methods=["POST"])
    def api_chatbot():
        message = request.json.get("message", "") if request.is_json else request.form.get("message", "")
        reply = chatbot_reply(message)
        return jsonify({"reply": reply})

    @app.route("/api/suggest-product-description", methods=["POST"])
    def api_suggest_product_description():
        data = request.get_json(silent=True) or {}
        name = data.get("name", "")
        category_name = data.get("category_name", "")
        is_organic = bool(data.get("is_organic"))
        text = suggest_product_description(name, category_name, is_organic)
        return jsonify({"description": text})

    @app.route("/api/suggest-post-caption", methods=["POST"])
    def api_suggest_post_caption():
        data = request.get_json(silent=True) or {}
        location = data.get("location", "")
        text = suggest_post_caption(location)
        return jsonify({"caption": text})

    # ---------- ERROR HANDLERS ----------
    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html"), 403

    return app


app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=5000)
