import aiomysql
from datetime import date


async def create_historique(pool, traitement_id: int, contenu: str, date_traitement: date | None = None) -> int | None:
    """
    Crée un historique pour un traitement donné avec gestion de transaction.

    Args:
        pool: Le pool de connexions aiomysql.
        traitement_id (int): L'ID du traitement associé.
        contenu (str): Le contenu de l'historique.
        date_traitement (date | None): La date du traitement. Par défaut, utilise la date d'aujourd'hui.

    Returns:
        int | None: L'ID de l'historique nouvellement créé, ou None en cas d'échec.
    """
    conn = None
    try:
        conn = await pool.acquire()
        await conn.begin()  # Début de la transaction
        async with conn.cursor() as cur:
            if date_traitement is None:
                date_traitement = date.today()
            await cur.execute(
                "INSERT INTO Historique (traitement_id, contenu, date_traitement) VALUES (%s, %s, %s)",
                (traitement_id, contenu, date_traitement)
            )
            await conn.commit()  # Validation de la transaction
            return cur.lastrowid
    except Exception as e:
        if conn:
            await conn.rollback()  # Annulation de la transaction en cas d'erreur
        print(f"Erreur lors de la création de l'historique : {e}")
        return None
    finally:
        if conn:
            pool.release(conn)


async def read_historique(pool, historique_id: int) -> dict | None:
    """
    Lit un historique à partir de son ID.
    Cette fonction ne modifie pas la base de données, donc pas de transaction explicite.

    Args:
        pool: Le pool de connexions aiomysql.
        historique_id (int): L'ID de l'historique à lire.

    Returns:
        dict | None: Un dictionnaire contenant les informations de l'historique, ou None si non trouvé ou en cas d'erreur.
    """
    conn = None
    try:
        conn = await pool.acquire()
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT * FROM Historique WHERE historique_id = %s", (historique_id,))
            return await cur.fetchone()
    except Exception as e:
        print(f"Erreur lors de la lecture de l'historique (ID: {historique_id}) : {e}")
        return None
    finally:
        if conn:
            pool.release(conn)


async def update_historique(pool, historique_id: int, contenu: str, date_traitement: date) -> int:
    """
    Modifie un historique existant avec gestion de transaction.

    Args:
        pool: Le pool de connexions aiomysql.
        historique_id (int): L'ID de l'historique à modifier.
        contenu (str): Le nouveau contenu de l'historique.
        date_traitement (date): La nouvelle date de traitement.

    Returns:
        int: Le nombre de lignes affectées (1 si succès, 0 sinon).
    """
    conn = None
    try:
        conn = await pool.acquire()
        await conn.begin()  # Début de la transaction
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE Historique SET contenu = %s, date_traitement = %s WHERE historique_id = %s",
                (contenu, date_traitement, historique_id)
            )
            await conn.commit()  # Validation de la transaction
            return cur.rowcount
    except Exception as e:
        if conn:
            await conn.rollback()  # Annulation de la transaction en cas d'erreur
        print(f"Erreur lors de la modification de l'historique (ID: {historique_id}) : {e}")
        return 0
    finally:
        if conn:
            pool.release(conn)


async def delete_historique(pool, historique_id: int) -> int:
    """
    Supprime un historique à partir de son ID avec gestion de transaction.

    Args:
        pool: Le pool de connexions aiomysql.
        historique_id (int): L'ID de l'historique à supprimer.

    Returns:
        int: Le nombre de lignes supprimées (1 si succès, 0 sinon).
    """
    conn = None
    try:
        conn = await pool.acquire()
        await conn.begin()  # Début de la transaction
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM Historique WHERE historique_id = %s", (historique_id,))
            await conn.commit()  # Validation de la transaction
            return cur.rowcount
    except Exception as e:
        if conn:
            await conn.rollback()  # Annulation de la transaction en cas d'erreur
        print(f"Erreur lors de la suppression de l'historique (ID: {historique_id}) : {e}")
        return 0
    finally:
        if conn:
            pool.release(conn)


