from flask import Flask, render_template, request, redirect, url_for, session, flash
from database import init_db, get_db_connection
from models import Utilisateur, Etagere, Bouteille, Vin

# Initialisation de l'application Flask
app = Flask(__name__)
app.secret_key = "macave_secret_key_tres_securisee"  # Nécessaire pour les sessions Flask

# Initialisation automatique de la base de données au lancement
init_db()

@app.route("/")
def index():
    """Page d'accueil publique de l'application."""
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Gère l'inscription d'un nouvel utilisateur."""
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        user = Utilisateur.creer(username, email, password)
        if user:
            flash("Compte créé avec succès ! Vous pouvez vous connecter.", "success")
            return redirect(url_for("login"))
        else:
            flash("Erreur : Ce nom d'utilisateur ou cet email est déjà utilisé.", "danger")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Gère l'authentification de l'utilisateur."""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = Utilisateur.trouver_par_username(username)
        if user and user.verifier_password(password):
            session["user_id"] = user.id
            session["username"] = user.username
            flash(f"Bienvenue, {user.username} !", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Nom d'utilisateur ou mot de passe incorrect.", "danger")

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    """Tableau de bord personnel avec indicateurs officiels (Section 5.2)."""
    if "user_id" not in session:
        flash("Veuillez vous connecter pour accéder à votre tableau de bord.", "warning")
        return redirect(url_for("login"))
    
    user_id = session["user_id"]
    stats = Etagere.get_statistiques_globales(user_id)
    
    return render_template("dashboard.html", username=session["username"], stats=stats)

@app.route("/logout")
def logout():
    """Déconnecte l'utilisateur en effaçant la session."""
    session.clear()
    flash("Vous avez été déconnecté avec succès.", "info")
    return redirect(url_for("index"))

@app.route("/etageres", methods=["GET", "POST"])
def gerer_etageres():
    """Permet de lister et de créer des étagères pour l'utilisateur connecté."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    if request.method == "POST":
        nom = request.form.get("nom")
        capacite = request.form.get("capacite")
        
        try:
            capacite = int(capacite)
            etagere = Etagere.creer(user_id, nom, capacite)
            if etagere:
                flash("Étagère créée avec succès !", "success")
            else:
                flash("Erreur : Une étagère avec ce nom existe déjà.", "danger")
        except ValueError:
            flash("La capacité doit être un nombre entier valide.", "danger")
            
        return redirect(url_for("gerer_etageres"))

    etageres = Etagere.lister_par_utilisateur(user_id)
    return render_template("etageres.html", etageres=etageres)

@app.route("/bouteilles/ajouter", methods=["GET", "POST"])
def ajouter_bouteille():
    """Permet d'ajouter une bouteille physique en stock dans une étagère."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = get_db_connection()

    if request.method == "POST":
        vin_id = request.form.get("vin_id")
        etagere_id = request.form.get("etagere_id")
        prix_achat = request.form.get("prix_achat")

        try:
            prix_achat = float(prix_achat)
            succes, message = Bouteille.ajouter(vin_id, user_id, etagere_id, prix_achat)
            if succes:
                flash(message, "success")
                return redirect(url_for("gerer_etageres"))
            else:
                flash(message, "danger")
        except ValueError:
            flash("Le prix d'achat doit être un nombre valide.", "danger")

    vins = conn.execute("SELECT * FROM vin").fetchall()
    etageres = conn.execute("SELECT * FROM etagere WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()

    return render_template("ajouter_bouteille.html", vins=vins, etageres=etageres)

@app.route("/bouteille/<int:bouteille_id>/archiver", methods=["GET", "POST"])
def archiver_bouteille(bouteille_id):
    """Permet d'archiver une bouteille et d'enregistrer son évaluation unique (R8, R11)."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = get_db_connection()

    bouteille_row = conn.execute(
        "SELECT * FROM bouteille WHERE id = ? AND user_id = ? AND statut = 'en_stock'",
        (bouteille_id, user_id)
    ).fetchone()

    if not bouteille_row:
        conn.close()
        flash("Bouteille introuvable, déjà archivée ou non autorisée.", "danger")
        return redirect(url_for("gerer_etageres"))

    bouteille = Bouteille(
        bouteille_row['id'],
        bouteille_row['vin_id'],
        bouteille_row['user_id'],
        bouteille_row['etagere_id'],
        bouteille_row['prix_achat'],
        bouteille_row['date_ajout'],
        bouteille_row['date_sortie'],
        bouteille_row['statut']
    )

    if request.method == "POST":
        try:
            note = int(request.form.get("note"))
            commentaire = request.form.get("commentaire")

            if not (0 <= note <= 20):
                flash("La note doit être comprise entre 0 et 20.", "danger")
            else:
                succes = bouteille.archiver(note, commentaire)
                if succes:
                    flash("Bouteille archivée et évaluation enregistrée avec succès !", "success")
                    return redirect(url_for("dashboard"))
                else:
                    flash("Erreur lors de l'archivage de la bouteille.", "danger")
        except ValueError:
            flash("Veuillez entrer une note valide.", "danger")

    conn.close()
    return render_template("archiver_bouteille.html", bouteille=bouteille)

@app.route("/catalogue")
def catalogue():
    """Affiche le catalogue communautaire des vins avec leurs notes moyennes."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM vin").fetchall()
    conn.close()

    vins = []
    for r in rows:
        vin = Vin(
            r['id'], r['domaine'], r['nom_cuvee'], r['type_vin'],
            r['millesime'], r['region'], r['description'], r['photo_etiquette']
        )
        vin.note_communautaire = vin.calculer_note_communautaire()
        vins.append(vin)

    return render_template("catalogue.html", vins=vins)

if __name__ == "__main__":
    app.run(debug=True)