from flask import Flask, render_template, jsonify, request, redirect, url_for,session
from datetime import datetime,timedelta
import sqlite3
import os
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)

# Configurations
DATABASE = 'instance/HIFIeats.db'  # Adjust path to database folder
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'mysecrethifi'
# Initialize Database
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS menu_items (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL,
                            description TEXT NOT NULL,
                            price REAL NOT NULL,
                            image_path TEXT NOT NULL,
                            category TEXT NOT NULL DEFAULT 'veg',
                            subcategory TEXT NOT NULL DEFAULT 'starter',
                            discount REAL NOT NULL DEFAULT 0.0)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS DeliveryData (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            orderId TEXT NOT NULL,
                            deliveryAgentId INTEGER NOT NULL,
                            pickupTime TEXT NOT NULL,
                            scheduledDeliveryTime TEXT NOT NULL,
                            status TEXT DEFAULT 'Pending',
                            FOREIGN KEY (deliveryAgentId) REFERENCES Delivery_Agent (id))''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS Delivery_Agent (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT NOT NULL,
                            approved INTEGER DEFAULT 0)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS DeliveryAgentPerformance (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            agent_id INTEGER NOT NULL,
                            orders_delivered INTEGER DEFAULT 0,
                            on_time_deliveries INTEGER DEFAULT 0,
                            customer_ratings REAL DEFAULT 0.0,
                            cancellation_rate REAL DEFAULT 0.0,
                            FOREIGN KEY (agent_id) REFERENCES Delivery_Agent (id))''')
        conn.commit()

# Database connection helper
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Home Page
@app.route('/')
def index():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM menu_items')
        items = cursor.fetchall()
    return render_template('menu_management.html', items=items, item=None)

# Add Item
@app.route('/add_item', methods=['POST'])
def add_item():
    try:
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        category = request.form.get('category')
        subcategory = request.form.get('subcategory')
        discount = request.form.get('discount', 0)
        image = request.files.get('image')

        # Validate numeric fields
        price = float(price)
        discount = float(discount)

        # Save the uploaded image
        if image and image.filename != '':
            image_filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            image.save(image_path)
        else:
            return "Image is required!", 400

        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO menu_items (name, description, price, image_path, category, subcategory, discount) VALUES (?, ?, ?, ?, ?, ?, ?)',
                           (name, description, price, image_path, category, subcategory, discount))
            conn.commit()

        return redirect(url_for('index'))
    except Exception as e:
        return f"Error adding item: {e}", 500

# Edit Item
@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            if request.method == 'POST':
                name = request.form.get('name')
                description = request.form.get('description')
                price = float(request.form.get('price'))
                category = request.form.get('category')
                subcategory = request.form.get('subcategory')
                discount = float(request.form.get('discount', 0))
                image = request.files.get('image')

                if image:
                    image_filename = secure_filename(image.filename)
                    image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
                    image.save(image_path)
                    cursor.execute('UPDATE menu_items SET name=?, description=?, price=?, image_path=?, category=?, subcategory=?, discount=? WHERE id=?',
                                   (name, description, price, image_path, category, subcategory, discount, item_id))
                else:
                    cursor.execute('UPDATE menu_items SET name=?, description=?, price=?, category=?, subcategory=?, discount=? WHERE id=?',
                                   (name, description, price, category, subcategory, discount, item_id))
                conn.commit()
                return redirect(url_for('index'))

            cursor.execute('SELECT * FROM menu_items WHERE id=?', (item_id,))
            item = cursor.fetchone()
        return render_template('menu_management.html', item=item, items=[])
    except Exception as e:
        return f"Error editing item: {e}", 500

# Delete Item
@app.route('/delete_item/<int:item_id>')
def delete_item(item_id):
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM menu_items WHERE id=?', (item_id,))
            conn.commit()
        return redirect(url_for('index'))
    except Exception as e:
        return f"Error deleting item: {e}", 500

# Order Assignment Page
@app.route('/orderassign', methods=['GET', 'POST'])
def orderassign():
    return render_template('orderassign.html')

# Fetch Approved Delivery Agents
@app.route('/get_agents', methods=['GET'])
def get_agents():
    conn = get_db_connection()
    agents = conn.execute('''SELECT a.id, a.username,a.location, ap.orders_delivered, ap.on_time_deliveries,
                                     ap.customer_ratings, ap.cancellation_rate
                              FROM Delivery_Agent a
                              JOIN DeliveryAgentPerformance ap ON a.id = ap.agent_id
                              WHERE a.approved = 1''').fetchall()
    conn.close()
    agent_data = [dict(agent) for agent in agents]
    return jsonify({'agents': agent_data})
# Assign Order
@app.route('/assign_order', methods=['POST'])
def assign_order():
    data = request.get_json()
    orderId = data['orderId']
    deliveryAgentId = data['deliveryAgentId']
    scheduledDeliveryTime = data['scheduledDeliveryTime']
    pickupTime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    status = 'Pending'

    conn = get_db_connection()
    conn.execute('''INSERT INTO DeliveryData (orderId, deliveryAgentId, pickupTime, scheduledDeliveryTime, status)
                    VALUES (?, ?, ?, ?, ?)''',
                 (orderId, deliveryAgentId, pickupTime, scheduledDeliveryTime, status))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Order assigned successfully!'})
@app.route('/get_orders', methods=['GET'])
def get_orders():
    conn = get_db_connection()
    query = '''
        SELECT * 
        FROM orders 
        WHERE id NOT IN (SELECT orderId FROM DeliveryData)
    '''
    orders = conn.execute(query).fetchall()
    conn.close()
    # Convert rows to list of dictionaries for JSON response
    orders_list = [dict(order) for order in orders]
    return jsonify(orders_list)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'agent_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, username, approved 
            FROM Delivery_Agent 
            WHERE username = ? AND password = ?
        ''', (username, password))
        agent = cursor.fetchone()
        conn.close()

        if agent:
            if agent['approved'] == 1:  # Check if the agent is approved
                session['agent_id'] = agent['id']
                session['username'] = agent['username']
                return redirect(url_for('update_status_page'))
            else:
                return render_template('login.html', error="Your account is not approved yet")
        else:
            return render_template('login.html', error="Invalid username or password")

    return render_template('login.html')

