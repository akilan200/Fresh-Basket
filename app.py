from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import boto3
import mysql.connector.pooling

app = Flask(__name__)

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
        'database': 'fbdb',
        'port': 3306,
        'pool_size': 10,
        'pool_name': 'primary_pool'
    },
    'replica': {
        'host': 'fbdb.c9ouwkeoegkz.us-east-1.rds.amazonaws.com',
        'user': 'admin',
        'password': 'qwerty1234',
        'database': 'fbdb',
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
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://admin:fbdb.c9ouwkeoegkz.us-east-1.rds.amazonaws.com:3306/fbdb'


app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'

# Initialize SQLAlchemy
db = SQLAlchemy(app)

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

# Database failover
def switch_to_replica():
    global current_pool
    try:
        current_pool = connection_pools['replica']
        return {'status': 'switched_to_replica'}
    except Exception as e:
        return {'error': str(e)}

# Database Models
class User(db.Model):
    __tablename__ = 'users'
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
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date_ordered = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')
    total_amount = db.Column(db.Float, nullable=False)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/shop')
def shop():
    return render_template('shop.html')

@app.route('/cart')
def cart():
    return render_template('cart.html')

@app.route('/items')
def items():
    return render_template('items.html')

@app.route('/user_dashboard')
def user_dashboard():
    return render_template('user_dashboard.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html')   

# Routes
@app.route('/api/health')
def health_check():
    return jsonify(check_system_health())

@app.route('/api/scaling/trigger', methods=['POST'])
def trigger_scaling():
    return jsonify(trigger_auto_scaling())

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        new_user = User(name=name, email=email, password=hashed_password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'error')
    
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

@app.route('/products')
def products():
    try:
        conn = connection_pools['primary'].get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('products.html', products=products)
    except Exception as e:
        flash('Error fetching products', 'error')
        return redirect(url_for('home'))

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name')
            price = float(request.form.get('price', 0))
            description = request.form.get('description')
            category = request.form.get('category')
            stock = int(request.form.get('stock', 0))
            image_url = request.form.get('image_url')

            # Print debug information
            print(f"Adding product: {name}, {price}, {category}")

            # Create product using direct SQL
            conn = connection_pools['primary'].get_connection()
            cursor = conn.cursor()
            
            insert_query = """
                INSERT INTO products (name, price, description, category, stock, image_url)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (name, price, description, category, stock, image_url))
            conn.commit()
            
            cursor.close()
            conn.close()

            flash('Product added successfully!', 'success')
            return redirect(url_for('products'))
            
        except Exception as e:
            print(f"Error adding product: {str(e)}")
            flash(f'Error adding product: {str(e)}', 'error')
            return redirect(url_for('add_product'))

    return render_template('add_product.html')

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

@app.route('/view_products')
def view_products():
    try:
        conn = connection_pools['primary'].get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({'products': products})
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
