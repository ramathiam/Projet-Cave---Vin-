import sqlite3
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection

class Utilisateur:
    def __init__(self, id, username, email, password_hash):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash

    @staticmethod
    def creer(username, email, password):
        pwd_hash = generate_password_hash(password)
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO usager (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, pwd_hash)
            )
            conn.commit()
            user_id = cursor.lastrowid
            return Utilisateur(user_id, username, email, pwd_hash)
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()

    @staticmethod
    def trouver_par_username(username):
        conn = get_db_connection()
        row = conn.execute("SELECT * FROM usager WHERE username = ?", (username,)).fetchone()
        conn.close()
        if row:
            return Utilisateur(row['id'], row['username'], row['email'], row['password_hash'])
        return None

    def verifier_password(self, password):
        return check_password_hash(self.password_hash, password)


class Etagere:
    def __init__(self, id, user_id, nom, capacite):
        self.id = id
        self.user_id = user_id
        self.nom = nom
        self.capacite = capacite

    @staticmethod
    def creer(user_id, nom, capacite):
        """Crée une nouvelle étagère pour un utilisateur (R2)."""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO etagere (user_id, nom, capacite) VALUES (?, ?, ?)",
                (user_id, nom, capacite)
            )
            conn.commit()
            etagere_id = cursor.lastrowid
            return Etagere(etagere_id, user_id, nom, capacite)
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()
    
    @staticmethod
    def lister_par_utilisateur(user_id):
        """Récupère toutes les étagères d'un utilisateur."""
        conn = get_db_connection()
        rows = conn.execute("SELECT * FROM etagere WHERE user_id = ?", (user_id,)).fetchall()
        conn.close()
        return [Etagere(r['id'], r['user_id'], r['nom'], r['capacite']) for r in rows]

    def get_occupation(self):
        conn = get_db_connection()
        res = conn.execute(
            "SELECT COUNT(*) as count FROM bouteille WHERE etagere_id = ? AND statut = 'en_stock'",
            (self.id,)
        ).fetchone()
        conn.close()
        return res['count']

    def verifier_capacite(self, quantite_a_ajouter=1):
        return (self.get_occupation() + quantite_a_ajouter) <= self.capacite

    def est_vide(self):
        return self.get_occupation() == 0
    
    @staticmethod
    def get_statistiques_globales(user_id):
        """Calcule les indicateurs personnels pour le tableau de bord (Section 5.2)."""
        conn = get_db_connection()
        
        # Nombre total d'étagères et somme des capacités
        etageres = conn.execute("SELECT * FROM etagere WHERE user_id = ?", (user_id,)).fetchall()
        nb_etageres = len(etageres)
        somme_capacites = sum(e['capacite'] for e in etageres)
        
        # Nombre de bouteilles en stock et valeur du stock
        bouteilles = conn.execute(
            "SELECT * FROM bouteille WHERE user_id = ? AND statut = 'en_stock'",
            (user_id,)
        ).fetchall()
        nb_bouteilles = len(bouteilles)
        valeur_stock = sum(b['prix_achat'] for b in bouteilles if b['prix_achat'] is not None)
        
        # Nombre de références distinctes en stock
        refs_distinctes = len(set(b['vin_id'] for b in bouteilles))
        
        # Occupation globale (sécurité division par zéro)
        if somme_capacites > 0:
            taux_occupation = round((nb_bouteilles / somme_capacites) * 100, 1)
        else:
            taux_occupation = 0.0
            
        conn.close()
        
        return {
            "nb_etageres": nb_etageres,
            "nb_bouteilles": nb_bouteilles,
            "refs_distinctes": refs_distinctes,
            "valeur_stock": round(valeur_stock, 2),
            "somme_capacites": somme_capacites,
            "taux_occupation": taux_occupation
        }

    def supprimer(self):
        """Règle R5 : Une étagère non vide ne peut être supprimée."""
        if self.get_occupation() > 0:
            return False, "Erreur (R5) : Impossible de supprimer une étagère non vide."
        
        conn = get_db_connection()
        try:
            conn.execute("DELETE FROM etagere WHERE id = ?", (self.id,))
            conn.commit()
            return True, "Étagère supprimée avec succès."
        except Exception as e:
            return False, f"Erreur : {e}"
        finally:
            conn.close()


class Vin:
    def __init__(self, id, domaine, nom_cuvee, type_vin, millesime, region, description, photo_etiquette):
        self.id = id
        self.domaine = domaine
        self.nom_cuvee = nom_cuvee
        self.type_vin = type_vin
        self.millesime = millesime
        self.region = region
        self.description = description
        self.photo_etiquette = photo_etiquette

    def calculer_note_communautaire(self):
        conn = get_db_connection()
        res = conn.execute(
            "SELECT AVG(note) as moyenne, COUNT(*) as total FROM evaluation WHERE vin_id = ?",
            (self.id,)
        ).fetchone()
        conn.close()
        if res['total'] == 0 or res['moyenne'] is None:
            return None
        return round(res['moyenne'], 1)


class Bouteille:
    def __init__(self, id, vin_id, user_id, etagere_id, prix_achat, date_ajout, date_sortie, statut):
        self.id = id
        self.vin_id = vin_id
        self.user_id = user_id
        self.etagere_id = etagere_id
        self.prix_achat = prix_achat
        self.date_ajout = date_ajout
        self.date_sortie = date_sortie
        self.statut = statut

    @staticmethod
    def ajouter(vin_id, user_id, etagere_id, prix_achat):
        conn = get_db_connection()
        etagere_row = conn.execute("SELECT capacite FROM etagere WHERE id = ?", (etagere_id,)).fetchone()
        
        if not etagere_row:
            conn.close()
            return False, "Étagère introuvable."

        count_row = conn.execute(
            "SELECT COUNT(*) as count FROM bouteille WHERE etagere_id = ? AND statut = 'en_stock'",
            (etagere_id,)
        ).fetchone()

        if count_row['count'] >= etagere_row['capacite']:
            conn.close()
            return False, "Erreur : L'étagère a atteint sa capacité maximale (R3)."

        today = date.today().isoformat()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO bouteille (vin_id, user_id, etagere_id, prix_achat, date_ajout, statut) 
                   VALUES (?, ?, ?, ?, ?, 'en_stock')""",
                (vin_id, user_id, etagere_id, prix_achat, today)
            )
            conn.commit()
            return True, "Bouteille ajoutée avec succès."
        except Exception as e:
            return False, f"Erreur : {e}"
        finally:
            conn.close()

    def archiver(self, note, commentaire):
        if self.statut == 'archivee':
            return False

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            conn.execute("BEGIN TRANSACTION")
            today = date.today().isoformat()
            
            cursor.execute(
                "UPDATE bouteille SET statut = 'archivee', date_sortie = ? WHERE id = ?",
                (today, self.id)
            )
            
            cursor.execute(
                "INSERT INTO evaluation (vin_id, user_id, bouteille_id, note, commentaire) VALUES (?, ?, ?, ?, ?)",
                (self.vin_id, self.user_id, self.id, note, commentaire)
            )
            
            conn.commit()
            self.statut = 'archivee'
            self.date_sortie = today
            return True
        except Exception as e:
            conn.rollback()
            return False
        finally:
            conn.close()