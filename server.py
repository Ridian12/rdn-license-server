from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
import hashlib
import time
import os

app = Flask(__name__)

# ---------------------- CONFIG ----------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://ridiandb_user:OhBij83nKsJxC6YLbPIMyiz9FEIqafkX@dpg-d0ocpo7fte5s738mjc1g-a.frankfurt-postgres.render.com/ridiandb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---------------------- MODELE ----------------------
class License(db.Model):
    __tablename__ = 'licenses'
    key = db.Column(db.String(100), primary_key=True)
    activated = db.Column(db.Boolean, default=False)
    expiry_timestamp = db.Column(db.Integer, default=0)

class User(db.Model):
    __tablename__ = 'users'
    username = db.Column(db.String(50), primary_key=True)
    password_hash = db.Column(db.String(128), nullable=False)
    hwid = db.Column(db.String(128), nullable=False)
    license_key = db.Column(db.String(100), db.ForeignKey('licenses.key'))

# ---------------------- ROUTEURI ----------------------
@app.route("/")
def index():
    return "RIDIAN LICENSE SERVER ONLINE cu PostgreSQL", 200

@app.route("/add_license", methods=["POST"])
def add_license():
    data = request.json
    license_key = data.get("license")
    if not license_key:
        return jsonify({"error": "No license provided"}), 400

    existing = License.query.get(license_key)
    if existing:
        return jsonify({"error": "License already exists"}), 400

    new_license = License(key=license_key, activated=False, expiry_timestamp=0)
    db.session.add(new_license)
    db.session.commit()
    return jsonify({"success": True, "license": license_key})

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    user, pwd, licenta, hwid = data["user"], data["pwd"], data["licenta"], data["hwid"]

    if User.query.get(user):
        return jsonify({"error": "User already exists"}), 400

    lic = License.query.get(licenta)
    if not lic or lic.activated:
        return jsonify({"error": "Licență invalidă sau activată"}), 400

    expiry = int(time.time()) + 7 * 24 * 60 * 60
    lic.activated = True
    lic.expiry_timestamp = expiry

    new_user = User(
        username=user,
        password_hash=hashlib.sha256(pwd.encode()).hexdigest(),
        hwid=hwid,
        license_key=licenta
    )

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"success": True})

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    user, pwd, hwid = data["user"], data["pwd"], data["hwid"]

    usr = User.query.get(user)
    if not usr:
        return jsonify({"error": "User not found"}), 400

    if hashlib.sha256(pwd.encode()).hexdigest() != usr.password_hash:
        return jsonify({"error": "Wrong password"}), 400

    if usr.hwid != hwid:
        return jsonify({"error": "Wrong HWID"}), 400

    lic = License.query.get(usr.license_key)
    if not lic or not lic.activated or lic.expiry_timestamp < time.time():
        return jsonify({"error": "Licență invalidă sau expirată"}), 400

    return jsonify({
        "success": True,
        "license_valid": True,
        "expiry_timestamp": lic.expiry_timestamp
    })

# ---------------------- INIT DB ----------------------
@app.before_first_request
def create_tables():
    db.create_all()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000)
