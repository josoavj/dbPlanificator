import aiomysql
from datetime import date, datetime, timedelta


async def get_enum_values(pool, table_name: str, column_name: str) -> list[str]:
    """
    Récupère les valeurs d'une colonne ENUM d'une table spécifique.
    Cette fonction ne modifie pas la base de données, donc pas de transaction explicite.

    Args:
        pool: Le pool de connexions aiomysql.
        table_name (str): Le nom de la table.
        column_name (str): Le nom de la colonne ENUM.

    Returns:
        list[str]: Une liste des valeurs ENUM, ou une liste vide en cas d'erreur.
    """
    conn = None
    try:
        conn = await pool.acquire()
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            query = """
                SELECT COLUMN_TYPE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
            """
            await cursor.execute(query, (table_name, column_name))
            result = await cursor.fetchone()

            if result and 'COLUMN_TYPE' in result and result['COLUMN_TYPE'].startswith("enum("):
                enum_str = result['COLUMN_TYPE']
                enum_values = [val.strip("'") for val in enum_str[5:-1].split(',')]
                return enum_values
            return []
    except Exception as e:
        print(f"Erreur lors de la récupération des valeurs ENUM pour '{table_name}.{column_name}': {e}")
        return []
    finally:
        if conn:
            pool.release(conn)

async def create_planning(pool, traitement_id: int, redondance: str, date_debut_planification: date, duree_traitement: int = 12, unite_duree: str = 'mois') -> int | None:
    """
    Crée un planning pour un traitement donné avec gestion de transaction.

    Args:
        pool: Le pool de connexions aiomysql.
        traitement_id (int): L'ID du traitement associé.
        redondance (str): Le type de redondance du planning.
        date_debut_planification (date): La date de début de la planification.
        duree_traitement (int): La durée du traitement. Par défaut, 12.
        unite_duree (str): L'unité de la durée ('mois' ou 'années').

    Returns:
        int | None: L'ID du planning nouvellement créé, ou None en cas d'échec.
    """
    conn = None
    try:
        conn = await pool.acquire()
        await conn.begin()  # Début de la transaction
        async with conn.cursor() as cur:
            # Calculer la date de fin de la planification
            if unite_duree == 'mois':
                date_fin_planification = date_debut_planification + timedelta(days=duree_traitement * 30)
            elif unite_duree == 'années':
                date_fin_planification = date_debut_planification + timedelta(days=duree_traitement * 365)
            else:
                raise ValueError("Unité de durée non valide. Utilisez 'mois' ou 'années'.")

            await cur.execute("""
                INSERT INTO Planning (traitement_id, redondance, date_debut_planification, date_fin_planification, duree_traitement, unite_duree)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (traitement_id, redondance, date_debut_planification, date_fin_planification, duree_traitement, unite_duree))
            await conn.commit()  # Validation de la transaction
            return cur.lastrowid
    except ValueError as ve:
        if conn:
            await conn.rollback() # Annulation en cas d'erreur de valeur
        print(f"Erreur de valeur : {ve}")
        return None
    except Exception as e:
        if conn:
            await conn.rollback() # Annulation en cas d'autre erreur
        print(f"Erreur lors de la création du planning : {e}")
        return None
    finally:
        if conn:
            pool.release(conn)

async def read_planning(pool, planning_id: int | None = None) -> list[dict] | dict | None:
    """
    Lit un planning à partir de son ID ou tous les plannings.
    Cette fonction ne modifie pas la base de données, donc pas de transaction explicite.

    Args:
        pool: Le pool de connexions aiomysql.
        planning_id (int | None): L'ID du planning à lire (optionnel).

    Returns:
        list[dict] | dict | None: Une liste de dictionnaires si l'ID est None, un dictionnaire si l'ID est spécifié, ou None en cas d'erreur.
    """
    conn = None
    try:
        conn = await pool.acquire()
        async with conn.cursor(aiomysql.DictCursor) as cur:
            if planning_id is None:
                await cur.execute("SELECT * FROM Planning")
                return await cur.fetchall()
            else:
                await cur.execute("SELECT * FROM Planning WHERE planning_id = %s", (planning_id,))
                return await cur.fetchone()
    except Exception as e:
        print(f"Erreur lors de la lecture du planning : {e}")
        return None if planning_id is not None else []
    finally:
        if conn:
            pool.release(conn)

async def update_planning(pool, planning_id: int, traitement_id: int, redondance: str, date_debut_planification: date, duree_traitement: int, unite_duree: str) -> int:
    """
    Modifie un planning existant avec gestion de transaction.

    Args:
        pool: Le pool de connexions aiomysql.
        planning_id (int): L'ID du planning à modifier.
        traitement_id (int): Le nouvel ID du traitement.
        redondance (str): La nouvelle redondance.
        date_debut_planification (date): La nouvelle date de début de planification.
        duree_traitement (int): La nouvelle durée du traitement.
        unite_duree (str): La nouvelle unité de durée.

    Returns:
        int: Le nombre de lignes affectées (1 si succès, 0 sinon).
    """
    conn = None
    try:
        conn = await pool.acquire()
        await conn.begin()  # Début de la transaction
        async with conn.cursor() as cur:
            if unite_duree == 'mois':
                date_fin_planification = date_debut_planification + timedelta(days=duree_traitement * 30)
            elif unite_duree == 'années':
                date_fin_planification = date_debut_planification + timedelta(days=duree_traitement * 365)
            else:
                raise ValueError("Unité de durée non valide. Utilisez 'mois' ou 'années'.")

            await cur.execute("""
                UPDATE Planning SET traitement_id = %s, redondance = %s, date_debut_planification = %s, date_fin_planification = %s, duree_traitement = %s, unite_duree = %s
                WHERE planning_id = %s
            """, (traitement_id, redondance, date_debut_planification, date_fin_planification, duree_traitement, unite_duree, planning_id))
            await conn.commit()  # Validation de la transaction
            return cur.rowcount
    except ValueError as ve:
        if conn:
            await conn.rollback() # Annulation en cas d'erreur de valeur
        print(f"Erreur de valeur : {ve}")
        return 0
    except Exception as e:
        if conn:
            await conn.rollback() # Annulation en cas d'autre erreur
        print(f"Erreur lors de la mise à jour du planning : {e}")
        return 0
    finally:
        if conn:
            pool.release(conn)

async def delete_planning(pool, planning_id: int) -> int:
    """
    Supprime un planning à partir de son ID avec gestion de transaction.

    Args:
        pool: Le pool de connexions aiomysql.
        planning_id (int): L'ID du planning à supprimer.

    Returns:
        int: Le nombre de lignes supprimées (1 si succès, 0 sinon).
    """
    conn = None
    try:
        conn = await pool.acquire()
        await conn.begin()  # Début de la transaction
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM Planning WHERE planning_id = %s", (planning_id,))
            await conn.commit()  # Validation de la transaction
            return cur.rowcount
    except Exception as e:
        if conn:
            await conn.rollback()  # Annulation de la transaction en cas d'erreur
        print(f"Erreur lors de la suppression du planning : {e}")
        return 0
    finally:
        if conn:
            pool.release(conn)

"""
    Répartition des redondances pour les plannings :
    - Par semaine
    - Deux à trois fois par semaine (Toutes les semaines)
    - Deux fois par mois (Tous les 15 jours)
    - Par mois
    - Tous les deux mois
    - Tous les 4 mois
    - Tous les 6 mois 
"""