# Logout route
@app.route('/logout')
def logout():
    session.pop('agent_id', None)
    session.pop('username', None)
    return redirect(url_for('login'))

# Update status page route
@app.route('/update_status_page')
@login_required
def update_status_page():
    return render_template('update_status.html')

# Get deliveries route
@app.route('/get_deliveries')
@login_required
def get_deliveries():
    agent_id = session.get('agent_id')
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, orderId, pickupTime, scheduledDeliveryTime, status
        FROM DeliveryData
        WHERE deliveryAgentId = ?
        ORDER BY scheduledDeliveryTime DESC
    ''', (agent_id,))

    deliveries = []
    for row in cursor.fetchall():
        deliveries.append({
            'id': row['id'],
            'orderId': row['orderid'],
            'pickupTime': row['pickupTime'],
            'scheduledTime': row['scheduledDeliveryTime'],
            'status': row['status'] or 'Pending'
        })

    conn.close()
    return jsonify(deliveries)

# Update delivery status route
@app.route('/update_status', methods=['POST'])
@login_required
def update_status():
    agent_id = session.get('agent_id')
    data = request.json
    delivery_id = data.get('delivery_id')
    new_status = data.get('status')

    if not delivery_id or not new_status:
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Verify that the delivery belongs to the logged-in agent
        cursor.execute('''
            SELECT deliveryAgentId
            FROM DeliveryData 
            WHERE id = ?
        ''', (delivery_id,))
        result = cursor.fetchone()

        if not result or result['deliveryAgentId'] != agent_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        # Update the status of the delivery
        cursor.execute('''
            UPDATE DeliveryData
            SET status = ?
            WHERE id = ? AND deliveryAgentId = ?
        ''', (new_status, delivery_id, agent_id))

        conn.commit()
        conn.close()

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/deliveries')
def deliveries():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, orderid, deliveryAgentId, pickupTime, scheduledDeliveryTime, status 
        FROM DeliveryData
    ''')

    deliveries = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(deliveries)

# Render the HTML page
@app.route('/track_delivery')
def track_delivery():
    return render_template('track_delivery.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
