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
    user, pwd, licenta, hwid = data.get("user"), data.get("pwd"), data.get("licenta"), data.get("hwid")

    # Verificare input
    if not all([user, pwd, licenta, hwid]):
        return jsonify({"error": "Missing fields"}), 400

    users = load_json(USERS_FILE)
    licenses = load_json(LICENSES_FILE)

    # Verificăm dacă userul există deja
    if user in users:
        return jsonify({"error": "User already exists"}), 400

    # Verificăm licența: trebuie să existe, să nu fie deja activată (activated == False)
    # corectam aici, tu aveai if licenta not in licenses or licenses[licenta].get("activated")
    # care bloca licentele deja activate
    if licenta not in licenses:
        return jsonify({"error": "Licență invalidă"}), 400
    if licenses[licenta].get("activated", False):
        return jsonify({"error": "Licență deja activată"}), 400

    # Activăm licența pentru 7 zile de acum
    expiry = int(time.time()) + 7 * 24 * 60 * 60
    licenses[licenta]["activated"] = True
    licenses[licenta]["expiry_timestamp"] = expiry
    licenses[licenta]["assigned_to"] = user  # opțional, pentru tracking

    # Salvăm userul cu parola hashuită, hwid și licența asociată
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
    user, pwd, hwid = data.get("user"), data.get("pwd"), data.get("hwid")

    if not all([user, pwd, hwid]):
        return jsonify({"error": "Missing fields"}), 400

    users = load_json(USERS_FILE)
    licenses = load_json(LICENSES_FILE)

    user_data = users.get(user)
    if not user_data:
        return jsonify({"error": "User not found"}), 400

    # Verificăm parola
    if hashlib.sha256(pwd.encode()).hexdigest() != user_data["password"]:
        return jsonify({"error": "Wrong password"}), 400

    # Verificăm hwid
    if user_data["hwid"] != hwid:
        return jsonify({"error": "Wrong HWID"}), 400

    lic_key = user_data.get("license")
    lic_data = licenses.get(lic_key)
    if not lic_data:
        return jsonify({"error": "Licență asociată inexistentă"}), 400

    if not lic_data.get("activated", False):
        return jsonify({"error": "Licență neactivă"}), 400

    if lic_data.get("expiry_timestamp", 0) < time.time():
        return jsonify({"error": "Licență expirată"}), 400

    # Returnăm succes și date suplimentare
    return jsonify({
        "success": True,
        "license_valid": True,
        "expiry_timestamp": lic_data.get("expiry_timestamp")
    })

@app.route("/add_license", methods=["POST"])
def add_license():
    data = request.json
    license_key = data.get("license")
    if not license_key:
        return jsonify({"error": "No license provided"}), 400

    licenses = load_json(LICENSES_FILE)
    if license_key in licenses:
        return jsonify({"error": "License already exists"}), 400

    licenses[license_key] = {"activated": False, "expiry_timestamp": 0, "assigned_to": None}
    save_json(LICENSES_FILE, licenses)
    return jsonify({"success": True, "license": license_key}), 200

@app.route("/")
def index():
    return "RIDIAN LICENSE SERVER ONLINE", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
