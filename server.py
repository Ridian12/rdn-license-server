from flask import Flask, request, jsonify
import json, time, hashlib, os

app = Flask(__name__)
USERS_FILE = "users.json"
LICENSES_FILE = "licenses.json"

def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, 'r') as f:
        return json.load(f)

def save_json(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=4)

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    user, pwd, licenta, hwid = data["user"], data["pwd"], data["licenta"], data["hwid"]

    users = load_json(USERS_FILE)
    licenses = load_json(LICENSES_FILE)

    if user in users:
        return jsonify({"error": "User already exists"}), 400
    if licenta not in licenses or licenses[licenta].get("activated"):
        return jsonify({"error": "Licență invalidă sau activată"}), 400

    expiry = int(time.time()) + 7 * 24 * 60 * 60
    licenses[licenta] = {"activated": True, "expiry_timestamp": expiry}
    users[user] = {
        "password": hashlib.sha256(pwd.encode()).hexdigest(),
        "hwid": hwid,
        "license": licenta
    }

    save_json(USERS_FILE, users)
    save_json(LICENSES_FILE, licenses)
    return jsonify({"success": True})

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    user, pwd, hwid = data["user"], data["pwd"], data["hwid"]

    users = load_json(USERS_FILE)
    licenses = load_json(LICENSES_FILE)

    user_data = users.get(user)
    if not user_data:
        return jsonify({"error": "User not found"}), 400
    if hashlib.sha256(pwd.encode()).hexdigest() != user_data["password"]:
        return jsonify({"error": "Wrong password"}), 400
    if user_data["hwid"] != hwid:
        return jsonify({"error": "Wrong HWID"}), 400

    lic_data = licenses.get(user_data["license"])
    if not lic_data or not lic_data.get("activated") or lic_data["expiry_timestamp"] < time.time():
        return jsonify({"error": "Licență invalidă sau expirată"}), 400

    return jsonify({"success": True})

@app.route("/add_license", methods=["POST"])
def add_license():
    data = request.json
    license_key = data.get("license")
    if not license_key:
        return jsonify({"error": "No license provided"}), 400

    licenses = load_json(LICENSES_FILE)
    if license_key in licenses:
        return jsonify({"error": "License already exists"}), 400

    licenses[license_key] = {"activated": False, "expiry_timestamp": 0}
    save_json(LICENSES_FILE, licenses)
    return jsonify({"success": True, "license": license_key}), 200

@app.route("/")
def index():
    return "RIDIAN LICENSE SERVER ONLINE", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
