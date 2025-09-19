/*
    Auteur: Josoa (josoavj sur GitHub)
    Ce script est la source de la base de données du projet Planificator
    Veuillez vous réferer à la documentation ou envoyer un mail à l'auteur si vous avez besoin d'aide
*/

-- Supprimer complètement la base de données
DROP DATABASE IF EXISTS Planificator;

-- Création de la DB
CREATE DATABASE Planificator;
USE Planificator;

-- Table Compte
CREATE TABLE Account (
                         id_compte INT AUTO_INCREMENT PRIMARY KEY,  -- Identifiant unique pour chaque compte
                         nom VARCHAR(70) NOT NULL,
                         prenom VARCHAR(70) NOT NULL,
                         email VARCHAR(100) NOT NULL UNIQUE,
                         username VARCHAR(50) NOT NULL UNIQUE,
                         password VARCHAR(255) NOT NULL,
                         type_compte ENUM('Administrateur', 'Utilisateur') NOT NULL,  -- Type de compte
                         date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Date de création du compte
                         UNIQUE (nom, prenom)                -- Contrainte d'unicité sur le nom et prénom
);

/*
    Pour la table Account:
    - Il est recommandé d'utiliser un mot de passe crypté: veuillez crypter votre mot de passe en fonction du techno ou langage utilisé
    - Le mot de passe ne doit pas contenir des informations sensibles (Informations personnelles)
    - Un seul compte Administrateur est requis.
    - Seul l'administrateur qui possède le droit de supprimer des comptes dans la base de données.
*/

-- Compte administrateur unique
DELIMITER $$

CREATE TRIGGER avant_ajout_compte
    BEFORE INSERT ON Account
    FOR EACH ROW
BEGIN
    IF NEW.type_compte = 'Administrateur' AND (SELECT COUNT(*) FROM Account WHERE type_compte = 'Administrateur') > 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Un compte Administrateur existe déjà.';
    END IF;
END$$

DELIMITER ;

-- Vérification du mail
DELIMITER $$

CREATE TRIGGER ajout_compte
    BEFORE INSERT ON Account
    FOR EACH ROW
BEGIN
    IF NEW.email NOT LIKE '%@%.%' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'L\'email doit contenir un "@" et un "."';
    END IF;
END$$

CREATE TRIGGER maj_compte
    BEFORE UPDATE ON Account
    FOR EACH ROW
BEGIN
    IF NEW.email NOT LIKE '%@%.%' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'L\'email doit contenir un "@" et un "."';
    END IF;
END$$

DELIMITER ;

-- Modification du type de compte
DELIMITER $$

CREATE TRIGGER avant_maj_compte
    BEFORE UPDATE ON Account
    FOR EACH ROW
BEGIN
    IF OLD.type_compte != NEW.type_compte THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Le type de compte ne peut pas être modifié.';
    END IF;
END$$

DELIMITER ;


-- Pour le mot de passe

DELIMITER $$

CREATE TRIGGER avant_ajout_password
    BEFORE INSERT ON Account
    FOR EACH ROW
BEGIN
    IF CHAR_LENGTH(NEW.password) < 8 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Le mot de passe doit contenir au moins 8 caractères.';
    END IF;
END$$

CREATE TRIGGER avant_maj_password
    BEFORE UPDATE ON Account
    FOR EACH ROW
BEGIN
    IF CHAR_LENGTH(NEW.password) < 8 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Le mot de passe doit contenir au moins 8 caractères.';
    END IF;
END$$

DELIMITER ;

-- Empêcher la suppression du dernier compte administrateur présent dans la base de données
DELIMITER $$

CREATE TRIGGER avant_suppression_compte_administrateur
    BEFORE DELETE ON Account
    FOR EACH ROW
BEGIN
    IF OLD.type_compte = 'Administrateur' AND (SELECT COUNT(*) FROM Account WHERE type_compte = 'Administrateur') = 1 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La suppression du dernier compte Administrateur est interdite.';
    END IF;
END$$

DELIMITER ;