async def get_historique_for_traitement(pool, traitement_id: int) -> list[dict]:
    """
    Récupère l'historique d'un traitement spécifique.
    Cette fonction ne modifie pas la base de données, donc pas de transaction explicite.

    Args:
        pool: Le pool de connexions aiomysql.
        traitement_id (int): L'ID du traitement.

    Returns:
        list[dict]: Une liste de dictionnaires, chaque dictionnaire représentant un historique.
    """
    conn = None
    try:
        conn = await pool.acquire()
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT * FROM Historique WHERE traitement_id = %s ORDER BY date_traitement DESC",
                              (traitement_id,))
            return await cur.fetchall()
    except Exception as e:
        print(f"Erreur lors de la récupération de l'historique pour le traitement ID {traitement_id} : {e}")
        return []
    finally:
        if conn:
            pool.release(conn)


async def create_historique_for_planning(pool, planning_id: int, contenu_specifique: str | None = None) -> bool:
    """
    Crée automatiquement un historique pour le traitement associé à un planning donné.
    Le contenu peut être spécifié ou généré par défaut.
    Cette fonction appelle 'create_historique' qui gère déjà sa propre transaction.

    Args:
        pool: Le pool de connexions aiomysql.
        planning_id (int): L'ID du planning.
        contenu_specifique (str | None): Le contenu à insérer. Si None, un contenu par défaut est généré.

    Returns:
        bool: True si l'historique a été créé avec succès, False sinon.
    """
    conn = None
    try:
        conn = await pool.acquire()
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT traitement_id FROM Planning WHERE planning_id = %s", (planning_id,))
            result = await cur.fetchone()
            if result:
                traitement_id = result['traitement_id']

                if contenu_specifique is None:
                    contenu = f"Historique généré automatiquement pour la planification du traitement {traitement_id}."
                else:
                    contenu = contenu_specifique

                success = await create_historique(pool, traitement_id, contenu)
                if success:
                    print(f"Historique créé pour le traitement {traitement_id} lié au planning {planning_id}.")
                    return True
                else:
                    print(f"Échec de la création de l'historique pour le traitement {traitement_id} lié au planning {planning_id}.")
                    return False
            else:
                print(f"Aucun traitement trouvé pour le planning ID {planning_id}.")
                return False
    except Exception as e:
        print(f"Erreur lors de la création automatique de l'historique pour le planning {planning_id} : {e}")
        return False
    finally:
        if conn:
            pool.release(conn)


async def afficher_historique_client(pool, client_id: int) -> None:
    """
    Affiche l'historique de tous les traitements d'un client.
    Cette fonction ne modifie pas la base de données, donc pas de transaction explicite.

    Args:
        pool: Le pool de connexions aiomysql.
        client_id (int): L'ID du client.
    """
    conn = None
    try:
        conn = await pool.acquire()
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("""
                              SELECT h.historique_id,
                                     h.traitement_id,
                                     h.contenu,
                                     h.date_traitement,
                                     t.id_type_traitement,
                                     tt.typeTraitement AS nom_type_traitement,
                                     c.contrat_id,
                                     cl.nom            AS nom_client,
                                     cl.prenom         AS prenom_client
                              FROM Historique h
                                       JOIN Traitement t ON h.traitement_id = t.traitement_id
                                       JOIN Contrat c ON t.contrat_id = c.contrat_id
                                       JOIN Client cl ON c.client_id = cl.client_id
                                       JOIN TypeTraitement tt ON t.id_type_traitement = tt.id_type_traitement
                              WHERE c.client_id = %s
                              ORDER BY h.date_traitement DESC
                              """, (client_id,))
            historiques = await cur.fetchall()

            if not historiques:
                print(f"Aucun historique trouvé pour le client ID {client_id}.")
                return

            print(
                f"\n--- Historique des traitements pour le client ID {client_id} ({historiques[0]['nom_client']} {historiques[0]['prenom_client']}) ---")
            for historique in historiques:
                print("-" * 30)
                print(f"ID Historique: {historique['historique_id']}")
                print(f"ID Traitement: {historique['traitement_id']} (Type: {historique['nom_type_traitement']})")
                print(f"Contenu: {historique['contenu']}")
                print(f"Date Traitement: {historique['date_traitement']}")
                print(f"ID Contrat: {historique['contrat_id']}")
            print("-" * 30)

    except Exception as e:
        print(f"Erreur lors de l'affichage de l'historique du client ID {client_id} : {e}")
    finally:
        if conn:
            pool.release(conn)
