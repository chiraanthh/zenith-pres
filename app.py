from flask import Flask, request, render_template, redirect, url_for, flash, session, jsonify
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


# ---------------- ADMIN PAGE ----------------
@app.route('/admin')
def admin_dashboard():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))  # Redirect to login if not admin

    with mysql.connector.connect(**db_config) as conn:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT order_id, customer, status, date, status_change_count FROM orders")
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

        cursor.execute(""" 
            SELECT order_id, changed_by, old_status, new_status, timestamp 
            FROM status_updates 
            ORDER BY timestamp DESC 
            LIMIT 10
        """)
        updates = cursor.fetchall()

    return render_template('adminpage.html', 
                           page='admin',
                           orders=orders,
                           pending_orders=pending,
                           upcoming_orders=upcoming,
                           inventory=inventory,
                           total_drugs=drugs_in_stock,
                           hospitals=hospitals,
                           updates=updates)
# Cancel Order Route
@app.route('/cancel_order/<int:order_id>', methods=['POST'])
def cancel_order(order_id):
    with mysql.connector.connect(**db_config) as conn:
        cursor = conn.cursor(dictionary=True)

        # Example logic to cancel an order (could be updating the status of the order to 'Canceled')
        cursor.execute("UPDATE orders SET status = 'Canceled' WHERE order_id = %s", (order_id,))
        conn.commit()

    flash(f"Order {order_id} has been canceled.")
    return redirect(url_for('admin_dashboard'))  # Redirect to the admin dashboard after canceling


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
@app.route('/update_order_status/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    new_status = None
    entered_otp = None

    # Handle form submission (from <form method="POST">)
    if request.form:
        new_status = request.form.get('status')
    # Handle fetch() JSON request
    elif request.is_json:
        data = request.get_json()
        new_status = data.get('status')
        entered_otp = data.get('otp')

    if not new_status:
        flash('Invalid status.')
        return redirect(url_for('vendor_dashboard'))

    with mysql.connector.connect(**db_config) as conn:
        cursor = conn.cursor(dictionary=True)

        # Fetch the order
        cursor.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
        order = cursor.fetchone()

        if not order:
            flash('Order not found.')
            return redirect(url_for('vendor_dashboard'))

        # Validate OTP if status is being set to Delivered
        if new_status == 'Delivered':
            if not entered_otp or str(entered_otp) != str(order.get("otp")):
                if request.is_json:
                    return jsonify({"success": False, "error": "Invalid OTP"})
                else:
                    flash('Invalid OTP.')
                    return redirect(url_for('vendor_dashboard'))

        # Update the status
        cursor.execute("""
            UPDATE orders
            SET status = %s, status_change_count = status_change_count + 1
            WHERE order_id = %s
        """, (new_status, order_id))
        conn.commit()

    if request.is_json:
        return jsonify({"success": True})
    else:
        flash('Order status updated successfully!')
        return redirect(url_for('vendor_dashboard'))

# ---------------- HOSPITAL PAGE ----------------
@app.route('/hospital')
def hospital_dashboard():
    if 'username' not in session or session.get('role') != 'hospital':
        return redirect(url_for('login'))  # Redirect to login if not hospital

    username = session['username']

    with mysql.connector.connect(**db_config) as conn:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM orders WHERE customer = %s", (username,))
        orders = cursor.fetchall()  # Fetch orders along with OTPs

    return render_template('hospitalpage.html', 
                           page='hospital',
                           orders=orders)

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


# ---------------- PLACE ORDER ----------------
import random
import string

# Function to generate a random OTP
def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))

# Update the `place_order` endpoint to generate OTP for pending orders
@app.route('/place_order', methods=['POST'])
def place_order():
    data = request.get_json()
    drug_name = data['drug_name']
    quantity = data['quantity']
    customer = data['customer']
    order_id = data['order_id']

    # Generate OTP only for pending orders
    otp = generate_otp()

    with mysql.connector.connect(**db_config) as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM inventory WHERE drug_name = %s", (drug_name,))
        inventory = cursor.fetchone()

        if inventory:
            available_quantity = inventory['quantity']
            if available_quantity >= quantity:
                # Insert order into database with OTP for pending orders
                cursor.execute("""
                    INSERT INTO orders (order_id, customer, drug_name, quantity, status, otp, date)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """, (order_id, customer, drug_name, quantity, 'Pending', otp))

                # Update inventory
                new_quantity = available_quantity - quantity
                cursor.execute("""
                    UPDATE inventory SET quantity = %s WHERE drug_name = %s
                """, (new_quantity, drug_name))

                conn.commit()

                return jsonify({"msg": "Order placed and inventory updated successfully", "otp": otp})

            else:
                return jsonify({"error": "Insufficient stock"})

        return jsonify({"error": "Drug not found"})


# ---------------- LOGOUT ----------------
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()  # Clear the session
    
    return redirect(url_for('login'))  # Redirect to the login page


# ---------------- MAIN ----------------
if __name__ == '__main__':
    app.run(debug=True)