/*
    Début du script pour l'ensemble des tables utilisées dans Planificator
    Structuration:
    - Table Client: Pour les informations sur les clients
    - Table Contrat: Pour les informations sur les contrats des clients
    - Table TypeTraitement: Pour les types de traitements prévus pour les clients
    - Table Traitement: Pour les informations sur chaque service choisit par un client dans son contrat
    - Table Planning: Pour les informations sur le planning de chaque service dedié à un client
    - Table PlanningDetails: Pour les détails de chaque planning
    - Table Facture: Pour la facturation de chaque service du client
    - Table Remarque: Ajout d'un remarque et confirmation si un traitement est effectué
    - Table Signalement: Signalement pour un avancement ou décalage
    - Table Historique: Historique des traitements pour chaque client
*/

-- Table Client
CREATE TABLE Client (
                        client_id INT PRIMARY KEY AUTO_INCREMENT,
                        nom VARCHAR(255) NOT NULL,
                        prenom VARCHAR(255),
                        email VARCHAR(255) NOT NULL,
                        telephone VARCHAR(30) NOT NULL,
                        adresse VARCHAR(255) NOT NULL,
                        nif VARCHAR(50),
                        stat VARCHAR(50),
                        date_ajout DATE NOT NULL,
                        categorie ENUM ('Particulier', 'Organisation', 'Société') NOT NULL,
                        axe ENUM ('Nord (N)', 'Sud (S)', 'Est (E)', 'Ouest (O)', 'Centre (C)') NOT NULL
);

# NIF STAT: Valable uniquement pour les sociétés

/*
    Dans le code back-end:
    Si ce n'est pas un particulier alors prénom change en Responsable
*/

CREATE TABLE Contrat (
                         contrat_id INT PRIMARY KEY AUTO_INCREMENT,
                         client_id INT NOT NULL,
                         reference_contrat VARCHAR(20),
                         date_contrat DATE NOT NULL,
                         date_debut DATE NOT NULL,
                         date_fin VARCHAR(50),
                         statut_contrat ENUM ('Actif', 'Terminé', 'Résilié') NOT NULL DEFAULT 'Actif',
                         duree_contrat INT DEFAULT NULL,
                         duree ENUM ('Indeterminée', 'Déterminée') NOT NULL,
                         categorie ENUM ('Nouveau', 'Renouvellement') NOT NULL,
                         FOREIGN KEY (client_id) REFERENCES Client(client_id) ON DELETE CASCADE
);

/*
    Cette partie est à décommenter si vous voulez calculer la duréee du contrat.
    L'opération se fait en fonction de la date de fin et date de début du contrat
    Dans le code, lors de l'ajout du contrat:
    SELECT *, DATEDIFF(date_fin, date_debut) AS duree FROM Contrat;
*/

-- Type de traitement utilisant enum
CREATE TABLE TypeTraitement (
                                id_type_traitement INT PRIMARY KEY AUTO_INCREMENT,
                                categorieTraitement ENUM ('AT: Anti termites', 'PC', 'NI: Nettoyage Industriel', 'RO: Ramassage Ordures'),
                                typeTraitement ENUM('Dératisation (PC)', 'Désinfection (PC)', 'Désinsectisation (PC)', 'Fumigation (PC)', 'Nettoyage industriel (NI)', 'Anti termites (AT)', 'Ramassage ordure') NOT NULL
);


-- Table Traitement
CREATE TABLE Traitement (
                            traitement_id INT PRIMARY KEY AUTO_INCREMENT,
                            contrat_id INT NOT NULL,
                            id_type_traitement INT NOT NULL, 
                            FOREIGN KEY (contrat_id) REFERENCES Contrat(contrat_id) ON DELETE CASCADE,
                            FOREIGN KEY (id_type_traitement) REFERENCES TypeTraitement(id_type_traitement) ON DELETE CASCADE 
);


-- Table Planning
CREATE TABLE Planning (
                          planning_id INT PRIMARY KEY AUTO_INCREMENT,
                          traitement_id INT NOT NULL,
                          date_debut_planification DATE,
                          mois_debut INT,
                          mois_fin INT,
                          duree_traitement INT NOT NULL DEFAULT 12,
                          redondance INT NOT NULL,
                          date_fin_planification DATE,
                          FOREIGN KEY (traitement_id) REFERENCES Traitement(traitement_id) ON DELETE CASCADE
);

