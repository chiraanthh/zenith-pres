from flask import Flask, request, render_template, redirect, url_for, flash, session, jsonify
import mysql.connector
from flask_cors import CORS
import random
import string

app = Flask(__name__)
CORS(app)
app.secret_key = 'your_secret_key_here'

# ---------------- DB CONFIG ----------------
db_config = {
    'host': 'mysql-db1-zenith-1503.j.aivencloud.com',
    'user': 'avnadmin',
    'password': 'AVNS_jfh0BOV8hX7cZMI7AI2',
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
        cursor = conn.cursor()
        cursor.execute("UPDATE orders SET status = 'Canceled' WHERE order_id = %s", (order_id,))
        conn.commit()

    flash(f"Order {order_id} has been canceled.")
    return redirect(url_for('admin_dashboard') + '#admin-orders')


# Add Hospital Route
@app.route('/add_hospital', methods=['POST'])
def add_hospital():
    name = request.form['name']
    location = request.form['location']

    with mysql.connector.connect(**db_config) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO hospitals (name, location) VALUES (%s, %s)", (name, location))
        conn.commit()

    flash("Hospital added successfully.")
    return redirect(url_for('admin_dashboard') + '#admin-hospitals')


# Delete Hospital Route
@app.route('/delete_hospital/<int:hospital_id>', methods=['POST'])
def delete_hospital(hospital_id):
    with mysql.connector.connect(**db_config) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM hospitals WHERE id = %s", (hospital_id,))
        conn.commit()

    flash("Hospital deleted successfully.")
    return redirect(url_for('admin_dashboard') + '#admin-hospitals')


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
    data = request.get_json()
    new_status = data.get('status')
    otp_entered = data.get('otp')

    with mysql.connector.connect(**db_config) as conn:
        cur = conn.cursor()

        # Fetch current OTP and status change count from DB
        cur.execute("SELECT otp, status_change_count FROM orders WHERE order_id = %s", (order_id,))
        row = cur.fetchone()

        if not row:
            return jsonify({'success': False, 'message': 'Order not found'})

        correct_otp, change_count = row

        if change_count >= 3:
            return jsonify({'success': False, 'message': 'Status change limit exceeded'})

        if new_status == "Delivered":
            if not otp_entered or otp_entered != correct_otp:
                return jsonify({'success': False, 'message': 'Invalid OTP'})

        # Update order status and increment counter
        cur.execute(""" 
            UPDATE orders 
            SET status = %s, status_change_count = status_change_count + 1 
            WHERE order_id = %s
        """, (new_status, order_id))
        conn.commit()

        return jsonify({'success': True})


# ---------------- PLACE ORDER ----------------
# Function to generate a random OTP
def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))


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
@app.route('/hospital')
def hospital_dashboard():
    if 'username' not in session or session.get('role') != 'hospital':
        return redirect(url_for('login'))  # Redirect to login if not hospital

    username = session['username']

    with mysql.connector.connect(**db_config) as conn:
        cursor = conn.cursor(dictionary=True)

        # Fetch inventory
        cursor.execute("SELECT * FROM inventory WHERE status = 'In Stock'")
        inventory = cursor.fetchall()

        # Fetch orders
        cursor.execute("SELECT * FROM orders WHERE customer = %s", (username,))
        orders = cursor.fetchall()

    return render_template('hospitalpage.html', 
                           page='hospital',
                           inventory=inventory,
                           orders=orders)



# ---------------- LOGOUT ----------------
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()  # Clear the session
    return redirect(url_for('login'))  # Redirect to the login page


@app.route('/add_stock', methods=['POST'])
def add_stock():
    drug_name = request.form.get('drug_name')
    quantity = request.form.get('quantity')

    print("Raw input:", drug_name, quantity)  # DEBUG

    if not drug_name or not quantity:
        flash("Please provide both drug name and quantity.")
        return redirect(url_for('admin_dashboard') + '#admin-inventory')

    try:
        quantity = int(quantity.strip())

        with mysql.connector.connect(**db_config) as conn:
            cur = conn.cursor(dictionary=True)

            cur.execute("SELECT quantity FROM inventory WHERE LOWER(drug_name) = LOWER(%s)", (drug_name,))
            existing = cur.fetchone()
            print("Existing:", existing)  # DEBUG

            if existing:
                new_quantity = existing['quantity'] + quantity
                cur.execute("UPDATE inventory SET quantity = %s WHERE LOWER(drug_name) = LOWER(%s)",
                            (new_quantity, drug_name))
                print(f"Updated {drug_name} to {new_quantity}")  # DEBUG
            else:
                cur.execute("INSERT INTO inventory (drug_name, quantity, status) VALUES (%s, %s, %s)",
                            (drug_name, quantity, 'Available'))
                print(f"Inserted new drug: {drug_name}")  # DEBUG

            conn.commit()
            cur.close()

        flash("Stock updated successfully!")
        return redirect(url_for('admin_dashboard') + '#admin-inventory')

    except Exception as e:
        print("Error adding stock:", e)
        flash("Something went wrong while adding stock.")
        return redirect(url_for('admin_dashboard') + '#admin-inventory')


# ---------------- MAIN ----------------
if __name__ == '__main__':
    app.run(debug=True)
