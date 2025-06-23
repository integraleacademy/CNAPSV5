from flask import Flask, render_template, request, redirect, send_file, url_for
import os
import json
import smtplib
import zipfile
from email.message import EmailMessage

UPLOAD_FOLDER = '/mnt/data/uploads'
DATA_FILE = '/mnt/data/data.json'


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
    return []

def save_data(data):
        # Email admin

        # Email stagiaire
    with open(DATA_FILE, 'w') as f:

def index():

def submit():
    nom = request.form['nom']
    prenom = request.form['prenom']
    email = request.form['email']

    fichiers = []

    def save_files(files, prefix, nom, prenom):
        paths = []
        for file in files:
            if file and file.filename:
                filename = f"{nom}_{prenom}_{prefix}_{file.filename}"
        return paths


    data.append({
        "nom": nom,
        "prenom": prenom,
        "email": email,
        "fichiers": fichiers

        # Email admin

        # Email stagiaire



def admin():

def delete():

    new_data = []

    for entry in data:
        if entry['nom'] == nom and entry['prenom'] == prenom:
            # Supprimer les fichiers associés
            for file in fichiers:
                if os.path.exists(path):
        else:



def download():

    if not entry or not entry["fichiers"]:
        return "Aucun fichier trouvé.", 404

    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file in entry["fichiers"]:
            if os.path.exists(full_path):



def uploaded_file(filename):


if __name__ == "__main__":


def update_status():

    for entry in data:
        if entry['nom'] == nom and entry['prenom'] == prenom:
            entry['statut'] = new_status

        # Email admin

        # Email stagiaire

