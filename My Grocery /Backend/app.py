from flask import Flask, jsonify, request, session, url_for, send_file, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import and_

import os
import csv
import time
from datetime import date, datetime

from flask_login import UserMixin
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from flask_jwt_extended import create_access_token, unset_jwt_cookies
from flask_jwt_extended import jwt_required, get_jwt_identity, JWTManager
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
from flask_cors import CORS
from flask_caching import Cache
import bcrypt

from celery import Celery
from celery.schedules import crontab

import smtplib
from jinja2 import Template
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
CORS(app, origins='*')

curr_path = os.path.dirname(__file__)
db_path = os.path.abspath(os.path.join(curr_path, os.path.relpath('./instance/mygrocery.sqlite3')))
# db_path = os.path.abspath(os.path.join(curr_path, os.path.relpath('./../instance/mygrocery.sqlite3')))
print(db_path)
app.config['SECRET_KEY'] = 'East'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['CACHE_TYPE'] = "RedisCache"
app.config['REDIS_URL'] = "redis://localhost:6379"
app.config['CACHE_REDIS_URL'] = "redis://localhost:6379/0"
app.config['CACHE_DEFAULT_TIMEOUT'] = 120
app.config['CACHE_KEY_PREFIX'] = "mygrocery"

app.config["CELERY_BROKER_URL"]="redis://localhost:6379/1"
app.config["CELERY_RESULT_BACKEND"]="redis://localhost:6379/2"
app.config["ENABLE_UTC"]=False

app.config["SMTP_SERVER_HOST"] = "localhost"
app.config["SMTP_SERVER_PORT"] = 1025
app.config["SENDER_ADDRESS"] = "noreply@grocerstore.com"
app.config["SENDER_PASSWORD"] = ""

jwt = JWTManager(app)
db = SQLAlchemy(app)
cache = Cache()
cache.init_app(app)

#-----------------------Mail-Schedulers--------------------#

def send_mail(to_address, message, subject):
    msg = MIMEMultipart()
    msg["From"] = app.config["SENDER_ADDRESS"]
    msg["To"] = to_address
    msg["Subject"] = subject
    
    msg.attach(MIMEText(message, "html"))
    
    s = smtplib.SMTP(host=app.config["SMTP_SERVER_HOST"], port=app.config["SMTP_SERVER_PORT"])
    s.login(msg["From"], app.config["SENDER_PASSWORD"])
    s.send_message(msg)
    s.quit()
    return True
            
        
#----------------------------------------------------------#



#------------------------Celery----------------------------#
celery = Celery("Application")
class ContextTask(celery.Task):
    def __call__(self, *args, **kwargs):
        with app.app_context():
            return self.run(*args, **kwargs)

celery.conf.update(
    broker_url=app.config["CELERY_BROKER_URL"],
    result_backend=app.config["CELERY_RESULT_BACKEND"],
    enable_utc=app.config["ENABLE_UTC"],
)

celery.Task = ContextTask

#-----------CELERY Tasks----------#

@celery.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    dom, hour, minute = 1, 17, 30
    sender.add_periodic_task(crontab(hour=hour, minute=minute), remind.s(), name="Daily reminder")
    sender.add_periodic_task(
        crontab(dom=dom, hour=hour, minute=minute),
        generate_monthly_report.s()
    )  

@celery.task()
def remind():
    today = date.today()
    user_list = User.query.all()
    for user in user_list:
        if user.admin==2:
            cart = Cart.query.filter_by(user_id=user.id).first()
            if not cart:
                continue
            if datetime.strptime(cart.last_purchased, "%d-%m-%Y").date() != today:
                msg = None
                with open("./templates/reminder.html", "r") as reminder_template:
                    template = Template(reminder_template.read())
                    msg = template.render(data={"username": user.username})
                send_mail(user.email, msg, "Daily reminder")

