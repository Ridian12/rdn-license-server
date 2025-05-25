from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
import hashlib
import time
import os
import datetime
import secrets

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

class SessionToken(db.Model):
    __tablename__ = 'session_tokens'
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False)
    username = db.Column(db.String(50), nullable=False)
    hwid = db.Column(db.String(128), nullable=False)
    expiry = db.Column(db.DateTime, nullable=False)

    def is_valid(self):
        return datetime.datetime.utcnow() < self.expiry

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

@app.route("/get_token", methods=["POST"])
def get_token():
    data = request.json
    hwid = data.get("hwid")
    if not hwid:
        return jsonify({"success": False, "error": "Missing HWID"}), 400

    user = User.query.filter_by(hwid=hwid).first()
    if not user:
        return jsonify({"success": False, "error": "HWID not found"}), 400

    lic = License.query.get(user.license_key)
    if not lic or not lic.activated or lic.expiry_timestamp < time.time():
        return jsonify({"success": False, "error": "Licență invalidă sau expirată"}), 400

    token_str = secrets.token_hex(32)
    expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=30)

    session_token = SessionToken(
        token=token_str,
        username=user.username,
        hwid=hwid,
        expiry=expiry
    )

    db.session.add(session_token)
    db.session.commit()

    return jsonify({"success": True, "token": token_str})

@app.route("/validate_token", methods=["POST"])
def validate_token():
    data = request.json
    token = data.get("token")
    if not token:
        return jsonify({"success": False, "error": "Missing token"}), 400

    session_token = SessionToken.query.filter_by(token=token).first()
    if not session_token or not session_token.is_valid():
        return jsonify({"success": False, "error": "Token invalid sau expirat"}), 400

    return jsonify({"success": True, "username": session_token.username})

# ---------------------- INIT DB ----------------------
# ---------------------- MAIN ----------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000)
