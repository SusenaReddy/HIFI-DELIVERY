import logging
import sqlite3
import os
import threading
import time
from flask import Flask, render_template, jsonify, request, session

app = Flask(__name__)

# Secret key for sessions
app.secret_key = 'your_secret_key'

# Dynamically determine the database path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'instance', 'HIFIeats.db')

DEFAULT_CITY = "New York"  # Set the default city

# Initialize SQLite database
def init_db():
    try:
        if not os.path.exists(DATABASE):
            app.logger.info(f"Database file not found at {DATABASE}, creating new one.")
        
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        # Create orders table if it doesn't exist
        c.execute('''CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        items TEXT NOT NULL,
                        location TEXT NOT NULL,
                        total_price REAL NOT NULL,
                        in_range TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'Order Placed',
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()
        conn.close()
        app.logger.info("Database initialized successfully.")
    except Exception as e:
        app.logger.error(f"Error initializing the database: {e}")

def get_db():
    """Establish a connection to the database."""
    try:
        if not os.path.exists(DATABASE):
            raise FileNotFoundError(f"Database file not found at {DATABASE}")
        # Allow SQLite to work in a multi-threaded environment
        return sqlite3.connect(DATABASE, check_same_thread=False)
    except Exception as e:
        app.logger.error(f"Error connecting to database: {e}")
        raise e

@app.route('/')
def index():
    """Render the menu page."""
    return render_template('menu.html')

@app.route('/api/menu', methods=['GET'])
def fetch_menu():
    """Fetches menu items from the SQLite database with optional filters."""
    category = request.args.get('category')
    subcategory = request.args.get('subcategory')

    try:
        conn = get_db()
        cursor = conn.cursor()

        query = 'SELECT id, name, description, price, image_path, category, subcategory, discount FROM menu_items WHERE 1=1'
        params = []

        if category:
            query += ' AND category = ?'
            params.append(category)

        if subcategory:
            query += ' AND subcategory = ?'
            params.append(subcategory)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        menu_items = [dict(zip([column[0] for column in cursor.description], row)) for row in rows]
        conn.close()
        return jsonify(menu_items)
    except Exception as e:
        app.logger.error(f"Error fetching menu items: {e}")
        return jsonify({'error': 'Failed to fetch menu items'}), 500

@app.route('/api/cart', methods=['POST'])
def add_to_cart():
    """Add an item to the cart."""
    item_id = request.json.get('id')
    quantity = request.json.get('quantity', 1)

    if 'cart' not in session:
        session['cart'] = []

    cart = session['cart']
    item_exists = next((item for item in cart if item['id'] == item_id), None)

    if item_exists:
        item_exists['quantity'] += quantity
    else:
        cart.append({'id': item_id, 'quantity': quantity})

    session.modified = True
    return jsonify({'message': 'Item added to cart'}), 200

@app.route('/cart', methods=['GET'])
def cart():
    """Render the cart page."""
    return render_template('cart.html')

@app.route('/api/confirm_order', methods=['POST'])
def confirm_order():
    """Saves the order and initializes its tracking status."""
    data = request.json
    print(data)
    cart = data['cartItems']
    location = data['location']
    total_price = data['total']
    #total_price=100
    #confirmation = data.get('confirmation', False)
    confirmation=True
    print("confirm order")
    if not confirmation:
        return jsonify({'error': 'Order not confirmed'}), 400
    
    city = location.split(',')[0].strip()
    in_range = "In Range" if city.lower() == DEFAULT_CITY.lower() else "Out of Range"

    try:
        conn = get_db()
        cursor = conn.cursor()

        item_names = []
        for item in cart:
            item_id = item['id']
            cursor.execute('SELECT name FROM menu_items WHERE id = ?', (item_id,))
            row = cursor.fetchone()
            if row:
                item_names.append(f"{row[0]} (x{item['quantity']})")

        items_str = ', '.join(item_names)

        cursor.execute('INSERT INTO orders (items, location, total_price, in_range, status) VALUES (?, ?, ?, ?, ?)',
                       (items_str, location, total_price, in_range, 'Order Placed'))
        conn.commit()
        order_id = cursor.lastrowid
        conn.close()

        app.logger.info(f"Order {order_id} confirmed and saved to database.")

        # Start a thread to update the order status
        threading.Thread(target=update_order_status_automatically, args=(order_id,), daemon=True).start()

        return jsonify({'message': 'Order confirmed', 'order_id': order_id})
    except Exception as e:
        app.logger.error(f"Error saving order: {e}")
        return jsonify({'error': 'Failed to save order'}), 500

def update_order_status_automatically(order_id):
    """Automatically updates the order status at specific intervals."""
    try:
        statuses = [
            ('Food Being Prepared', 60),  # After 1 minute
            ('Out for Delivery', 600),   # After 10 minutes
            ('Order Delivered', 900)     # After 15 minutes
        ]

        for status, delay in statuses:
            time.sleep(delay)  # Wait for the specified time
            conn = get_db()  # Open a new connection for each update
            cursor = conn.cursor()
            app.logger.info(f"Updating order {order_id} status to {status}")
            cursor.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
            conn.commit()
            conn.close()
            app.logger.info(f"Order {order_id} status updated to {status}")
    except Exception as e:
        app.logger.error(f"Error in automatic status update for order {order_id}: {e}")

@app.route('/api/orders', methods=['GET'])
def fetch_orders():
    """Fetch all orders."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id, items, location, total_price, in_range, status, timestamp FROM orders')
        rows = cursor.fetchall()
        conn.close()

        orders = [dict(zip([column[0] for column in cursor.description], row)) for row in rows]
        return jsonify(orders)
    except Exception as e:
        app.logger.error(f"Error fetching orders: {e}")
        return jsonify({'error': 'Failed to fetch orders'}), 500
@app.route('/api/order/<int:order_id>/items', methods=['GET'])
def get_order_items(order_id):
    """Retrieve the items of a specific order."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT items FROM orders WHERE id = ?', (order_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return jsonify({'items': row[0]})
        else:
            return jsonify({'error': 'Order not found'}), 404
    except Exception as e:
        app.logger.error(f"Error fetching order items: {e}")
        return jsonify({'error': 'Failed to fetch order items'}), 500
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
