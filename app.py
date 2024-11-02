from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import boto3
import mysql.connector.pooling

app = Flask(_name_)

# AWS Configuration
AWS_REGION = 'us-east-1'
AWS_ACCESS_KEY = 'your-access-key'
AWS_SECRET_KEY = 'your-secret-key'

# Initialize AWS services
ec2_client = boto3.client('ec2', region_name=AWS_REGION)
rds_client = boto3.client('rds', region_name=AWS_REGION)
iam_client = boto3.client('iam', region_name=AWS_REGION)

# RDS Configuration for multiple regions
db_configs = {
    'primary': {
        'host': 'fbdb.c9ouwkeoegkz.us-east-1.rds.amazonaws.com',
        'user': 'admin',
        'password': 'qwerty1234',
        'database': 'fresh',
        'port': 3306,
        'pool_size': 10,
        'pool_name': 'primary_pool'
    },
    'replica': {
        'host': 'fbdb.c9ouwkeoegkz.us-east-1.rds.amazonaws.com',
        'user': 'admin',
        'password': 'qwerty1234',
        'database': 'fresh',
        'port': 3306,
        'pool_size': 5,
        'pool_name': 'replica_pool'
    }
}

# Connection pools for different regions
connection_pools = {
    'primary': mysql.connector.pooling.MySQLConnectionPool(**db_configs['primary']),
    'replica': mysql.connector.pooling.MySQLConnectionPool(**db_configs['replica'])
}

# Flask SQLAlchemy Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://admin:qwerty1234@fbdb.c9ouwkeoegkz.us-east-1.rds.amazonaws.com:3306/fresh'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True  # Enables SQL query logging for debugging
app.secret_key = 'your_secret_key'

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Create tables if they don’t exist
with app.app_context():
    db.create_all()

# Health monitoring function
def check_system_health():
    try:
        # Check EC2 status
        ec2_status = ec2_client.describe_instance_status()
        
        # Check RDS status
        rds_status = rds_client.describe_db_instances()
        
        # Check security status
        iam_status = iam_client.get_account_summary()
        
        return {
            'ec2_health': 'healthy' if ec2_status else 'unhealthy',
            'rds_health': 'healthy' if rds_status else 'unhealthy',
            'security_status': 'secure' if iam_status else 'warning'
        }
    except Exception as e:
        return {'error': str(e)}

# Auto-scaling trigger
def trigger_auto_scaling():
    try:
        response = ec2_client.describe_auto_scaling_groups()
        # Implement auto-scaling logic
        return {'status': 'success'}
    except Exception as e:
        return {'error': str(e)}

# Database Models
class User(db.Model):
    _tablename_ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    mobile = db.Column(db.String(20))
    address = db.Column(db.String(200))
    role = db.Column(db.String(20), default='user')
    orders = db.relationship('Order', backref='user', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    stock = db.Column(db.Integer, default=0)
    image_url = db.Column(db.String(200))

class Order(db.Model):
    _tablename_ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date_ordered = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')
    total_amount = db.Column(db.Float, nullable=False)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if email already exists
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return redirect(url_for('register'))
        
        # Hash the password
        hashed_password = generate_password_hash(password)
        new_user = User(name=name, email=email, password=hashed_password)

        # Try to add user to the database
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()  # Rollback in case of error
            print(f"Error committing to database: {str(e)}")  # Debugging print
            flash('Registration failed. Please try again.', 'error')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['user_role'] = user.role
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('home'))

# Initialize database
def init_db():
    try:
        conn = connection_pools['primary'].get_connection()
        cursor = conn.cursor()

        # Create products table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                price FLOAT NOT NULL,
                description TEXT,
                category VARCHAR(50),
                stock INT DEFAULT 0,
                image_url VARCHAR(200)
            )
        """)

        # Create orders table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                date_ordered DATETIME DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(20) DEFAULT 'pending',
                total_amount FLOAT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Create order_items table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_id INT NOT NULL,
                product_id INT NOT NULL,
                quantity INT NOT NULL,
                price FLOAT NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)

        conn.commit()
        cursor.close()
        conn.close()
        print("Database initialized successfully")
        
    except Exception as e:
        print(f"Error initializing database: {str(e)}")

# Add this route to test database connection
@app.route('/test_db')
def test_db():
    try:
        # Test direct database query
        conn = connection_pools['primary'].get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({'tables': tables})
    except Exception as e:
        return jsonify({'error': str(e)})

if _name_ == '_main_':
    init_db()
    app.run(host='0.0.0.0', debug=True)
