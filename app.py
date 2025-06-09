
import sqlite3
import threading
import time
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, redirect, send_file
import csv
import os

app = Flask(__name__)

DB_FILE = "dossiers.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS dossiers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT,
        prenom TEXT,
        formation TEXT,
        session TEXT,
        lien TEXT,
        statut_dossier TEXT,
        statut_cnaps TEXT,
        commentaire TEXT,
        check_auto TEXT
    )''')
    conn.commit()
    conn.close()

@app.route("/")
def index():
    conn = sqlite3.connect(DB_FILE)
    dossiers = conn.execute("SELECT * FROM dossiers").fetchall()
    conn.close()
    return render_template("index.html", dossiers=dossiers)

@app.route("/add", methods=["POST"])
def add():
    nom = request.form["nom"]
    prenom = request.form["prenom"]
    formation = request.form.get("formation", "")
    session = request.form.get("session", "")
    lien = request.form.get("lien", "")
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT INTO dossiers (nom, prenom, formation, session, lien, statut_dossier, statut_cnaps, commentaire, check_auto) VALUES (?, ?, ?, ?, ?, '', '', '', '')",
                 (nom, prenom, formation, session, lien))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/edit/<int:id>", methods=["POST"])
def edit(id):
    lien = request.form["lien"]
    conn = sqlite3.connect(DB_FILE)
    conn.execute("UPDATE dossiers SET lien=? WHERE id=?", (lien, id))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/statut/<int:id>/<string:statut>")
def toggle_statut_dossier(id, statut):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("UPDATE dossiers SET statut_dossier=? WHERE id=?", (statut, id))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/statut_cnaps/<int:id>", methods=["POST"])
def update_statut_cnaps(id):
    statut = request.form.get("statut", "")
    conn = sqlite3.connect(DB_FILE)
    conn.execute("UPDATE dossiers SET statut_cnaps=? WHERE id=?", (statut, id))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/commentaire/<int:id>", methods=["POST"])
def update_commentaire(id):
    commentaire = request.form["commentaire"]
    conn = sqlite3.connect(DB_FILE)
    conn.execute("UPDATE dossiers SET commentaire=? WHERE id=?", (commentaire, id))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/delete/<int:id>")
def delete(id):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("DELETE FROM dossiers WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/export")
def export_csv():
    conn = sqlite3.connect(DB_FILE)
    dossiers = conn.execute("SELECT * FROM dossiers").fetchall()
    conn.close()
    filename = "export_dossiers.csv"
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "nom", "prenom", "formation", "session", "lien", "statut_dossier", "statut_cnaps", "commentaire", "check_auto"])
        for d in dossiers:
            writer.writerow(d)
    return send_file(filename, as_attachment=True)

@app.route("/import")
def import_csv():
    return redirect("/")

def check_cnaps_loop():
    while True:
        try:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            dossiers = c.execute("SELECT id, lien FROM dossiers WHERE lien IS NOT NULL AND lien != ''").fetchall()
            for dossier_id, lien in dossiers:
                try:
                    r = requests.get(lien, timeout=10)
                    if "accepté" in r.text:
                        statut = "accepté"
                    elif "instruction" in r.text:
                        statut = "instruction en cours"
                    elif "décision" in r.text:
                        statut = "décision en cours"
                    else:
                        statut = ""
                    c.execute("UPDATE dossiers SET check_auto=? WHERE id=?", (statut, dossier_id))
                except Exception as e:
                    pass
            conn.commit()
            conn.close()
        except:
            pass
        time.sleep(300)

if __name__ == "__main__":
    init_db()
    threading.Thread(target=check_cnaps_loop, daemon=True).start()
    app.run(debug=True, host="0.0.0.0")
