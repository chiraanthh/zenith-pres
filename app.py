from flask import Flask, request, render_template, redirect, url_for, flash, session, jsonify, render_template_string

import mysql.connector
from flask_cors import CORS
app = Flask(__name__)
CORS(app)
app.secret_key = 'your_secret_key_here'

# ---------------- DB CONFIG ----------------
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Ch!raan1h',
    'database': 'drug'
}

# ---------------- DB CONNECTION ----------------
def get_db_connection():
    return mysql.connector.connect(**db_config)

# ---------------- LOGIN ----------------
@app.route('/')
def login():
    return render_template('login.html', page='login')

@app.route('/login', methods=['POST'])
def login_post():
    username = request.form['username']
    password = request.form['password']

    with mysql.connector.connect(**db_config) as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()

    if user:
        session['username'] = username
        session['role'] = user['role'].lower()
        if session['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif session['role'] == 'vendor':
            return redirect(url_for('vendor_dashboard'))
        elif session['role'] == 'hospital':
            return redirect(url_for('hospital_dashboard'))
    else:
        flash('Invalid login')
        return redirect(url_for('login'))
@app.route('/cancel_order/<int:order_id>', methods=['POST'])
def cancel_order(order_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT drug_name, quantity FROM orders WHERE order_id = %s", (order_id,))
    order = cursor.fetchone()

    if order:
        cursor.execute("""
            UPDATE inventory
            SET quantity = quantity + %s
            WHERE drug_name = %s
        """, (order['quantity'], order['drug_name']))

        cursor.execute("UPDATE orders SET status = 'Cancelled' WHERE order_id = %s", (order_id,))
        conn.commit()
        cursor.close()
        conn.close()

        # Return a small HTML snippet with redirect after 3 seconds
        return render_template_string("""
            <html>
            <head>
                <meta http-equiv="refresh" content="3;url={{ url_for('admin_dashboard') }}">
                <style>
                    body { font-family: 'Poppins', sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; }
                    .msg-box { text-align: center; border: 2px solid #ccc; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
                </style>
            </head>
            <body>
                <div class="msg-box">
                    <h2>✅ Order Cancelled</h2>
                    <p>Inventory has been reverted.</p>
                    <p>Redirecting to admin dashboard...</p>
                </div>
            </body>
            </html>
        """)

    else:
        return "Order not found", 404
    if order:
        # Revert the inventory quantity
        cursor.execute("""
            UPDATE inventory
            SET quantity = quantity + %s
            WHERE drug_name = %s
        """, (order['quantity'], order['drug_name']))

        # Update the order status to 'Cancelled'
        cursor.execute("UPDATE orders SET status = 'Cancelled' WHERE order_id = %s", (order_id,))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"msg": "Order cancelled and inventory reverted"})
    else:
        return jsonify({"error": "Order not found"}), 404

# ---------------- ADMIN PAGE ----------------
@app.route('/admin')
def admin_dashboard():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))  # Redirect to login if not admin

    with mysql.connector.connect(**db_config) as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM orders")
        orders = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) AS count FROM orders WHERE status = 'Pending'")
        pending = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) AS count FROM orders WHERE status = 'Upcoming'")
        upcoming = cursor.fetchone()['count']

        cursor.execute("SELECT * FROM inventory")
        inventory = cursor.fetchall()

        cursor.execute("SELECT SUM(quantity) AS total FROM inventory WHERE status = 'In Stock'")
        drugs_in_stock = cursor.fetchone()['total'] or 0

        cursor.execute("SELECT * FROM hospitals")
        hospitals = cursor.fetchall()

    return render_template('adminpage.html', 
                           page='admin',
                           orders=orders,
                           pending_orders=pending,
                           upcoming_orders=upcoming,
                           inventory=inventory,
                           total_drugs=drugs_in_stock,
                           hospitals=hospitals)

# ---------------- VENDOR PAGE ----------------
@app.route('/vendor')
def vendor_dashboard():
    if 'username' not in session or session.get('role') != 'vendor':
        return redirect(url_for('login'))  # Redirect to login if not vendor

    with mysql.connector.connect(**db_config) as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM orders")
        orders = cursor.fetchall()

        cursor.execute("SELECT * FROM inventory")
        inventory = cursor.fetchall()

    return render_template('vendorpage.html', 
                           page='vendor',
                           orders=orders,
                           inventory=inventory)

