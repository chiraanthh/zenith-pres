from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired
from werkzeug.security import check_password_hash

# Initialize Flask app and set up the database connection
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace this with a secure key
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:7100@localhost/namma_drug_manager'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database connection
db = SQLAlchemy(app)

# User model for SQLAlchemy
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

# Login form using Flask-WTF
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired()])
    password = PasswordField('Password', validators=[InputRequired()])

# Route for the login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        # Query the database to find the user
        user = User.query.filter_by(username=username).first()

        if user and user.password == password:  # Check for plain text password
            # If the user exists and the password matches, redirect to home
            return redirect(url_for('home'))
        else:
            # If login fails, show an error message
            flash('Invalid username or password', 'danger')

    return render_template('login.html', form=form)

# Route for the home page (after successful login)
@app.route('/home')
def home():
    return render_template('home.html')

if __name__ == '__main__':
    app.run(debug=True)
