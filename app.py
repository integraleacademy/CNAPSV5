from flask import Flask, render_template, request, redirect, url_for, send_file
import os, json, smtplib, io, zipfile
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

@app.route("/download", methods=["POST"])
def download():
    row_id = int(request.form["row_id"])
    data = load_data()
    if 0 <= row_id < len(data):
        row = data[row_id]
        mem_zip = io.BytesIO()
        with zipfile.ZipFile(mem_zip, 'w') as zipf:
            for f in row["fichiers"]:
                path = os.path.join("static", f)
                if os.path.exists(path):
                    zipf.write(path, arcname=os.path.basename(path))
        mem_zip.seek(0)
        filename = f"{row['prenom']}_{row['nom']}_documents.zip"
        return send_file(mem_zip, as_attachment=True, download_name=filename)
    return redirect("/admin")

def send_email(subject, body, to):
    msg = EmailMessage()
    prenom, nom = body.split()[4], body.split()[5]
    msg.set_content(f"""Bonjour,

Nous confirmons la réception de votre dossier CNAPS.

Nom : {nom}
Prénom : {prenom}

Votre dossier est en cours de traitement. Vous serez recontacté sous peu.

Cordialement,
L'équipe Intégrale Academy
""")
    msg["Subject"] = subject
    msg["From"] = os.environ["SMTP_USER"]
    msg["To"] = to

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
        smtp.send_message(msg)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
