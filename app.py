
from flask import Flask, render_template, request, redirect, send_file
import sqlite3
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('cnaps.db')
    conn.row_factory = sqlite3.Row
    return conn

# Ajout colonne check_auto si manquante
with get_db_connection() as conn:
    try:
        conn.execute("ALTER TABLE dossiers ADD COLUMN check_auto TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # La colonne existe déjà

def verifier_statut_cnaps(lien):
    try:
        if not lien:
            return ""
        r = requests.get(lien, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        text = soup.get_text().lower()
        if "accepté" in text:
            return "accepté"
        elif "instruction" in text:
            return "instruction en cours"
        elif "décision" in text:
            return "décision en cours"
        else:
            return ""
    except:
        return ""

@app.route("/")
def index():
    conn = get_db_connection()
    dossiers = conn.execute('SELECT * FROM dossiers').fetchall()
    conn.close()
    return render_template("index.html", dossiers=dossiers)

@app.route("/add", methods=["POST"])
def add():
    nom = request.form["nom"]
    prenom = request.form["prenom"]
    formation = request.form.get("formation", "")
    session = request.form.get("session", "")
    lien = request.form.get("lien", "")
    statut_dossier = "INCOMPLET"
    statut_cnaps = ""
    commentaire = ""
    check_auto = verifier_statut_cnaps(lien)

    conn = get_db_connection()
    conn.execute("INSERT INTO dossiers (nom, prenom, formation, session, lien, statut_dossier, statut_cnaps, commentaire, check_auto) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 (nom, prenom, formation, session, lien, statut_dossier, statut_cnaps, commentaire, check_auto))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/verifier/<int:id>")
def verifier(id):
    conn = get_db_connection()
    dossier = conn.execute("SELECT * FROM dossiers WHERE id = ?", (id,)).fetchone()
    if dossier and dossier["lien"]:
        statut = verifier_statut_cnaps(dossier["lien"])
        conn.execute("UPDATE dossiers SET check_auto = ? WHERE id = ?", (statut, id))
        conn.commit()
    conn.close()
    return redirect("/")
