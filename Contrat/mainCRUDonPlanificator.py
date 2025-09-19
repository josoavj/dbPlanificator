import asyncio
from datetime import datetime
import sys

import aiomysql
from aiomysql import DictCursor

from Contrat.CRUDonClient import (
    create_client,
    read_client,
    update_client,
    delete_client,
)
from Contrat.CRUDonContrat import (
    create_contrat,
    read_contrat,
    update_contrat,
    delete_contrat,
)
from Contrat.CRUDonFacture import obtenir_axe_contrat
from Contrat.CRUDonTraitement import (
    creation_traitement,
    obtenir_types_traitement,
    read_traitement,
    update_traitement,
    delete_traitement,
)
from Contrat.CRUDonPlanning import (
    create_planning,
    read_planning,
    update_planning,
    delete_planning,
)

from Contrat.CRUDonSignalement import (
    create_signalement,
    read_signalement,
    update_signalement,
    delete_signalement,
)

from Contrat.fonctionnalités.Facture.gestionFacture import (
    create_facture,
    get_facture_details,
    update_facture_montant_and_status,
    delete_facture,
    get_all_factures_for_client,
)


# Fonction utilitaire manquante pour obtenir les valeurs d'ENUM
async def get_enum_values(pool, table_name: str, column_name: str):
    """
    Récupère les valeurs possibles pour une colonne de type ENUM d'une table donnée.
    """
    async with pool.acquire() as conn:
        async with conn.cursor(DictCursor) as cursor:
            query = f"""
                SELECT COLUMN_TYPE
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s;
            """
            await cursor.execute(query, (table_name, column_name))
            result = await cursor.fetchone()

            if result and 'COLUMN_TYPE' in result:
                enum_type = result['COLUMN_TYPE']
                values = [v.strip("'") for v in enum_type[5:-1].split(',')]
                return values
            return []


