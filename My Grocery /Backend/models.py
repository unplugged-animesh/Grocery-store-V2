from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    admin = db.Column(db.Boolean,default=False)
    user_cart = db.relationship(
        "Cart", backref="User", lazy=True, cascade='all, delete-orphan')


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    products = db.relationship(
        "Product", backref="Category", lazy=True, cascade='all, delete-orphan')


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit = db.Column(db.String(100), nullable=False)
    mf_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    sold_quantity = db.Column(db.Integer, default=0, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey(
        "category.id"), nullable=False)


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    cart_count = db.Column(db.Integer, default=0, nullable=False)
    items = db.relationship("CartItem", backref="Cart",
                            cascade='all, delete-orphan')


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    quantity = db.Column(db.Integer, default=0, nullable=False)
    cart_id = db.Column(db.Integer, db.ForeignKey("cart.id"), nullable=False)
    cartitem_product_id = db.Column(
        db.Integer, db.ForeignKey("product.id"), nullable=False)
