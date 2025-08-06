from datetime import date
import aiomysql


async def obtenir_categories(pool, table_name: str, column_name: str) -> list[str]:
    """
    Récupère les valeurs d'une colonne ENUM spécifique.
    Cette fonction ne modifie pas la base de données, donc pas de transaction explicite.

    Args:
        pool: Le pool de connexions aiomysql.
        table_name (str): Le nom de la table contenant la colonne ENUM.
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
        print(f"Erreur lors de la récupération des catégories pour la table '{table_name}' et la colonne '{column_name}': {e}")
        return []
    finally:
        if conn:
            pool.release(conn)

async def create_client(pool, nom: str, prenom: str, email: str, telephone: str, adresse: str, nif: str, stat: str, categorie: str, axe: str) -> int | None:
    """
    Crée un nouveau client dans la base de données avec gestion de transaction.

    Args:
        pool: Le pool de connexions aiomysql.
        nom (str): Le nom du client.
        prenom (str): Le prénom du client.
        email (str): L'email du client.
        telephone (str): Le numéro de téléphone du client.
        adresse (str): L'adresse du client.
        nif (str): Le NIF du client.
        stat (str): Le STAT du client.
        categorie (str): La catégorie du client ('Particulier', 'Organisation', 'Société').
        axe (str): L'axe géographique du client.

    Returns:
        int | None: L'ID du client nouvellement créé, ou None en cas d'échec.
    """
    conn = None
    try:
        conn = await pool.acquire()
        await conn.begin()  # Début de la transaction
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO Client (nom, prenom, email, telephone, adresse, nif, stat, date_ajout, categorie, axe) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (nom, prenom, email, telephone, adresse, nif, stat, date.today(), categorie, axe)
            )
            await conn.commit()  # Validation de la transaction
            return cur.lastrowid
    except Exception as e:
        if conn:
            await conn.rollback()  # Annulation de la transaction en cas d'erreur
        print(f"Erreur lors de la création du client: {e}")
        return None
    finally:
        if conn:
            pool.release(conn)

async def read_client(pool, client_id: int | None = None) -> list[dict] | dict | None:
    """
    Lit les détails d'un client spécifique par ID ou de tous les clients.
    Cette fonction ne modifie pas la base de données, donc pas de transaction explicite.

    Args:
        pool: Le pool de connexions aiomysql.
        client_id (int | None): L'ID du client à lire (optionnel).

    Returns:
        list[dict] | dict | None: Une liste de dictionnaires pour tous les clients,
                                  un seul dictionnaire pour un client spécifique,
                                  ou None en cas d'erreur.
    """
    conn = None
    try:
        conn = await pool.acquire()
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            if client_id is None:
                await cursor.execute("SELECT * FROM Client")
                return await cursor.fetchall()
            else:
                await cursor.execute("SELECT * FROM Client WHERE client_id = %s", (client_id,))
                return await cursor.fetchone()
    except Exception as e:
        print(f"Erreur lors de la lecture du client/des clients: {e}")
        return None if client_id is not None else []
    finally:
        if conn:
            pool.release(conn)

async def update_client(pool, client_id: int, nom: str, prenom: str, email: str, telephone: str, adresse: str, nif: str, stat: str, categorie: str, axe: str) -> int:
    """
    Modifie un client existant dans la base de données avec gestion de transaction.

    Args:
        pool: Le pool de connexions aiomysql.
        client_id (int): L'ID du client à mettre à jour.
        nom (str): Le nouveau nom.
        prenom (str): Le nouveau prénom.
        email (str): Le nouvel email.
        telephone (str): Le nouveau téléphone.
        adresse (str): La nouvelle adresse.
        nif (str): Le nouveau NIF.
        stat (str): Le nouveau STAT.
        categorie (str): La nouvelle catégorie.
        axe (str): Le nouvel axe.

    Returns:
        int: Le nombre de lignes affectées (1 en cas de succès, 0 sinon).
    """
    conn = None
    try:
        conn = await pool.acquire()
        await conn.begin()
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE Client SET nom = %s, prenom = %s, email = %s, telephone = %s, adresse = %s, nif = %s, stat = %s, categorie = %s, axe = %s WHERE client_id = %s",
                (nom, prenom, email, telephone, adresse, nif, stat, categorie, axe, client_id)
            )
            await conn.commit()
            return cur.rowcount
    except Exception as e:
        if conn:
            await conn.rollback()
        print(f"Erreur lors de la mise à jour du client (ID: {client_id}): {e}")
        return 0
    finally:
        if conn:
            pool.release(conn)

async def delete_client(pool, client_id: int) -> int:
    """
    Supprime un client de la base de données avec gestion de transaction.

    Args:
        pool: Le pool de connexions aiomysql.
        client_id (int): L'ID du client à supprimer.

    Returns:
        int: Le nombre de lignes supprimées (1 en cas de succès, 0 sinon).
    """
    conn = None
    try:
        conn = await pool.acquire()
        await conn.begin()
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM Client WHERE client_id = %s", (client_id,))
            await conn.commit()
            return cur.rowcount
    except Exception as e:
        if conn:
            await conn.rollback()
        print(f"Erreur lors de la suppression du client (ID: {client_id}): {e}")
        return 0
    finally:
        if conn:
            pool.release(conn)