@celery.task
def generate_monthly_report():
    current_month = datetime.now().strftime('%B')
    current_year = datetime.now().year

    users = User.query.all()
    for user in users:
        if user.admin != 2:
            continue
        cart = Cart.query.filter_by(user_id=user.id).first()
        if not cart:
            continue
        total_orders = cart.cart_count
        total_expenditure =cart.expenditure

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Your Monthly Activity</title>
        </head>
        <body>
            <h1> Your Monthly Activity - {current_month} {current_year}</h1>
            <p>Hello {user.username},</p>
            <p>Here's your Monthly Shopping activity for the month of {current_month} {current_year}:</p>
            <ul>
                <li>Total Expenditure: ₹{total_expenditure}</li>
                <li>Total Orders: {total_orders}</li>
            </ul>
            <p>We appreciate your choice in our services. Happy shopping and have a great time! </p>
            <p>Best regards,</p>
            <p>My Grocery</p>
        </body>
        </html>
        """
        send_mail(user.email, html_content, f"{user.username}'s monthly report")

@celery.task()
def export_csv_task():
    products = Product.query.all()  
    filename = "./product_details.csv"

    with open(filename, "w", newline="") as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(["Product Name", "Stock Remaining", "Price", "Units Sold"])

        for product in products:
            csv_writer.writerow([product.name, product.quantity, product.price, product.sold_quantity])
    
            

    return {"message": "file exported", "file_path": filename}

#----------------------------------------------------------#

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(), unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    admin = db.Column(db.Integer, default=2) # 0: admin, 1: manager, 2: user
    user_cart = db.relationship(
        "Cart", backref="User", lazy=True, cascade='all, delete-orphan')

        
    def  __repr__(self) -> str:
        return f"<email {self.email}>"

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
    created_user_id=db.Column(db.Integer, db.ForeignKey("user.id"))


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    cart_count = db.Column(db.Integer, default=0, nullable=False)
    expenditure=db.Column(db.Integer,default=0)
    last_purchased = db.Column(db.String(10), nullable=True)
    items = db.relationship("CartItem", backref="Cart",
                            cascade='all, delete-orphan')

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    quantity = db.Column(db.Integer, default=0, nullable=False)
    cart_id = db.Column(db.Integer, db.ForeignKey("cart.id"), nullable=False)
    cartitem_product_id = db.Column(
        db.Integer, db.ForeignKey("product.id"), nullable=False)

class KeyList(db.Model):
    role = db.Column(db.String(50), primary_key=True, unique=True)
    key = db.Column(db.String, unique=True)


with app.app_context():
    db.create_all()
    users = [(user.admin==0) for user in User.query.all()]
    if True not in users:
        app_admin = User(username="animesh", email="as12@mail.com", password=generate_password_hash('kanu'), admin=0) 
        admin_key = KeyList(role="admin", key=generate_password_hash("admin"))
        manager_key = KeyList(role="manager", key=generate_password_hash("manager"))
        db.session.add(app_admin)
        db.session.add(admin_key)
        db.session.add(manager_key)
        db.session.commit()
        


@app.route('/', methods=['GET'])
def home():
    return jsonify({'message:ok.'}),200


@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
        return jsonify({'error': 'Username or email already exists. Please choose a different username or email.'}), 400

    hashed_password = generate_password_hash(password)
    user = User(username=username, email=email, password=hashed_password)
    db.session.add(user)
    db.session.commit()

    return jsonify({'message': 'Account created successfully!'}), 200



@app.route('/login_page', methods=['POST'])
def login():
    username_or_email = request.json.get('username')
    password = request.json.get('password')

    user = User.query.filter(
        or_(User.username == username_or_email, User.email == username_or_email)).first()
    
    if not user or not check_password_hash(user.password, password):
        return jsonify({'error': 'Invalid Username or Password'}), 401
    
    if user.admin != 2:
        return jsonify({'error': 'No such user with customer role'}), 401

    access_token = create_access_token(
        identity=user.id, expires_delta=timedelta(days=1))
    user_info = {
        'user_id': user.id,
        'username': user.username,
    }

    return jsonify({'access_token': access_token, 'user': user_info}), 200


@app.route('/logout_page', methods=['GET'])
def logout():
    cache.clear()
    resp = jsonify({'message': 'Logged out successfully'})
    unset_jwt_cookies(resp)
    return resp, 200


@app.route('/store_signup', methods=['POST'])
def store_signup():
    data = request.json  


    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    store_manager_key = data.get('key')

    
    if not check_password_hash(KeyList.query.filter_by(role="manager").first().key, store_manager_key):
        return jsonify({'error': 'Invalid key.'}), 401

    try:

        hashed_password = generate_password_hash(password)
        user = User(username=username, email=email,
                    password=hashed_password, admin=3)

        db.session.add(user)
        db.session.commit()
        return jsonify({'message': 'Signup successful!'}), 200

    except IntegrityError:

        db.session.rollback()
        return jsonify({'error': 'Username or email already exists.'}), 400

    except Exception as e:

        db.session.rollback()
        return jsonify({'error': 'An error occurred during signup. Please try again later.'}), 500


@app.route('/store_login', methods=['POST'])
def store_login():
    username_or_email = request.json.get('username')
    password = request.json.get('password')
    store_manager_key = request.json.get('key')
    
    user = User.query.filter(
        or_(User.username == username_or_email, User.email == username_or_email)).first()
    
    if not user or not check_password_hash(user.password, password):
        return jsonify({'error': 'Invalid Username or Password'}), 401
    
    if user.admin == 1:
        if not check_password_hash(KeyList.query.filter_by(role="manager").first().key, store_manager_key):
            return jsonify({'error': 'Invalid key'}), 401
    elif user.admin == 0:
        if not check_password_hash(KeyList.query.filter_by(role="admin").first().key, store_manager_key):
            return jsonify({'error': 'Invalid key'}), 401
    else:
        return jsonify({'error': 'No user with this role.'}), 401  
    
    access_token = create_access_token(identity=user.id, expires_delta=timedelta(days=1))
    user_info = {
        'user_id': user.id,
        'username': user.username,
    }

    return jsonify({'access_token': access_token, 'user': user_info,'user_role':user.admin}), 200


@app.route('/api/admin/approval_managers', methods=['GET', 'POST'])
@jwt_required()
def pending_managers():

    if request.method == 'POST':
        data = request.get_json()
        manager_id = data.get('manager_id')
        status = data.get('status')

        if not manager_id or status not in ['approve', 'reject']:
            return jsonify({'message': 'Invalid request data'}), 400

        user = User.query.get(manager_id)

        if not user:
            return jsonify({'message': 'User not found'}), 404

        if status == 'approve':
            user.admin = 1
        elif status == 'reject':
            db.session.delete(user)

        db.session.commit()

        return jsonify({'message': 'Manager action successfully processed'}), 200
    pending_managers = User.query.filter_by(
         admin=3).all()

    pending_managers_data = []

    for manager in pending_managers:
        manager_data = {
            'id': manager.id,
            'email': manager.email,
            'username': manager.username,
        }
        pending_managers_data.append(manager_data)

    return jsonify(pending_managers_data)

@app.route('/admin_dashboard/<int:curr_login_id>', methods=['GET'])
@jwt_required()  
def admin_dashboard(curr_login_id):

    current_user_id = get_jwt_identity()

    if current_user_id != curr_login_id:
        return jsonify({'error': 'You are not authorized to access this resource.'}), 403


    user = User.query.filter_by(id=current_user_id)
    if not user or not user.admin:
        return jsonify({'error': 'You are not authorized to access the admin dashboard.'}), 403

    if user.admin != 0:
        return jsonify({'error':'User not admin'}), 401

    categories = Category.query.all()
    data = {'curr_login_id': curr_login_id,
            'categories': [{'id': category.id, 'name': category.name}
                           for category in categories]}
    return jsonify(data)


@app.route('/customer_dashboard/<int:curr_login_id>', methods=['POST'])
@jwt_required()
def customer_dashboard(curr_login_id):
    if request.method == 'POST':
        current_user_id = get_jwt_identity()
        
        user = User.query.filter_by(id=curr_login_id).first()
        if not user:
            return jsonify({'error': 'User not found for the given identifier.'}), 404
        if user.admin != 2:
            return jsonify({'error':'User not customer'}), 401
        user_cart = Cart.query.filter_by(user_id=curr_login_id).first()
        if not user_cart:
            return jsonify({'message': 'Cart not found for the given user identifier.'}), 200
        categories = Category.query.all()
        data = {'name': user.username,
                'dashboardData': {'curr_login_id': curr_login_id,
                                    'cart': {category.name: [
                                        {
                                            'quantity': 0 if cart_item is None else cart_item.quantity,
                                            'name': product.name,
                                            'price': product.price,
                                            'unit': product.unit,
                                            'mf_date': product.mf_date,
                                            'expiry_date': product.expiry_date
                                        }
                                        for product in category.products
                                        for cart_item in [CartItem.query.filter_by(cart_id=user_cart.id, cartitem_product_id=product.id).first()]
                                    ] for category in categories}}}
        return jsonify(data)

@app.route('/api/customer/<int:curr_login_id>/cart', methods=['GET'])
def get_cart_data(curr_login_id):
    try:

        cart = Cart.query.filter_by(user_id=curr_login_id).first()

        if cart:
            cart_items = CartItem.query.filter_by(cart_id=cart.id).all()

            cartitem_data = []
            amount = 0

            for item in cart_items:
                product = Product.query.get(item.cartitem_product_id)
                subtotal = product.price * min(item.quantity, product.quantity)
                amount += subtotal

                cartitem_data.append({
                    "item_id": item.id,
                    "product": {
                        "id": product.id,
                        "name": product.name,
                        "price": product.price,
                        "quantity": product.quantity,
                        "subtotal": subtotal
                    },
                    "quantity": item.quantity
                })

            response_data = {
                "isEmpty": False,
                "cartitem_data": cartitem_data,
                "amount": amount,
                "curr_login_id": curr_login_id
            }

            return jsonify(response_data), 200
        else:
            response_data = {
                "isEmpty": True,
                "cartitem_data": [],
                "amount": 0,
                "curr_login_id": curr_login_id
            }
            return jsonify(response_data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/customer/<int:user_id>/dashboard', methods=['GET'])
@jwt_required
def get_user_dashboard_data(user_id):
    try:
        user = User.query.get(user_id)
        if user is None:
            return jsonify({'message': 'User not found.'}), 404

        cart = user.cart
        category_data = [
            {
                'id': category.id,
                'name': category.name,
                'products': [
                    {
                        'id': product.id,
                        'name': product.name,
                        'expiry_date': product.expiry_date.strftime('%Y-%m-%d'),
                        'mf_date': product.manufacture_date.strftime('%Y-%m-%d'),
                        'price': product.price,
                        'unit': product.unit,
                        'quantity': product.quantity,
                    }
                    for product in category.products
                ],
            }
            for category in cart.categories
        ]

        user_data = {
            'name': user.name,
            'cart': category_data,
        }

        return jsonify(user_data), 200

    except Exception as e:
        return jsonify({'message': 'Error fetching user data.', 'error': str(e)}), 500


@app.route('/api/categories', methods=['GET'])
@cache.cached()
def get_categories():
    time.sleep(1)
    try:
        categories = Category.query.options(
            joinedload(Category.products)).all()

        category_data = [
            {
                'id': category.id,
                'name': category.name,
                'products': [
                    {
                        'id': product.id,
                        'name': product.name,
                        'expiry_date': product.expiry_date.strftime('%Y-%m-%d'),
                        'mf_date': product.mf_date.strftime('%Y-%m-%d'),
                        'price': product.price,
                        'unit': product.unit,
                        'quantity': product.quantity,

                    }
                    for product in category.products
                ],
            }
            for category in categories
        ]

        return jsonify(category_data), 200
    except Exception as e:
        return jsonify({'message': 'Error fetching categories.', 'error': str(e)}), 500


@app.route("/store_manager/export", methods=["POST"])
def export_csv():
    result = export_csv_task()
    print(result)
    return jsonify({"message": "file exported"})

@app.route('/api/check_admin/<int:curr_login_id>', methods=['GET'])
def check_user_admin(curr_login_id):
    user = User.query.get(curr_login_id)
    if user is None:
        return jsonify({'message': 'User not found.'}), 404

    if user.admin == 1:
        return jsonify({'admin': True}), 200
    else:
        return jsonify({'admin': False}), 200


@app.route('/admin/<int:curr_login_id>/create_category', methods=['POST'])
def create_category(curr_login_id):
    cache.clear()
    if not check_user_admin(curr_login_id):
        return jsonify({'message': 'You are not authorized to access this page.'}), 403

    if request.method == 'POST':
        name = request.json.get('name')
        if not name:
            return jsonify({'message': 'Category name is required.'}), 400

        try:
            category = Category(name=name)
            db.session.add(category)
            db.session.commit()
            return jsonify({'message': 'Category created successfully.'}), 200
        except IntegrityError:
            db.session.rollback()
            return jsonify({'message': 'Category with the given name already exists.'}), 409

    return jsonify({'message': 'Method not allowed.'}), 405


@app.route('/api/category/<category_id>', methods=['GET', 'POST'])
def edit_category(category_id):
    cache.clear()
    category = Category.query.get_or_404(category_id)

    if request.method == 'GET':
        return jsonify({
            'category': {
                'id': category.id,
                'name': category.name
            }
        })
    elif request.method == 'POST':
        data = request.get_json()
        new_name = data.get('name')

        try:
            category.name = new_name
            db.session.commit()
            return jsonify({'message': 'Category updated successfully.'}), 200
        except IntegrityError:
            db.session.rollback()
            return jsonify({'error': 'Category with the given name already exists.'}), 400


@app.route('/api/admin/remove_categ/<category_id>', methods=['POST'])
def remove_category(category_id):
    cache.clear()
    category = Category.query.get_or_404(category_id)

    try:
        db.session.delete(category)
        db.session.commit()
        return jsonify({'success': True}), 200
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({'error': 'Failed to remove category. Please try again.'}), 500

@app.route('/api/store_manager/categories', methods=['GET'])
@cache.cached()
def give_cat():
    time.sleep(1)
    categories = Category.query.all()
    categories_data = [{'id': category.id, 'name': category.name}
                        for category in categories]
    return jsonify({'categories': categories_data})

@cache.cached()
def get_user_role():
    time.sleep(1)
    identity = get_jwt_identity()
    return identity

@app.route('/api/store_manager/<int:curr_login_id>/create_product', methods=['POST'])
@jwt_required()
def create_product(curr_login_id):
    cache.clear()
    user_id=get_user_role()

    
    new_product_data = request.json
    expiry_date = datetime.strptime(
    new_product_data.get('expiry_date'), '%Y-%m-%d').date()
    mf_date = datetime.strptime(new_product_data.get('mf_date'), '%Y-%m-%d').date()

    new_product_name = new_product_data.get('name', '').lower()


    existing_product = Product.query.filter(and_(db.func.lower(Product.name) == new_product_name, Product.created_user_id == user_id)).first()
    if existing_product:
            return jsonify({"error": "Product with the same name already exists."}), 409

    new_product = Product(
            name=new_product_data.get('name'),
            category_id=new_product_data.get('category_id'),
            expiry_date=expiry_date,
            mf_date=mf_date,
            price=new_product_data.get('price'),
            unit=new_product_data.get('unit'),
            quantity=new_product_data.get('quantity'),
            created_user_id=user_id,
        )

    db.session.add(new_product)
    db.session.commit()

    return jsonify({"message": "Product added successfully!"}), 200
 

@app.route('/api/store_manager/get_product/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = Product.query.get_or_404(product_id)

    return jsonify({
        'id': product.id,
        'name': product.name,
        'price': product.price,
        'unit': product.unit,
        'quantity': product.quantity,
        'mf_date': product.mf_date,
        'expiry_date': product.expiry_date,
        'category_id': product.category_id,
    }), 200

@app.route('/api/store_manager/update_product/<int:product_id>', methods=['POST'])
def edit_product(product_id):
    cache.clear()


    data = request.json
    product = Product.query.get_or_404(product_id)
    try:
        product.name = data['name']
        product.price = data['price']
        product.unit = data['unit']
        product.quantity = data['quantity']
        product.mf_date = datetime.strptime(data['mf_date'], '%Y-%m-%d').date()
        product.expiry_date = datetime.strptime(data['expiry_date'], '%Y-%m-%d').date()
        product.category_id = data['category_id']
        db.session.commit()
        return jsonify({'success': True}), 200
    except:
        db.session.rollback()
        return jsonify({'error': 'Failed to update product. Please try again.'}), 500

@app.route('/api/store_manager/delete_product/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    cache.clear()

    product = Product.query.get_or_404(product_id)
    db.session.delete(product)

    try:
        db.session.commit()
        return jsonify({'success': True}), 200
    except:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete product. Please try again.'}), 500


@app.route('/api/customer/<int:curr_login_id>/cart', methods=['POST'])
def cart(curr_login_id):
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        quantity = data.get('quantity')

        if not product_id or not quantity:
            return jsonify({'error': 'Product ID and quantity must be provided.'}), 400

        product = Product.query.get(product_id)
        if not product:
            return jsonify({'error': 'Product not found.'}), 404

        if quantity > product.quantity:
            return jsonify({'error': 'Requested quantity exceeds available stock.'}), 400


        cart = Cart.query.filter_by(user_id=curr_login_id).first()
        if cart is None:
            cart = Cart(user_id=curr_login_id)
            db.session.add(cart)
            db.session.commit()


        cart_item = CartItem.query.filter_by(
            cart_id=cart.id, cartitem_product_id=product_id).first()
        if cart_item:
            cart_item.quantity += quantity
        else:
            cart_item = CartItem(
                cart_id=cart.id, cartitem_product_id=product_id, quantity=quantity)
            db.session.add(cart_item)

        db.session.commit()

        return jsonify({'success': 'Product added to the cart successfully.'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/update_cart_quantity/<int:curr_login_id>/<int:product_id>', methods=['POST'])
def update_cart_quantity(curr_login_id, product_id):
    try:
        data = request.get_json()
        quantity = data.get('quantity')

        if not quantity:
            return jsonify({'error': 'Quantity must be provided.'}), 400

        cart = Cart.query.filter_by(user_id=curr_login_id).first()
        if not cart:
            return jsonify({'error': 'Cart not found for the current customer.'}), 404

        cart_item = CartItem.query.filter_by(cart_id=cart.id, cartitem_product_id=product_id).first()
        if not cart_item:
            return jsonify({'error': 'Product not found in the cart.'}), 404

        product = Product.query.get(product_id)
        if not product:
            return jsonify({'error': 'Product not found.'}), 404

        if quantity > product.quantity:
            return jsonify({'error': 'Requested quantity exceeds available stock.'}), 400

        cart_item.quantity = quantity
        db.session.commit()

        return jsonify({'success': 'Cart quantity updated successfully.'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/api/remove_from_cart/<int:curr_login_id>/cart/<int:product_id>/remove-cartitem', methods=['POST'])
def remove_from_cart(curr_login_id, product_id):
    cache.clear()
    try:
        print(f"Trying to remove product_id: {product_id} from the cart of user_id: {curr_login_id}")


        cart = Cart.query.filter_by(user_id=curr_login_id).first()
        if not cart:
            return jsonify({'error': 'Cart not found for the current customer.'}), 404

        cart_item = CartItem.query.filter_by(cart_id=cart.id, cartitem_product_id=product_id).first()
        if not cart_item:
            return jsonify({'error': 'Product not found in cart.'}), 404

        db.session.delete(cart_item)
        db.session.commit()

        print(f"Product_id: {product_id} removed from the cart of user_id: {curr_login_id}")

        return jsonify({'message': 'Product removed from cart and quantity added back.'}), 200

    except Exception as e:
        print(f"Error removing from cart: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/customer/<int:curr_login_id>/checkout', methods=['GET', 'POST'])
def checkout(curr_login_id):
    if request.method == 'GET':
        cart = Cart.query.filter_by(user_id=curr_login_id).first()
        cartitem_pdt = []
        total_amount = 0
        

        for item in cart.items:
            product = Product.query.filter_by(id=item.cartitem_product_id).first()
            if product and product.quantity > 0:
                quantity_to_buy = min(item.quantity, product.quantity)
                cartitem_pdt.append(({"id": item.id, "quantity":item.quantity}, {"name":product.name, "price":product.price, "quantity":quantity_to_buy}))
                total_amount += product.price * quantity_to_buy

        cartitem_pdt = [(item, pdt) for item, pdt in cartitem_pdt if pdt]

        data = {
            'cartitem_pdt': cartitem_pdt,
            'amount': total_amount,
            'user_id': curr_login_id,
        }
        return jsonify(data), 200
    else:
        cart = Cart.query.filter_by(user_id=curr_login_id).first()
        total_amount = 0
        for item in cart.items:
            product = Product.query.filter_by(id=item.cartitem_product_id).first()
            if product and product.quantity > 0:
                quantity_to_buy = min(item.quantity, product.quantity)
                total_amount += product.price * quantity_to_buy

        cart = Cart.query.filter_by(user_id=curr_login_id).first()
        if not cart:
            return jsonify({'error': 'Cart not found for the current customer.'}), 404
        data = request.get_json()
        for item_pdt in data:
            item = item_pdt["item"]
            pdt = item_pdt["product"]
            orig_pdt = Product.query.filter_by(name = pdt["name"]).first()
            orig_pdt.quantity -= pdt["quantity"]
            orig_pdt.sold_quantity += pdt["quantity"]
            cart.cart_count +=1
            db.session.add(orig_pdt)
            db.session.commit()
            remove_from_cart(curr_login_id, orig_pdt.id)
        cart.last_purchased = date.today().strftime("%d-%m-%Y")
        cart.expenditure +=total_amount
        db.session.add(cart)
        db.session.commit()
        return jsonify({'message':'done'}), 200

@app.route('/customer/<int:curr_login_id>/search', methods=['GET', 'POST'])
def search(curr_login_id):
    if request.method == 'POST':
        search_query = request.args.get('search')
        if not search_query:
            return jsonify({'error': 'Search query is empty'}), 400

        products = Product.query.filter(
            Product.name.ilike(f'%{search_query}%')
        ).all()

        categories = Category.query.filter(
            Category.name.ilike(f'%{search_query}%')
        ).all()

        products_data = [{'id': product.id, 'name': product.name,
                          'price': product.price,'quantity':product.quantity,'unit':product.unit,'mf_date':product.mf_date,'expiry_date':product.expiry_date} for product in products]
        categories_data = [{'id': category.id, 'name': category.name, 'products': [{'id': product.id, 'name': product.name,
                          'price': product.price,'quantity':product.quantity,'unit':product.unit,'mf_date':product.mf_date,'expiry_date':product.expiry_date} for product in Product.query.filter_by(category_id=category.id).all()]}
                           for category in categories]

        data = {
            'curr_login_id': curr_login_id,
            'search_query': search_query,
            'products': products_data,
            'categories': categories_data
        }
        return jsonify(data), 200

    return jsonify({'error': 'Method not allowed'}), 405


if __name__ == '__main__':
    app.run(debug=True, port=8000)
