from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import os

# ------------------------
# APP CONFIG
# ------------------------
app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Ensure DB folder exists
db_folder = os.path.join(os.path.dirname(__file__), 'db')
os.makedirs(db_folder, exist_ok=True)
db_path = os.path.join(db_folder, 'database.sqlite')

# Database config
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ------------------------
# DATABASE MODELS
# ------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')


class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)  # quantity only, no price

class Allotment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='Allotted')

    item = db.relationship('Inventory', backref='allotments')
    user = db.relationship('User', backref='allotments')



# ------------------------
# INIT DATABASE
# ------------------------
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', password='admin', role='admin')
        db.session.add(admin)
        db.session.commit()

# ------------------------
# ROUTES
# ------------------------
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(
            username=request.form['username'],
            password=request.form['password']
        ).first()
        if user:
            session['user'] = user.username
            session['role'] = user.role
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'donor':
                return redirect(url_for('donor_page'))
            else:
                return redirect(url_for('inventory'))
        flash("Invalid credentials", "error")
    return render_template('login.html')


@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    # Handle adding new user
    if request.method == 'POST':
        new_username = request.form['username']
        new_password = request.form['password']
        new_role = request.form['role']

        if User.query.filter_by(username=new_username).first():
            flash(f"User '{new_username}' already exists!", "error")
        else:
            user = User(username=new_username, password=new_password, role=new_role)
            db.session.add(user)
            db.session.commit()
            flash(f"User '{new_username}' added successfully!", "success")

    users = User.query.all()
    items = Inventory.query.all()
    allotments = Allotment.query.all()   # <<< ADD THIS
    return render_template('admin_dashboard.html', users=users, items=items, allotments=allotments)



@app.route('/delete_item/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    item = Inventory.query.get(item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
        flash(f"{item.name} has been deleted from inventory.", "success")
    else:
        flash("Item not found.", "error")
    return redirect(url_for('admin_dashboard'))

@app.route('/allot', methods=['POST'])
def allot_item():
    item_id = request.form['item_id']
    user_id = request.form['user_id']

    item = Inventory.query.get(item_id)
    if not item:
        flash("Item not found!", "error")
        return redirect(url_for('admin_dashboard'))

    # Check if already allotted or received
    existing = Allotment.query.filter_by(item_id=item_id, status='Allotted').first()
    if existing:
        flash("This item is already allotted!", "error")
        return redirect(url_for('admin_dashboard'))

    # Allot full quantity
    allotment = Allotment(item_id=item.id, user_id=user_id, quantity=item.quantity, status='Allotted')
    db.session.add(allotment)

    # Set inventory quantity to 0 (full allot)
    item.quantity = 0
    db.session.commit()
    flash("Item successfully allotted!", "success")
    return redirect(url_for('admin_dashboard'))






@app.route('/receive/<int:allot_id>', methods=['POST'])
def receive_item(allot_id):
    allot = Allotment.query.get(allot_id)
    if allot and allot.user.username == session.get('user'):
        allot.status = 'Received'
        db.session.commit()
        flash("Marked as received.", "success")
    return redirect(url_for('inventory'))

@app.route('/drop/<int:allot_id>', methods=['POST'])
def drop_item(allot_id):
    allot = Allotment.query.get(allot_id)
    if allot and allot.user.username == session.get('user'):
        allot.status = 'Dropped'
        db.session.commit()
        flash("Order dropped and moved to previous orders.", "success")
    return redirect(url_for('inventory'))








@app.route('/donor', methods=['GET', 'POST'])
def donor_page():
    if session.get('role') != 'donor':
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        quantity = request.form['quantity']

        item = Inventory(name=name, quantity=int(quantity))
        db.session.add(item)
        db.session.commit()
        flash(f"Item '{name}' ({quantity} kg) added successfully!", "success")

    items = Inventory.query.all()
    return render_template('donor_page.html', items=items)


@app.route('/inventory')
def inventory():
    if not session.get('user'):
        return redirect(url_for('login'))

    current_user = User.query.filter_by(username=session['user']).first()

    # Only show user's allotments that are not dropped
    user_allotments = Allotment.query.filter(
        Allotment.user_id == current_user.id,
        Allotment.status.in_(['Allotted', 'Received'])
    ).all()

    return render_template('user.html', allotments=user_allotments)




@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ------------------------
# RUN APP
# ------------------------
if __name__ == '__main__':
    app.run(debug=True)
