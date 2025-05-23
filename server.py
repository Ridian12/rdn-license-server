from flask import Flask, request, jsonify
import json, time, hashlib, os

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.json")
LICENSES_FILE = os.path.join(BASE_DIR, "licenses.json")

def initialize_file(file_path, default_data):
    if not os.path.exists(file_path):
        print(f"[INIT] Fișierul {file_path} nu există. Se creează cu valori implicite.")
        with open(file_path, 'w') as f:
            json.dump(default_data, f, indent=4)

initialize_file(USERS_FILE, {})
initialize_file(LICENSES_FILE, {})

def load_json(file):
    try:
        with open(file, 'r') as f:
            data = json.load(f)
            print(f"[LOAD] {file} încărcat cu succes ({len(data)} înregistrări).")
            return data
    except Exception as e:
        print(f"[ERROR] Eroare la citirea fișierului {file}: {e}")
        return {}

def save_json(file, data):
    try:
        with open(file, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"[SAVE] {file} salvat cu succes.")
    except Exception as e:
        print(f"[ERROR] Eroare la scrierea fișierului {file}: {e}")

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    print(f"[REGISTER] Date primite: {data}")
    
    try:
        user, pwd, licenta, hwid = data["user"], data["pwd"], data["licenta"], data["hwid"]
    except KeyError as e:
        return jsonify({"error": f"Missing key: {str(e)}"}), 400

    users = load_json(USERS_FILE)
    licenses = load_json(LICENSES_FILE)

    if user in users:
        print("[WARN] Utilizatorul deja există.")
        return jsonify({"error": "User already exists"}), 400
    if licenta not in licenses or licenses[licenta].get("activated"):
        print("[WARN] Licență invalidă sau deja activată.")
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
    print(f"[LOGIN] Date primite: {data}")

    try:
        user, pwd, hwid = data["user"], data["pwd"], data["hwid"]
    except KeyError as e:
        return jsonify({"error": f"Missing key: {str(e)}"}), 400

    users = load_json(USERS_FILE)
    licenses = load_json(LICENSES_FILE)

    user_data = users.get(user)
    if not user_data:
        print("[WARN] Utilizator inexistent.")
        return jsonify({"error": "User not found"}), 400
    if hashlib.sha256(pwd.encode()).hexdigest() != user_data["password"]:
        print("[WARN] Parolă greșită.")
        return jsonify({"error": "Wrong password"}), 400
    if user_data["hwid"] != hwid:
        print("[WARN] HWID greșit.")
        return jsonify({"error": "Wrong HWID"}), 400

    lic_data = licenses.get(user_data["license"])
    if not lic_data or not lic_data.get("activated") or lic_data["expiry_timestamp"] < time.time():
        print("[WARN] Licență invalidă sau expirată.")
        return jsonify({"error": "Licență invalidă sau expirată"}), 400

    print("[SUCCESS] Autentificare reușită.")
    return jsonify({
        "success": True,
        "license_valid": True,
        "expiry_timestamp": lic_data["expiry_timestamp"]
    })

@app.route("/add_license", methods=["POST"])
def add_license():
    data = request.json
    print(f"[ADD LICENSE] Date primite: {data}")
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
    cwd = os.getcwd()
    print("[INFO] Acces homepage.")
    return f"RIDIAN LICENSE SERVER ONLINE<br>Director curent: {cwd}", 200

@app.route("/test_write", methods=["POST"])
def test_write():
    try:
        with open("test_write.txt", "w") as f:
            f.write("test scriere OK")
        print("[TEST] Scriere în test_write.txt reușită.")
        return "Scriere reușită", 200
    except Exception as e:
        print(f"[ERROR] Test scriere eșuat: {e}")
        return f"Eroare la scriere: {e}", 500

if __name__ == "__main__":
    print("[SERVER] Pornire server Flask...")
    app.run(host="0.0.0.0", port=5000)
