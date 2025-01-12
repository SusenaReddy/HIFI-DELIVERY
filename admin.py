from flask import Flask, request, render_template, redirect, url_for
import sqlite3
import os
from werkzeug.utils import secure_filename
app = Flask(__name__)
# Configurations
DATABASE = 'instance\HIFIeats.db'  # Adjust path to database folder
UPLOAD_FOLDER = '../static/uploads'
os.makedirs('../database', exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize Database
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
        # Retrieve form data
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        category = request.form.get('category')
        subcategory = request.form.get('subcategory')
        discount = request.form.get('discount', 0)
        image = request.files.get('image')  # Corrected this line
        
        # Validate numeric fields
        try:
            price = float(price)
            discount = float(discount)
        except ValueError:
            return "Price and discount must be numeric values!", 400

        # Save the uploaded image
        if image and image.filename != '':
            image_filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            image.save(image_path)
        else:
            return "Image is required!", 400

        # Insert into Database
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO menu_items (name, description, price, image_path, category, subcategory, discount) VALUES (?, ?, ?, ?, ?, ?, ?)',
                           (name, description, price, image_path, category, subcategory, discount))
            conn.commit()

        return redirect(url_for('index'))
    except Exception as e:
        print(f"Error: {e}")
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
                price = request.form.get('price')
                category = request.form.get('category')
                subcategory = request.form.get('subcategory')
                discount = request.form.get('discount', 0)
                image = request.files.get('image')

                # Validate form data
                if not name or not description or not price or not category or not subcategory:
                    return "All fields except image are required!", 400

                try:
                    price = float(price)
                    discount = float(discount)
                except ValueError:
                    return "Price and discount must be numeric values!", 400

                # Update the image if provided
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
        print(f"Error: {e}")
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
        print(f"Error: {e}")
        return f"Error deleting item: {e}", 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
