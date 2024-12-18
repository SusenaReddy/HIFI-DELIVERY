from flask import Flask, request, render_template, redirect, url_for
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configurations
UPLOAD_FOLDER = 'static/uploads'
DATABASE = '../database/menu.db'  # Adjust path to database folder
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure necessary folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('../database', exist_ok=True)

# Initialize Database
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS menu_items (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL,
                            description TEXT NOT NULL,
                            price REAL NOT NULL,
                            image_path TEXT,
                            category TEXT NOT NULL DEFAULT 'veg',
                            discount REAL NOT NULL DEFAULT 0.0)''')
        conn.commit()

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
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        category = request.form['category']
        discount = float(request.form.get('discount', 0))
        image = request.files['image']

        # Save Image
        filename = secure_filename(image.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(image_path)

        # Insert into Database
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO menu_items (name, description, price, category, discount, image_path) VALUES (?, ?, ?, ?, ?, ?)',
                           (name, description, price, category, discount, image_path))
            conn.commit()

        return redirect(url_for('index'))
    except Exception as e:
        print(f"Error: {e}")
        return "Error adding item!", 500

# Edit Item
@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()

        if request.method == 'POST':
            name = request.form['name']
            description = request.form['description']
            price = float(request.form['price'])
            category = request.form['category']
            discount = float(request.form.get('discount', 0))
            image = request.files.get('image')

            if image and image.filename:
                filename = secure_filename(image.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image.save(image_path)
                cursor.execute('UPDATE menu_items SET name=?, description=?, price=?, category=?, discount=?, image_path=? WHERE id=?',
                               (name, description, price, category, discount, image_path, item_id))
            else:
                cursor.execute('UPDATE menu_items SET name=?, description=?, price=?, category=?, discount=? WHERE id=?',
                               (name, description, price, category, discount, item_id))

            conn.commit()
            return redirect(url_for('index'))

        cursor.execute('SELECT * FROM menu_items WHERE id=?', (item_id,))
        item = cursor.fetchone()
    return render_template('menu_management.html', item=item, items=[])

# Delete Item
@app.route('/delete_item/<int:item_id>')
def delete_item(item_id):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM menu_items WHERE id=?', (item_id,))
        conn.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
