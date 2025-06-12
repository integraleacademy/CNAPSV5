
import os
import sqlite3
import csv
from flask import Flask, render_template, request, redirect, send_file
from datetime import datetime

app = Flask(__name__)

DATABASE = 'cnaps.db'

# Initialisation de la base de données avec la nouvelle colonne
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dossiers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT,
                prenom TEXT,
                formation TEXT,
                session TEXT,
                lien_suivi TEXT,
                statut_dossier TEXT,
                statut_cnaps TEXT,
                commentaire TEXT,
                date_de_transmission TEXT
            )
        """)
        conn.commit()

init_db()

@app.route("/")
def index():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM dossiers")
    dossiers = cursor.fetchall()
    conn.close()
    return render_template("index.html", dossiers=dossiers)

@app.route("/ajouter", methods=["POST"])
def ajouter():
    nom = request.form["nom"]
    prenom = request.form["prenom"]
    formation = request.form["formation"]
    session = request.form["session"]
    lien_suivi = request.form["lien_suivi"]
    statut_dossier = request.form["statut_dossier"]
    statut_cnaps = request.form["statut_cnaps"]
    commentaire = request.form["commentaire"]
    date_de_transmission = request.form["date_de_transmission"]

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO dossiers (nom, prenom, formation, session, lien_suivi, statut_dossier, statut_cnaps, commentaire, date_de_transmission)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (nom, prenom, formation, session, lien_suivi, statut_dossier, statut_cnaps, commentaire, date_de_transmission))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/supprimer/<int:id>")
def supprimer(id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM dossiers WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/export")
def export():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM dossiers")
    dossiers = cursor.fetchall()
    conn.close()

    filename = "export_cnaps.csv"
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "nom", "prenom", "formation", "session", "lien_suivi", "statut_dossier", "statut_cnaps", "commentaire", "date_de_transmission"])
        writer.writerows(dossiers)

    return send_file(filename, as_attachment=True)

@app.route("/import", methods=["POST"])
def importer():
    fichier = request.files["fichier"]
    if not fichier:
        return redirect("/")

    fichier.save("import.csv")


    with open("import.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        lignes = list(reader)

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    for ligne in lignes:
        cursor.execute("""
            INSERT OR REPLACE INTO dossiers (id, nom, prenom, formation, session, lien_suivi, statut_dossier, statut_cnaps, commentaire, date_de_transmission)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ligne["id"],
            ligne["nom"],
            ligne["prenom"],
            ligne["formation"],
            ligne["session"],
            ligne["lien_suivi"],
            ligne["statut_dossier"],
            ligne["statut_cnaps"],
            ligne["commentaire"],
            ligne.get("date_de_transmission", "")
        ))

    conn.commit()
    conn.close()

    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
