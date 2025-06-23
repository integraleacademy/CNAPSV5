
from flask import Flask, render_template, request, redirect, url_for
import os, json, smtplib
from email.message import EmailMessage
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_DIR = "static/uploads"
DATA_FILE = "data.json"

os.makedirs(UPLOAD_DIR, exist_ok=True)

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/submit", methods=["POST"])
def submit():
    nom = request.form["nom"]
    prenom = request.form["prenom"]
    email = request.form["email"]
    fichiers = []

    for field in request.files.getlist("identite"):
        if field.filename:
            filename = secure_filename(f"{nom}_{prenom}_id_{field.filename}")
            path = os.path.join(UPLOAD_DIR, filename)
            field.save(path)
            fichiers.append(f"uploads/{filename}")

    for fieldname in ["domicile", "identite_hebergeant", "attestation_hebergement"]:
        file = request.files.get(fieldname)
        if file and file.filename:
            filename = secure_filename(f"{nom}_{prenom}_{fieldname}_{file.filename}")
            path = os.path.join(UPLOAD_DIR, filename)
            file.save(path)
            fichiers.append(f"uploads/{filename}")

    data = load_data()
    data.append({"nom": nom, "prenom": prenom, "email": email, "fichiers": fichiers})
    save_data(data)

    send_email("Confirmation dépôt CNAPS", f"Dossier reçu pour {prenom} {nom}", email)
    return redirect("/")

@app.route("/admin")
def admin():
    data = load_data()
    return render_template("admin.html", data=data)

@app.route("/delete", methods=["POST"])
def delete():
    row_id = int(request.form["row_id"])
    data = load_data()
    if 0 <= row_id < len(data):
        data.pop(row_id)
        save_data(data)
    return redirect("/admin")

def send_email(subject, body, to):
    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"] = "ecole@integraleacademy.com"
    msg["To"] = to
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login("ecole@integraleacademy.com", os.environ["EMAIL_APP_PASSWORD"])
        smtp.send_message(msg)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