-- Table PlanningDetails
CREATE TABLE PlanningDetails (
                                 planning_detail_id INT PRIMARY KEY AUTO_INCREMENT,
                                 planning_id INT NOT NULL,
                                 date_planification DATE NOT NULL,
                                 statut ENUM ('Effectué', 'À venir') NOT NULL,
                                 FOREIGN KEY (planning_id) REFERENCES Planning(planning_id) ON DELETE CASCADE
);

-- Table Facture (Pour la facturation de chaque service effectué)
CREATE TABLE Facture (
                         facture_id INT PRIMARY KEY AUTO_INCREMENT,
                         planning_detail_id INT NOT NULL,
                         reference_facture VARCHAR(30),
                         montant INT NOT NULL,
                         mode ENUM('Chèque', 'Espèce', 'Mobile Money', 'Virement'),
                         etablissemnt_payeur VARCHAR(50), -- Pour la chèque uniquement
                         numero_cheque VARCHAR(50) NULL,
                         date_paiement DATE NULL, -- Valide pour tous
                         date_traitement DATE NOT NULL,
                         etat ENUM('Payé', 'Non payé', 'À venir') DEFAULT 'Non payé',
                         axe ENUM ('Nord (N)', 'Sud (S)', 'Est (E)', 'Ouest (O)', 'Centre (C)') NOT NULL,
                         FOREIGN KEY (planning_detail_id) REFERENCES PlanningDetails(planning_detail_id) ON DELETE CASCADE
);

-- Historique des prix
CREATE TABLE Historique_prix (
    history_id INT AUTO_INCREMENT PRIMARY KEY,
    facture_id INT NOT NULL,
    old_amount INT NOT NULL,
    new_amount INT NOT NULL,
    change_date DATETIME NOT NULL,
    changed_by VARCHAR(255) DEFAULT 'System',
    FOREIGN KEY (facture_id) REFERENCES Facture(facture_id) ON DELETE CASCADE
);

-- Table Remarque (Pour confirmer si une traitement a été effectuée)
CREATE TABLE Remarque (
                          remarque_id INT PRIMARY KEY AUTO_INCREMENT,
                          client_id INT NOT NULL,
                          planning_detail_id INT NOT NULL,
                          facture_id INT,
                          contenu TEXT NOT NULL,
                          issue TEXT,
                          action TEXT NOT NULL,
                          date_remarque TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                          FOREIGN KEY (facture_id) REFERENCES Facture(facture_id) ON DELETE SET NULL,
                          FOREIGN KEY (client_id) REFERENCES Client(client_id) ON DELETE CASCADE,
                          FOREIGN KEY (planning_detail_id) REFERENCES PlanningDetails(planning_detail_id) ON DELETE CASCADE
);
/*
    contenu pour contenir les remarques effectués
    issue pour un cas isolé, en cas de problème ou erreur lors du traitement
    action pour contenire les actions entrepris à chaque traitement
*/
-- Table Signalement (Pour un signalement d'avancement ou de décalage)
CREATE TABLE Signalement (
                             signalement_id INT PRIMARY KEY AUTO_INCREMENT,
                             planning_detail_id INT NOT NULL,
                             motif TEXT NOT NULL,
                             type ENUM ('Avancement', 'Décalage') NOT NULL,
                             FOREIGN KEY (planning_detail_id) REFERENCES PlanningDetails(planning_detail_id) ON DELETE CASCADE
);


-- Table Historique (Historique des traitements effectués)
CREATE TABLE Historique (
                            historique_id INT PRIMARY KEY AUTO_INCREMENT,
                            facture_id INT NOT NULL,
                            planning_detail_id INT,
                            signalement_id INT,
                            date_historique TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            contenu TEXT NOT NULL,
                            issue TEXT,
                            action TEXT NOT NULL,
                            FOREIGN KEY (planning_detail_id) REFERENCES PlanningDetails(planning_detail_id) ON DELETE SET NULL,
                            FOREIGN KEY (signalement_id) REFERENCES Signalement(signalement_id) ON DELETE SET NULL,
                            FOREIGN KEY (facture_id) REFERENCES Facture(facture_id) ON DELETE CASCADE
);

/*
    Historique regroupe toutes les informations utiles pour chaque traitement effectué
    Modifié et corrigé le 18 Septembre 2025
*/