# ---------------- HOSPITAL PAGE ----------------
@app.route('/hospital')
def hospital_dashboard():
    if 'username' not in session or session.get('role') != 'hospital':
        return redirect(url_for('login'))  # Redirect to login if not hospital

    username = session['username']

    with mysql.connector.connect(**db_config) as conn:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM inventory WHERE status = 'In Stock'")
        inventory = cursor.fetchall()

        cursor.execute("SELECT * FROM orders WHERE customer = %s", (username,))
        orders = cursor.fetchall()

    return render_template('hospitalpage.html', 
                           page='hospital',
                           inventory=inventory,
                           orders=orders)

# ---------------- APIs FOR UNIVERSAL UPDATES ----------------
@app.route('/add_order', methods=['POST'])
def add_order():
    data = request.json
    with mysql.connector.connect(**db_config) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "REPLACE INTO orders (order_id, status, date, customer) VALUES (%s, %s, %s, %s)",
            (data['order_id'], data['status'], data['date'], data['customer'])
        )
        conn.commit()
    return jsonify({"msg": "Order added"})

@app.route('/add_inventory', methods=['POST'])
def add_inventory():
    data = request.json
    with mysql.connector.connect(**db_config) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "REPLACE INTO inventory (drug_name, quantity, status) VALUES (%s, %s, %s)",
            (data['drug_name'], data['quantity'], data['status'])
        )
        conn.commit()
    return jsonify({"msg": "Inventory updated"})

@app.route('/add_hospital', methods=['POST'])
def add_hospital():
    data = request.json
    with mysql.connector.connect(**db_config) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "REPLACE INTO hospitals (hospital_name, location, contact) VALUES (%s, %s, %s)",
            (data['hospital_name'], data['location'], data['contact'])
        )
        conn.commit()
    return jsonify({"msg": "Hospital added"})

@app.route('/dashboard-stats')
def dashboard_stats():
    with mysql.connector.connect(**db_config) as conn:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) AS count FROM orders WHERE status = 'Pending'")
        pending = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) AS count FROM orders WHERE status = 'Upcoming'")
        upcoming = cursor.fetchone()['count']

        cursor.execute("SELECT SUM(quantity) AS total FROM inventory WHERE status = 'In Stock'")
        in_stock = cursor.fetchone()['total'] or 0

    return jsonify({
        "pending": pending,
        "upcoming": upcoming,
        "drugs_in_stock": in_stock
    })

# ---------------- PLACE ORDER ----------------
@app.route('/place_order', methods=['POST'])
def place_order():
    # Get order data from the request
    data = request.get_json()
    drug_name = data['drug_name']
    quantity = data['quantity']
    customer = data['customer']  # Assuming this comes from the request

    # Fetch the inventory for the requested drug
    with mysql.connector.connect(**db_config) as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM inventory WHERE drug_name = %s", (drug_name,))
        inventory = cursor.fetchone()

        if inventory:
            available_quantity = inventory['quantity']  # Access quantity by column name
            if available_quantity >= quantity:
                # Place the order logic here...
                cursor.execute("""
                    INSERT INTO orders (order_id, customer, drug_name, quantity, status, date)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                """, (data['order_id'], customer, drug_name, quantity, 'Pending'))

                # Update the inventory after placing the order
                new_quantity = available_quantity - quantity
                cursor.execute("""
                    UPDATE inventory SET quantity = %s WHERE drug_name = %s
                """, (new_quantity, drug_name))

                conn.commit()

                return jsonify({"msg": "Order placed and inventory updated successfully"})

            else:
                return jsonify({"error": "Insufficient stock"})

        return jsonify({"error": "Drug not found"})

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()  # Clear the session
    flash('You have been logged out.')  # Show a flash message
    return redirect(url_for('login'))  # Redirect to the login page

# ---------------- MAIN ----------------
if __name__ == '__main__':
    app.run(debug=True)
