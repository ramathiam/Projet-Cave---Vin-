import os
import pytest
from database import init_db, get_db_connection
from models import Utilisateur, Etagere, Bouteille, Vin

@pytest.fixture(autouse=True)
def setup_test_db():
    """Initialise une base de données propre avant chaque test."""
    # Utilisation d'une base de test temporaire
    import database
    database.DB_NAME = "test_macave.db"
    
    # Supprimer l'ancienne base de test si elle existe
    if os.path.exists("test_macave.db"):
        os.remove("test_macave.db")
        
    init_db()
    yield
    # Nettoyage après le test
    if os.path.exists("test_macave.db"):
        os.remove("test_macave.db")

def test_creation_utilisateur_et_hachage():
    """Vérifie la création d'un utilisateur et le hachage sécurisé du mot de passe."""
    user = Utilisateur.creer("testuser", "test@mail.com", "monpassword123")
    assert user is not None
    assert user.username == "testuser"
    assert user.verifier_password("monpassword123") is True
    assert user.verifier_password("mauvaispassword") is False

def test_contrainte_capacite_etagere():
    """Vérifie que la règle R3 sur la capacité maximale d'une étagère est respectée."""
    user = Utilisateur.creer("vinophile", "vino@mail.com", "pwd123")
    etagere = Etagere.creer(user.id, "Étagère Haute", 2) # Capacité de 2 bouteilles
    
    # Insérer un vin de test
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO vin (domaine, nom_cuvee, type_vin, millesime, region) VALUES (?, ?, ?, ?, ?)",
                   ("Domaine Test", "Cuvée Test", "Rouge", 2020, "Bordeaux"))
    vin_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Ajout de la 1ère bouteille (doit réussir)
    succes1, msg1 = Bouteille.ajouter(vin_id, user.id, etagere.id, 15.0)
    assert succes1 is True

    # Ajout de la 2ème bouteille (doit réussir)
    succes2, msg2 = Bouteille.ajouter(vin_id, user.id, etagere.id, 20.0)
    assert succes2 is True

    # Ajout de la 3ème bouteille (doit échouer car capacité = 2)
    succes3, msg3 = Bouteille.ajouter(vin_id, user.id, etagere.id, 25.0)
    assert succes3 is False
    assert "capacité maximale" in msg3