async def main():
    pool = None
    try:
        # Configuration de la connexion à la base de données
        host = input("Hôte de la base de données (par défaut : localhost) : ") or "localhost"
        port_str = input("Port de la base de données (par défaut : 3306) : ") or "3306"
        port = int(port_str) if port_str.isdigit() else 3306
        user = input("Nom d'utilisateur : ")
        password = input("Mot de passe : ")
        database = input("Nom de la base de données : ")

        # Création du pool de connexion
        pool = await aiomysql.create_pool(
            host=host,
            port=port,
            user=user,
            password=password,
            db=database,
            autocommit=True
        )

        # Récupération des valeurs ENUM au début du script
        categories_client = await get_enum_values(pool, "Client", "categorie")
        categories_contrat_duree = await get_enum_values(pool, "Contrat", "duree_contrat")
        categories_contrat_type = await get_enum_values(pool, "Contrat", "categorie")
        types_traitement_data = await obtenir_types_traitement(pool)
        types_traitement_names = [t['typeTraitement'] for t in types_traitement_data if 'typeTraitement' in t]
        types_traitement_map = {t['typeTraitement']: t['id_type_traitement'] for t in types_traitement_data if
                                'typeTraitement' in t and 'id_type_traitement' in t}
        redondances = await get_enum_values(pool, "Planning", "redondance")
        etats_facture = await get_enum_values(pool, "Facture", "etat")
        # Cette ligne était manquante, ajoutée pour la gestion des factures
        axes_facture = await get_enum_values(pool, "Facture", "axe")

        while True:
            print("\n--- Menu Principal ---")
            print("1. Gérer les Clients")
            print("2. Gérer les Contrats")
            print("3. Gérer les Traitements")
            print("4. Gérer les Plannings")
            print("5. Gérer les Factures")
            print("6. Gérer les Signalements")
            print("7. Quitter")

            choix_table = input("Choisissez une table (1-7) : ").strip()
            if choix_table == '7':
                print("Exiting...")
                break

            table_functions = {
                '1': {'create': create_client, 'read': read_client, 'update': update_client, 'delete': delete_client,
                      'name': "Client"},
                '2': {'create': create_contrat, 'read': read_contrat, 'update': update_contrat,
                      'delete': delete_contrat, 'name': "Contrat"},
                '3': {'create': creation_traitement, 'read': read_traitement, 'update': update_traitement,
                      'delete': delete_traitement, 'name': "Traitement"},
                '4': {'create': create_planning, 'read': read_planning, 'update': update_planning,
                      'delete': delete_planning, 'name': "Planning"},
                '5': {'create': create_facture, 'read': get_facture_details,
                      'update': update_facture_montant_and_status, 'delete': delete_facture, 'name': "Facture"},
                '6': {'create': create_signalement, 'read': read_signalement, 'update': update_signalement,
                      'delete': delete_signalement, 'name': "Signalement"},
            }

            if choix_table not in table_functions:
                print("Choix de table invalide.")
                continue

            table_name = table_functions[choix_table]['name']

            while True:
                if table_name == "Facture":
                    print(f"\n--- Opérations pour {table_name} ---")
                    print("1. Créer une facture")
                    print("2. Lire les détails d'une facture (par ID)")
                    print("3. Modifier le montant et/ou le statut d'une facture")
                    print("4. Supprimer une facture")
                    print("5. Afficher toutes les factures pour un client")
                    print("6. Générer une facture Excel pour un client")
                    print("7. Retour au menu principal")
                    choix_operation = input("Choisissez une opération (1-7) : ").strip()

                    if choix_operation == '7':
                        break
                    elif choix_operation == '1':
                        try:
                            contrat_id = int(input("ID du contrat pour lequel facturer les traitements : ").strip())
                            async with pool.acquire() as conn:
                                async with conn.cursor(DictCursor) as cursor:
                                    await cursor.execute(
                                        "SELECT t.traitement_id, t.id_type_traitement FROM Traitement t WHERE t.contrat_id = %s",
                                        (contrat_id,))
                                    traitements = await cursor.fetchall()
                            if not traitements:
                                print("Aucun traitement trouvé pour ce contrat. Impossible de créer des factures.")
                                continue

                            print("\nTraitements disponibles pour ce contrat:")
                            for i, t_info in enumerate(traitements):
                                type_name = next((name for name, id_val in types_traitement_map.items() if
                                                  id_val == t_info['id_type_traitement']), "Inconnu")
                                print(f"{i + 1}. Traitement ID: {t_info['traitement_id']} (Type: {type_name})")

                            selected_traitement_id = None
                            while True:
                                try:
                                    choice = input("Sélectionnez le numéro du traitement pour la facture : ").strip()
                                    if choice.isdigit() and 1 <= int(choice) <= len(traitements):
                                        selected_traitement_id = traitements[int(choice) - 1]['traitement_id']
                                        break
                                    else:
                                        print("Choix invalide.")
                                except ValueError:
                                    print("Entrée invalide. Veuillez entrer un numéro.")

                            if not selected_traitement_id:
                                print("Aucun traitement sélectionné. Annulation de la création de facture.")
                                continue

                            planning_details_for_treatment = []
                            async with pool.acquire() as conn:
                                async with conn.cursor(DictCursor) as cursor:
                                    await cursor.execute("""
                                                         SELECT pd.planning_detail_id, pd.date_planification, pd.statut
                                                         FROM PlanningDetails pd
                                                                  JOIN Planning p ON pd.planning_id = p.planning_id
                                                         WHERE p.traitement_id = %s
                                                         ORDER BY pd.date_planification DESC
                                                         """, (selected_traitement_id,))
                                    planning_details_for_treatment = await cursor.fetchall()

                            if not planning_details_for_treatment:
                                print(
                                    f"Aucun détail de planification trouvé pour le traitement ID {selected_traitement_id}. Impossible de créer une facture.")
                                continue

                            print("\nDétails de planification disponibles pour ce traitement:")
                            for i, pd_info in enumerate(planning_details_for_treatment):
                                print(
                                    f"{i + 1}. Planning Detail ID: {pd_info['planning_detail_id']} (Date: {pd_info['date_planification']}, Statut: {pd_info['statut']})")

                            selected_planning_detail_id = None
                            selected_date_traitement = None
                            while True:
                                try:
                                    choice = input(
                                        "Sélectionnez le numéro du détail de planification pour la facture : ").strip()
                                    if choice.isdigit() and 1 <= int(choice) <= len(planning_details_for_treatment):
                                        selected_planning_detail_id = planning_details_for_treatment[int(choice) - 1][
                                            'planning_detail_id']
                                        selected_date_traitement = planning_details_for_treatment[int(choice) - 1][
                                            'date_planification']
                                        break
                                    else:
                                        print("Choix invalide.")
                                except ValueError:
                                    print("Entrée invalide. Veuillez entrer un numéro.")

                            if not selected_planning_detail_id:
                                print(
                                    "Aucun détail de planification sélectionné. Annulation de la création de facture.")
                                continue

                            montant = float(input("Montant de la facture : ").strip())
                            remarque = input("Remarque (facultatif) : ").strip() or None
                            axe_contrat = await obtenir_axe_contrat(pool, contrat_id)

                            if not axe_contrat:
                                print(
                                    "Impossible de récupérer l'axe du contrat. La création de la facture pourrait être incomplète.")
                                axe_contrat = "N/A"

                            result_id = await create_facture(pool, selected_planning_detail_id, montant,
                                                             selected_date_traitement, axe_contrat, remarque)
                            print(f"Facture créée avec l'ID : {result_id}")

                        except ValueError as ve:
                            print(f"Erreur d'entrée : {ve}. Assurez-vous d'entrer des numéros valides.")
                        except Exception as e:
                            print(f"Une erreur est survenue lors de la création de la facture : {e}")

                    elif choix_operation == '2':
                        try:
                            facture_id = int(input("ID de la facture à lire : ").strip())
                            result = await get_facture_details(pool, facture_id)
                            if result:
                                print("\n--- Détails de la Facture ---")
                                for key, value in result.items():
                                    print(f"{key}: {value}")
                            else:
                                print(f"Aucune facture trouvée avec l'ID {facture_id}.")
                        except ValueError:
                            print("Entrée invalide. Veuillez entrer un numéro.")

                    elif choix_operation == '3':
                        try:
                            facture_id = int(input("ID de la facture à modifier : ").strip())
                            existing_facture = await get_facture_details(pool, facture_id)
                            if not existing_facture:
                                print(f"Aucune facture trouvée avec l'ID {facture_id}.")
                                continue

                            new_montant_str = input(
                                f"Nouveau montant ({existing_facture.get('montant', 'N/A')}), laissez vide pour garder l'actuel) : ").strip()
                            new_montant = float(new_montant_str) if new_montant_str else existing_facture.get('montant')

                            print("États de facture disponibles:")
                            for i, etat in enumerate(etats_facture):
                                print(f"{i + 1}. {etat}")
                            current_status_name = existing_facture.get('etat')
                            new_status_name = current_status_name

                            while True:
                                status_choice_str = input(
                                    f"Nouvel état ({current_status_name}), entrez le numéro ou Entrée pour garder l'actuel) : ").strip()
                                if not status_choice_str:
                                    break  # Keep the current status
                                try:
                                    choice_idx = int(status_choice_str) - 1
                                    if 0 <= choice_idx < len(etats_facture):
                                        new_status_name = etats_facture[choice_idx]
                                        break
                                    else:
                                        print("Choix invalide. Veuillez réessayer.")
                                except ValueError:
                                    print("Entrée invalide. Veuillez entrer un numéro.")

                            if await update_facture_montant_and_status(pool, facture_id, new_montant, new_status_name):
                                print(f"Facture ID {facture_id} mise à jour avec succès.")
                            else:
                                print(f"Échec de la mise à jour de la facture ID {facture_id}.")
                        except ValueError:
                            print("Entrée invalide. Veuillez entrer un numéro.")

                    elif choix_operation == '4':
                        try:
                            facture_id = int(input("ID de la facture à supprimer : ").strip())
                            if await delete_facture(pool, facture_id):
                                print(f"Facture ID {facture_id} supprimée avec succès.")
                            else:
                                print(f"Échec de la suppression de la facture ID {facture_id}.")
                        except ValueError:
                            print("Entrée invalide. Veuillez entrer un numéro.")

                    elif choix_operation == '5':
                        try:
                            client_id = int(input("ID du client pour afficher toutes les factures : ").strip())
                            all_factures = await get_all_factures_for_client(pool, client_id)
                            if all_factures:
                                print(f"\n--- Toutes les Factures pour le Client ID {client_id} ---")
                                for facture in all_factures:
                                    print("-" * 30)
                                    for key, value in facture.items():
                                        print(f"{key}: {value}")
                                print("-" * 30)
                            else:
                                print(f"Aucune facture trouvée pour le client ID {client_id}.")
                        except ValueError:
                            print("Entrée invalide. Veuillez entrer un numéro.")

                    elif choix_operation == '6':
                        try:
                            client_id = int(input("ID du client pour générer la facture Excel : ").strip())
                            mois_str = input("Mois de la facture (MM, ex: 01 pour Janvier) : ").strip()
                            annee_str = input("Année de la facture (AAAA, ex: 2023) : ").strip()
                            if not mois_str.isdigit() or not annee_str.isdigit() or not (
                                    1 <= int(mois_str) <= 12) or len(annee_str) != 4:
                                print(
                                    "Mois ou année invalide. Veuillez entrer un mois (MM) entre 01 et 12 et une année (AAAA) à quatre chiffres.")
                                continue
                            mois = int(mois_str)
                            annee = int(annee_str)
                            print("La fonction de génération de rapport Excel n'est pas implémentée dans ce script.")
                        except ValueError:
                            print("Entrée invalide. Veuillez entrer des numéros valides.")
                        except ImportError:
                            print("Le module 'Rapports.export_excel' n'a pas pu être importé.")
                    else:
                        print("Choix d'opération invalide pour Facture.")
                    continue

                # Partie du menu pour les autres tables
                print(f"\n--- Opérations pour {table_name} ---")
                print("1. Créer")
                print("2. Lire")
                print("3. Modifier")
                print("4. Supprimer")
                print("5. Retour au menu principal")
                choix_operation = input("Choisissez une opération (1-5) : ").strip()
                if choix_operation == '5':
                    break
                if choix_operation not in ('1', '2', '3', '4'):
                    print("Choix d'opération invalide.")
                    continue

                operation_key = ['create', 'read', 'update', 'delete'][int(choix_operation) - 1]
                func = table_functions[choix_table][operation_key]

                try:
                    if operation_key == 'create':
                        if table_name == "Client":
                            nom = input("Nom : ").strip()
                            prenom, nif, stat = None, None, None
                            axe = input("Axe : ").strip()
                            print("Catégories disponibles:")
                            for i, cat in enumerate(categories_client): print(f"{i + 1}. {cat}")
                            choix = int(input("Choisissez une catégorie (entrez le numéro): ").strip()) - 1
                            categorie_choisie = categories_client[choix]
                            if categorie_choisie == "Particulier":
                                prenom = input("Prénom (facultatif) : ").strip() or None
                            elif categorie_choisie == "Société":
                                prenom = input("Responsable : ").strip() or None
                                nif = input("NIF (Numéro d'Immatriculation Fiscale): ").strip() or None
                                stat = input("Stat: ").strip() or None
                            else:
                                prenom = input("Responsable : ").strip() or None
                            email = input("Email : ").strip()
                            telephone = input("Téléphone : ").strip()
                            adresse = input("Adresse : ").strip()
                            result_id = await func(pool, nom, prenom, email, telephone, adresse, categorie_choisie, nif,
                                                   stat, axe)
                            print(f"{table_name} créé avec l'ID : {result_id}")
                        elif table_name == "Contrat":
                            client_id = int(input("ID du client : ").strip())
                            date_contrat_str = input("Date du contrat (AAAA-MM-JJ) : ").strip()
                            date_contrat = datetime.strptime(date_contrat_str, '%Y-%m-%d').date()
                            date_debut_str = input("Date de début (AAAA-MM-JJ) : ").strip()
                            date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
                            print("Catégories de durée disponibles:")
                            for i, cat in enumerate(categories_contrat_duree): print(f"{i + 1}. {cat}")
                            choix = int(input("Choisissez une catégorie de durée (entrez le numéro): ").strip()) - 1
                            duree_contrat_choisie = categories_contrat_duree[choix]
                            date_fin_contrat, duree_contrat_mois = None, None
                            if duree_contrat_choisie == "Déterminée":
                                date_fin_contrat_str = input("Date de fin (AAAA-MM-JJ) : ").strip()
                                date_fin_contrat = datetime.strptime(date_fin_contrat_str, '%Y-%m-%d').date()
                                duree_contrat_mois = int(input("Durée du contrat en mois : ").strip())
                            print("Catégories de type disponibles:")
                            for i, cat in enumerate(categories_contrat_type): print(f"{i + 1}. {cat}")
                            choix = int(input("Choisissez une catégorie de type (entrez le numéro): ").strip()) - 1
                            categorie_contrat_choisie = categories_contrat_type[choix]
                            result_id = await func(pool, client_id, date_contrat, date_debut, duree_contrat_choisie,
                                                   categorie_contrat_choisie, date_fin_contrat, duree_contrat_mois)
                            print(f"{table_name} créé avec l'ID : {result_id}")
                        elif table_name == "Traitement":
                            contrat_id = int(input("ID du contrat : ").strip())
                            if not types_traitement_names:
                                print("Aucun type de traitement trouvé. Impossible de créer un traitement.")
                                continue
                            print("Types de traitement disponibles:")
                            for i, tt_name in enumerate(types_traitement_names): print(f"{i + 1}. {tt_name}")
                            choix_str = input(
                                "Choisissez les types de traitement (numéros séparés par des virgules) : ").strip()
                            choix_list = [int(c.strip()) - 1 for c in choix_str.split(',') if c.strip()]
                            for c_idx in choix_list:
                                selected_type_name = types_traitement_names[c_idx]
                                id_type_traitement_chosen = types_traitement_map[selected_type_name]
                                result_id = await func(pool, contrat_id, id_type_traitement_chosen)
                                print(
                                    f"Traitement créé avec l'ID : {result_id} pour le type de traitement ID {id_type_traitement_chosen}")
                        elif table_name == "Planning":
                            traitement_id = int(input("ID du traitement : ").strip())
                            date_debut_planification_str = input(
                                "Date de début de planification (AAAA-MM-JJ) : ").strip()
                            date_debut_planification = datetime.strptime(date_debut_planification_str,
                                                                         '%Y-%m-%d').date()
                            print("Options de redondance disponibles:")
                            for i, red in enumerate(redondances): print(f"{i + 1}. {red}")
                            choix_red = int(
                                input("Choisissez une option de redondance (entrez le numéro): ").strip()) - 1
                            redondance_choisie = redondances[choix_red]
                            duree_traitement = int(input("Durée du traitement : ").strip())
                            unite_duree = input("Unité de la durée ('mois' ou 'années') : ").strip()
                            result_id = await func(pool, traitement_id, redondance_choisie, date_debut_planification,
                                                   duree_traitement, unite_duree)
                            print(f"Planning créé avec l'ID : {result_id}")
                        elif table_name == "Signalement":
                            planning_detail_id = int(input("ID du détail de planification : ").strip())
                            motif = input("Motif : ").strip()
                            type_signalement = input("Type de signalement : ").strip()
                            result_id = await func(pool, planning_detail_id, motif, type_signalement)
                            print(f"{table_name} créé avec l'ID : {result_id}")

                    elif operation_key == 'read':
                        if table_name == "Client":
                            client_id = input("ID du client à lire (laissez vide pour tous) : ").strip()
                            result = await func(pool, int(client_id) if client_id else None)
                            if isinstance(result, list):
                                for r in result: print(r)
                            elif result:
                                print(result)
                            else:
                                print("Aucun client trouvé.")
                        elif table_name == "Contrat":
                            contrat_id = input("ID du contrat à lire (laissez vide pour tous) : ").strip()
                            result = await func(pool, int(contrat_id) if contrat_id else None)
                            if isinstance(result, list):
                                for r in result: print(r)
                            elif result:
                                print(result)
                            else:
                                print("Aucun contrat trouvé.")
                        elif table_name == "Traitement":
                            traitement_id = input("ID du traitement à lire (laissez vide pour tous) : ").strip()
                            result = await func(pool, int(traitement_id) if traitement_id else None)
                            if isinstance(result, list):
                                for r in result: print(r)
                            elif result:
                                print(result)
                            else:
                                print("Aucun traitement trouvé.")
                        elif table_name == "Planning":
                            planning_id = input("ID du planning à lire (laissez vide pour tous) : ").strip()
                            result = await func(pool, int(planning_id) if planning_id else None)
                            if isinstance(result, list):
                                for r in result: print(r)
                            elif result:
                                print(result)
                            else:
                                print("Aucun planning trouvé.")
                        elif table_name == "Signalement":
                            signalement_id = input("ID du signalement à lire (laissez vide pour tous) : ").strip()
                            result = await func(pool, int(signalement_id) if signalement_id else None)
                            if isinstance(result, list):
                                for r in result: print(r)
                            elif result:
                                print(result)
                            else:
                                print("Aucun signalement trouvé.")

                    elif operation_key == 'update':
                        if table_name == "Client":
                            client_id = int(input("ID du client à modifier : ").strip())
                            nom = input("Nom : ").strip()
                            prenom = input("Prénom : ").strip()
                            email = input("Email : ").strip()
                            telephone = input("Téléphone : ").strip()
                            adresse = input("Adresse : ").strip()
                            print("Catégories disponibles:")
                            for i, cat in enumerate(categories_client): print(f"{i + 1}. {cat}")
                            choix = int(input("Choisissez une catégorie (entrez le numéro): ").strip()) - 1
                            categorie_choisie = categories_client[choix]
                            nif = input("NIF (facultatif) : ").strip() or None
                            stat = input("Stat (facultatif) : ").strip() or None
                            axe = input("Axe : ").strip()
                            rows = await func(pool, client_id, nom, prenom, email, telephone, adresse,
                                              categorie_choisie, nif, stat, axe)
                            print(f"{rows} ligne(s) modifiée(s).")
                        elif table_name == "Contrat":
                            contrat_id = int(input("ID du contrat à modifier : ").strip())
                            client_id = int(input("ID du client : ").strip())
                            date_contrat_str = input("Date du contrat (AAAA-MM-JJ) : ").strip()
                            date_contrat = datetime.strptime(date_contrat_str, '%Y-%m-%d').date()
                            date_debut_str = input("Date de début (AAAA-MM-JJ) : ").strip()
                            date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
                            date_fin_str = input("Date de fin (AAAA-MM-JJ) : ").strip()
                            date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
                            duree_contrat_mois = int(input("Durée en mois : ").strip())
                            print("Catégories de durée disponibles:")
                            for i, cat in enumerate(categories_contrat_duree): print(f"{i + 1}. {cat}")
                            choix_duree = int(
                                input("Choisissez une catégorie de durée (entrez le numéro): ").strip()) - 1
                            duree_contrat_choisie = categories_contrat_duree[choix_duree]
                            print("Catégories de type disponibles:")
                            for i, cat in enumerate(categories_contrat_type): print(f"{i + 1}. {cat}")
                            choix_type = int(input("Choisissez une catégorie de type (entrez le numéro): ").strip()) - 1
                            categorie_choisie = categories_contrat_type[choix_type]
                            rows = await func(pool, contrat_id, client_id, date_contrat, date_debut, date_fin,
                                              duree_contrat_choisie, categorie_choisie, duree_contrat_mois)
                            print(f"{rows} ligne(s) modifiée(s).")
                        elif table_name == "Traitement":
                            traitement_id = int(input("ID du traitement à modifier : ").strip())
                            contrat_id = int(input("ID du contrat : ").strip())
                            print("Types de traitement disponibles:")
                            for i, tt_name in enumerate(types_traitement_names): print(f"{i + 1}. {tt_name}")
                            choix = int(input("Choisissez un type de traitement (entrez le numéro) : ").strip()) - 1
                            selected_type_name = types_traitement_names[choix]
                            id_type_traitement_chosen = types_traitement_map[selected_type_name]
                            rows = await func(pool, traitement_id, contrat_id, id_type_traitement_chosen)
                            print(f"{rows} ligne(s) modifiée(s).")
                        elif table_name == "Planning":
                            planning_id = int(input("ID du planning à modifier : ").strip())
                            traitement_id = int(input("ID du traitement : ").strip())
                            print("Options de redondance disponibles:")
                            for i, red in enumerate(redondances): print(f"{i + 1}. {red}")
                            choix_red = int(
                                input("Choisissez une option de redondance (entrez le numéro): ").strip()) - 1
                            redondance_choisie = redondances[choix_red]
                            date_debut_planification_str = input(
                                "Date de début de planification (AAAA-MM-JJ) : ").strip()
                            date_debut_planification = datetime.strptime(date_debut_planification_str,
                                                                         '%Y-%m-%d').date()
                            duree_traitement = int(input("Durée du traitement : ").strip())
                            unite_duree = input("Unité de la durée ('mois' ou 'années') : ").strip()
                            rows = await func(pool, planning_id, traitement_id, redondance_choisie,
                                              date_debut_planification, duree_traitement, unite_duree)
                            print(f"{rows} ligne(s) modifiée(s).")
                        elif table_name == "Signalement":
                            signalement_id = int(input("ID du signalement à modifier : ").strip())
                            planning_detail_id = int(input("ID du détail de planification : ").strip())
                            motif = input("Motif : ").strip()
                            type_signalement = input("Type de signalement : ").strip()
                            rows = await func(pool, signalement_id, planning_detail_id, motif, type_signalement)
                            print(f"{rows} ligne(s) modifiée(s).")

                    elif operation_key == 'delete':
                        if table_name == "Client":
                            client_id = int(input("ID du client à supprimer : ").strip())
                            rows = await func(pool, client_id)
                            print(f"{rows} ligne(s) supprimée(s).")
                        elif table_name == "Contrat":
                            contrat_id = int(input("ID du contrat à supprimer : ").strip())
                            rows = await func(pool, contrat_id)
                            print(f"{rows} ligne(s) supprimée(s).")
                        elif table_name == "Traitement":
                            traitement_id = int(input("ID du traitement à supprimer : ").strip())
                            rows = await func(pool, traitement_id)
                            print(f"{rows} ligne(s) supprimée(s).")
                        elif table_name == "Planning":
                            planning_id = int(input("ID du planning à supprimer : ").strip())
                            rows = await func(pool, planning_id)
                            print(f"{rows} ligne(s) supprimée(s).")
                        elif table_name == "Signalement":
                            signalement_id = int(input("ID du signalement à supprimer : ").strip())
                            rows = await func(pool, signalement_id)
                            print(f"{rows} ligne(s) supprimée(s).")

                except ValueError as ve:
                    print(f"Erreur d'entrée : {ve}. Assurez-vous d'entrer des numéros et des dates valides.")
                except IndexError:
                    print("Choix invalide. Veuillez sélectionner un numéro de la liste.")
                except Exception as e:
                    print(f"Une erreur est survenue lors de l'opération : {e}")

    except aiomysql.Error as e:
        print(f"Erreur de connexion à la base de données : {e}", file=sys.stderr)
    except Exception as e:
        print(f"Une erreur inattendue est survenue : {e}", file=sys.stderr)
    finally:
        if pool:
            pool.close()
            await pool.wait_closed()
            print("Connexion à la base de données fermée.")


if __name__ == "__main__":
    asyncio.run(main())
