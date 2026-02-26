from flask import Flask, render_template, request, redirect, url_for, flash
import os
import json
import smtplib
import logging
from datetime import datetime
from email.message import EmailMessage
from PIL import Image, ImageDraw, ImageFont
import requests

app = Flask(__name__)
app.secret_key = "supersecretkey"
PUBLIC_FORM_URL = "https://cnapsv3.onrender.com/public-form"

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


def get_storage_paths():
    preferred_root = '/mnt/data'
    fallback_root = os.path.join(app.root_path, 'data')

    for root in (preferred_root, fallback_root):
        upload_folder = os.path.join(root, 'uploads')
        data_file = os.path.join(root, 'data.json')
        try:
            os.makedirs(upload_folder, exist_ok=True)
            if not os.path.exists(data_file):
                with open(data_file, 'w', encoding='utf-8') as f:
                    json.dump([], f)
            return upload_folder, data_file
        except OSError:
            continue

    raise RuntimeError("Aucun dossier de stockage accessible n'a pu être initialisé.")


UPLOAD_FOLDER, DATA_FILE = get_storage_paths()

FORMATIONS = {
    "APS": {
        "label": "AGENT DE PREVENTION ET DE SECURITE (APS)",
        "rncp": "34054",
        "nature": "Titre à Finalité Professionnelle (TFP) Agent de Prévention et de Sécurité - Agrément de la CPNEFP n°8320032701 en date du 23/06/2025 (valable jusqu'au 23/06/2028)",
    },
    "A3P": {
        "label": "AGENT DE PROTECTION PHYSIQUE DES PERSONNES (A3P)",
        "rncp": "35098",
        "nature": "Titre à Finalité Professionnelle (TFP) Agent de Protection Physique des Personnes - Agrément de la CPNEFP n°8320111201 en date du 27/06/2025 (valable jusqu'au 27/06/2028)",
    }
}


def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def clean_value(text):
    return (text or "").strip()


