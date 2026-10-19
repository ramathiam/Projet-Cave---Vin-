import sqlite3

DB_NAME = "macave.db"

def get_db_connection():
    """
    Établit une connexion avec la base de données SQLite.
    row_factory = sqlite3.Row permet de manipuler les lignes comme des dictionnaires (ex: row['nom']).
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    # Active impérativement les contraintes de clés étrangères sous SQLite (désactivées par défaut)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """
    Crée l'ensemble des tables de la base de données relationnelle si elles n'existent pas.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Table des utilisateurs (gestion des comptes et sécurité)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usager (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    # 2. Table des étagères (R2: noms uniques par cave, capacité strictement positive)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS etagere (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            nom TEXT NOT NULL,
            capacite INTEGER NOT NULL CHECK(capacite > 0),
            FOREIGN KEY (user_id) REFERENCES usager(id) ON DELETE CASCADE,
            UNIQUE(user_id, nom)
        )
    """)

    # 3. Table des références de vins (Catalogue communautaire partagé)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domaine TEXT NOT NULL,
            nom_cuvee TEXT NOT NULL,
            type_vin TEXT NOT NULL,
            millesime INTEGER NOT NULL,
            region TEXT NOT NULL,
            description TEXT,
            photo_etiquette TEXT,
            UNIQUE(domaine, nom_cuvee, type_vin, millesime, region)
        )
    """)

    # 4. Table des bouteilles (Exemplaires physiques détenus par les utilisateurs)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bouteille (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vin_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            etagere_id INTEGER NOT NULL,
            prix_achat REAL NOT NULL CHECK(prix_achat >= 0),
            date_ajout TEXT NOT NULL,
            date_sortie TEXT,
            statut TEXT NOT NULL CHECK(statut IN ('en_stock', 'archivee')),
            FOREIGN KEY (vin_id) REFERENCES vin(id),
            FOREIGN KEY (user_id) REFERENCES usager(id) ON DELETE CASCADE,
            FOREIGN KEY (etagere_id) REFERENCES etagere(id) ON DELETE CASCADE
        )
    """)

    # 5. Table des évaluations (R8/R11: Une bouteille archivée = une évaluation unique, note de 0 à 20)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evaluation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vin_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            bouteille_id INTEGER UNIQUE NOT NULL,
            note INTEGER NOT NULL CHECK(note >= 0 AND note <= 20),
            commentaire TEXT,
            FOREIGN KEY (vin_id) REFERENCES vin(id),
            FOREIGN KEY (user_id) REFERENCES usager(id) ON DELETE CASCADE,
            FOREIGN KEY (bouteille_id) REFERENCES bouteille(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Base de données 'macave.db' et tables créées avec succès !")
    
    
    
def inserer_vins_tests():
    """Insère quelques vins de test dans le catalogue communautaire."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    vins_initiaux = [
        ("Château Margaux", "Premier Grand Cru", "Rouge", 2015, "Bordeaux", "Un grand vin élégant et structuré.", None),
        ("Domaine Leflaive", "Puligny-Montrachet", "Blanc", 2018, "Bourgogne", "Notes minérales et beurrées.", None),
        ("Château Miraval", "Rosé", "Rosé", 2021, "Provence", "Frais, fruité et léger.", None),
        ("Champagne Bollinger", "Special Cuvée", "Effervescent", 2017, "Champagne", "Bulles fines et arômes briochés.", None)
    ]
    
    for vin in vins_initiaux:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO vin (domaine, nom_cuvee, type_vin, millesime, region, description, photo_etiquette)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, vin)
        except Exception as e:
            print(f"Erreur insertion vin : {e}")
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    inserer_vins_tests()
    print("Base de données et vins de test initialisés avec succès !")