def generate_justificatif_pdf(stagiaire):
    safe_nom = stagiaire['nom'].replace(' ', '_')
    safe_prenom = stagiaire['prenom'].replace(' ', '_')
    filename = f"justificatif_preinscription_{safe_nom}_{safe_prenom}_{stagiaire['formation'].lower()}.pdf"
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    formation = FORMATIONS[stagiaire['formation']]
    lines = [
        "ANNEXE : Justificatif de préinscription à une formation",
        "",
        "Cadre réservé à l’organisme de formation",
        "Je soussigné(e), Monsieur Clément VAILLANT",
        "Responsable de l'organisme de formation : INTEGRALE SECURITE FORMATIONS",
        "Numéro d'enregistrement DIRECCTE : 93830600283",
        "Autorisé à exercer par le CNAPS sous le numéro : FOR-083-2027-02-08-20220755135",
        "Contact : 04 22 47 07 68 – integralesecuriteformations@gmail.com",
        f"Certifie que Monsieur / Madame : {stagiaire['nom']} {stagiaire['prenom']}",
        "est préinscrit(e) à la formation qualifiante ci-dessous :",
        f"Libellé exact de la formation : {formation['label']}",
        f"Numéro d'enregistrement RNCP : {formation['rncp']}",
        f"Nature de la formation : {formation['nature']}",
        f"Dates de la formation : {stagiaire['session']} qui se déroulera à Puget sur Argens (83480).",
        "Lieu(x) de réalisation de la formation : Intégrale Sécurité Formations - 54 chemin du Carreou - 83480 PUGET SUR ARGENS",
        "",
        "Monsieur Clément VAILLANT",
        "Directeur Général – Intégrale Sécurité Formations",
    ]

    image = Image.new("RGB", (1240, 1754), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
    except Exception:
        font = ImageFont.load_default()
        title_font = font

    y = 60
    for i, line in enumerate(lines):
        current_font = title_font if i == 0 else font
        wrapped = []
        words = line.split(" ")
        part = ""
        for word in words:
            test = (part + " " + word).strip()
            if draw.textlength(test, font=current_font) <= 1100:
                part = test
            else:
                wrapped.append(part)
                part = word
        wrapped.append(part)
        for segment in wrapped:
            draw.text((70, y), segment, fill="black", font=current_font)
            y += 40 if i == 0 else 34
        if line == "":
            y += 10

    signature_path = os.path.join("static", "signature_bloc.png")
    if os.path.exists(signature_path):
        signature = Image.open(signature_path).convert("RGB")
        signature.thumbnail((320, 160))
        image.paste(signature, (70, y + 10))

    image.save(file_path, "PDF", resolution=100.0)
    return file_path


def send_email_with_attachment(user_email, subject, contenu_txt, contenu_html, attachment_path):
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("EMAIL_USER")
    smtp_password = os.environ.get("EMAIL_PASSWORD")

    if not smtp_user or not smtp_password:
        message = "EMAIL_USER ou EMAIL_PASSWORD non définis"
        logger.warning(message)
        return False, message

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = user_email
        msg.set_content(contenu_txt)
        msg.add_alternative(contenu_html, subtype="html")

        with open(attachment_path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="application",
                subtype="pdf",
                filename=os.path.basename(attachment_path)
            )

        with smtplib.SMTP(smtp_server, smtp_port, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        return True, "Email envoyé"
    except Exception as e:
        logger.exception("Erreur envoi mail vers %s", user_email)
        return False, str(e)


def send_sms_notification(stagiaire):
    sms_webhook_url = os.environ.get("SMS_WEBHOOK_URL")
    if not sms_webhook_url:
        message = "SMS_WEBHOOK_URL non défini"
        logger.warning(message)
        return False, message

    payload = {
        "phone": stagiaire["telephone"],
        "name": f"{stagiaire['prenom']} {stagiaire['nom']}",
        "formation": stagiaire["formation"],
        "session": stagiaire["session"],
    }

    headers = {"Content-Type": "application/json"}
    sms_api_key = os.environ.get("SMS_API_KEY")
    if sms_api_key:
        headers["Authorization"] = f"Bearer {sms_api_key}"

    try:
        response = requests.post(sms_webhook_url, json=payload, headers=headers, timeout=20)
        if response.ok:
            return True, "SMS envoyé"
        return False, f"HTTP {response.status_code}: {response.text[:200]}"
    except requests.RequestException as e:
        logger.exception("Erreur envoi SMS vers %s", stagiaire["telephone"])
        return False, str(e)


def get_mail_content(stagiaire, cnaps_link):
    formation = FORMATIONS[stagiaire['formation']]['label']
    subject = "Votre formation - Procédure demande d'autorisation CNAPS"
    text = f"""Bonjour,\n\nVous souhaitez suivre une formation {formation}.\n\nVous pouvez déposer votre dossier CNAPS puis cliquer sur ce lien : {cnaps_link}\n\nLa Team Intégrale Academy"""
    html = f"""
    <html><body style=\"font-family:Arial,sans-serif;line-height:1.6;color:#222;\">
    <p>Bonjour,</p>
    <p>Vous souhaitez suivre une formation <b>{formation}</b>. Pour intégrer une formation aux métiers de la sécurité privée, vous devez obtenir une autorisation préalable d'entrée en formation délivrée par le CNAPS (Ministère de l'intérieur).</p>
    <p>Pour obtenir cette autorisation, vous devez à présent créer votre espace particulier sur le site internet du CNAPS (Ministère de l'intérieur) en cliquant ici : <a href=\"https://espace-usagers.cnaps.interieur.gouv.fr/usager/app/creation-compte-pp\">https://espace-usagers.cnaps.interieur.gouv.fr/usager/app/creation-compte-pp</a></p>
    <p>Vous devrez joindre à votre demande :</p>
    <p>➡️ Une copie lisible de votre pièce d’identité (carte d'identité recto verso ou passeport ou titre de séjour recto verso). Le permis de conduire n'est pas accepté.</p>
    <p>➡️ Un justificatif de domicile de moins de 3 mois (pas de facture de téléphone). Acceptés : facture d’eau, d’électricité, de gaz, quittance de loyer.</p>
    <p>➡️ Si vous êtes hébergé(e) :<br>- Pièce d’identité de l’hébergeant<br>- Attestation d’hébergement - Modèle officiel à télécharger ici : <a href=\"https://www.service-public.fr/simulateur/calcul/AttestationHebergement\">https://www.service-public.fr/simulateur/calcul/AttestationHebergement</a></p>
    <p>➡️ Le justificatif de pré-inscription en centre de formation que vous trouverez en pièce jointe.</p>
    <p>➡️ Si vous êtes étranger, vous devrez également fournir :<br>- Casier judiciaire de votre pays de naissance de moins de 3 mois traduit en français<br>- Diplôme français supérieur au brevet ou test TCF de moins de 2 ans</p>
    <p>Attention, tout document manquant ou incomplet entraînera un retard de traitement de la part des services du CNAPS.</p>
    <p><b>Important :</b> Pour un meilleur suivi de votre dossier, nous vous remercions de bien vouloir cliquer sur le bouton ci-dessous dès que votre dossier CNAPS aura été déposé :</p>
    <p style=\"margin:24px 0;\"><a href=\"{cnaps_link}\" style=\"background:#198754;color:#fff;text-decoration:none;padding:12px 18px;border-radius:6px;font-weight:bold;\">J'ai déposé mon dossier auprès du CNAPS</a></p>
    <p>Nous restons à votre disposition au 04 22 47 07 68 pour tous renseignements complémentaires,</p>
    <p>La Team Intégrale Academy</p>
    </body></html>
    """
    return subject, text, html


@app.route('/')
def index():
    return redirect(PUBLIC_FORM_URL)


@app.route('/submit', methods=['POST'])
def submit():
    nom = clean_value(request.form.get('nom'))
    prenom = clean_value(request.form.get('prenom'))
    email = clean_value(request.form.get('email'))
    telephone = clean_value(request.form.get('telephone'))
    formation = clean_value(request.form.get('formation'))
    session = clean_value(request.form.get('session'))

    if formation not in FORMATIONS:
        flash("Formation invalide.")
        return redirect(url_for('index'))

    data = load_data()
    dossier = {
        "nom": nom,
        "prenom": prenom,
        "email": email,
        "telephone": telephone,
        "formation": formation,
        "session": session,
        "date_preinscription": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "cnaps_depose": False,
        "cnaps_depose_date": "",
        "email_sent": False,
        "email_error": "",
        "sms_sent": False,
        "sms_error": "",
    }

    data.append(dossier)
    save_data(data)
    index_dossier = len(data) - 1

    justificatif_path = generate_justificatif_pdf(dossier)
    cnaps_link = url_for('cnaps_submitted', index=index_dossier, _external=True)
    subject, txt, html = get_mail_content(dossier, cnaps_link)
    email_sent, email_error = send_email_with_attachment(email, subject, txt, html, justificatif_path)
    sms_sent, sms_error = send_sms_notification(dossier)

    data[index_dossier]["email_sent"] = email_sent
    data[index_dossier]["email_error"] = email_error
    data[index_dossier]["sms_sent"] = sms_sent
    data[index_dossier]["sms_error"] = sms_error
    save_data(data)

    if not email_sent or not sms_sent:
        logger.warning(
            "Notifications incomplètes pour %s %s (email=%s, sms=%s)",
            prenom,
            nom,
            email_error,
            sms_error,
        )

    return redirect(url_for('confirmation'))


@app.route('/cnaps_submitted/<int:index>')
def cnaps_submitted(index):
    data = load_data()
    if 0 <= index < len(data):
        data[index]['cnaps_depose'] = True
        data[index]['cnaps_depose_date'] = datetime.now().strftime("%d/%m/%Y %H:%M")
        save_data(data)
    return render_template('cnaps_submitted.html')


@app.route('/confirmation')
def confirmation():
    return render_template('confirmation.html')


@app.route('/admin')
def admin():
    data = load_data()
    return render_template('admin.html', data=data, dossier_count=len(data))


@app.route('/reset', methods=['POST'])
def reset():
    save_data([])
    for f in os.listdir(UPLOAD_FOLDER):
        try:
            if f.lower().endswith('.pdf'):
                os.remove(os.path.join(UPLOAD_FOLDER, f))
        except Exception:
            pass
    flash("✅ Base et justificatifs PDF vidés avec succès.")
    return redirect(url_for('admin'))
