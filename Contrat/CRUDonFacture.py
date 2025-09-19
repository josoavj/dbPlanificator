from datetime import date
import aiomysql

async def create_facture(pool, traitement_id: int, montant: float, date_traitement: date, axe: str, remarque: str | None) -> int | None:
    """
    Crée une nouvelle facture dans la base de données avec gestion de transaction.

    Args:
        pool: Le pool de connexions aiomysql.
        traitement_id (int): L'ID du traitement associé.
        montant (float): Le montant de la facture.
        date_traitement (date): La date du traitement.
        axe (str): L'axe géographique.
        remarque (str | None): Une remarque sur la facture (peut être None).

    Returns:
        int | None: L'ID de la facture nouvellement créée, ou None en cas d'échec.
    """
    conn = None
    try:
        conn = await pool.acquire()
        await conn.begin()  # Début de la transaction
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO Facture (traitement_id, montant, date_traitement, axe, remarque) VALUES (%s, %s, %s, %s, %s)",
                (traitement_id, montant, date_traitement, axe, remarque)
            )
            await conn.commit()  # Validation de la transaction
            return cur.lastrowid
    except Exception as e:
        if conn:
            await conn.rollback()  # Annulation de la transaction en cas d'erreur
        print(f"Erreur lors de la création de la facture: {e}")
        return None
    finally:
        if conn:
            pool.release(conn)

async def read_facture(pool, facture_id: int | None = None) -> list[dict] | dict | None:
    """
    Lit les détails d'une facture spécifique par ID ou de toutes les factures.
    Cette fonction ne modifie pas la base de données, donc pas de transaction explicite.

    Args:
        pool: Le pool de connexions aiomysql.
        facture_id (int | None): L'ID de la facture à lire (optionnel).

    Returns:
        list[dict] | dict | None: Une liste de dictionnaires pour toutes les factures,
                                  un seul dictionnaire pour une facture spécifique,
                                  ou None en cas d'erreur.
    """
    conn = None
    try:
        conn = await pool.acquire()
        async with conn.cursor(aiomysql.DictCursor) as cur:
            if facture_id is None:
                await cur.execute("SELECT * FROM Facture")
                return await cur.fetchall()
            else:
                await cur.execute("SELECT * FROM Facture WHERE facture_id = %s", (facture_id,))
                return await cur.fetchone()
    except Exception as e:
        print(f"Erreur lors de la lecture de la facture/des factures: {e}")
        return None if facture_id is not None else []
    finally:
        if conn:
            pool.release(conn)

async def update_facture(pool, facture_id: int, traitement_id: int, montant: float, date_traitement: date, axe: str, remarque: str | None) -> int:
    """
    Modifie une facture existante dans la base de données avec gestion de transaction.

    Args:
        pool: Le pool de connexions aiomysql.
        facture_id (int): L'ID de la facture à modifier.
        traitement_id (int): Le nouvel ID du traitement.
        montant (float): Le nouveau montant.
        date_traitement (date): La nouvelle date du traitement.
        axe (str): Le nouvel axe.
        remarque (str | None): La nouvelle remarque.

    Returns:
        int: Le nombre de lignes affectées (1 en cas de succès, 0 sinon).
    """
    conn = None
    try:
        conn = await pool.acquire()
        await conn.begin()  # Début de la transaction
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE Facture SET traitement_id = %s, montant = %s, date_traitement = %s, axe = %s, remarque = %s WHERE facture_id = %s",
                (traitement_id, montant, date_traitement, axe, remarque, facture_id)
            )
            await conn.commit()  # Validation de la transaction
            return cur.rowcount
    except Exception as e:
        if conn:
            await conn.rollback()  # Annulation de la transaction en cas d'erreur
        print(f"Erreur lors de la mise à jour de la facture (ID: {facture_id}): {e}")
        return 0
    finally:
        if conn:
            pool.release(conn)

async def delete_facture(pool, facture_id: int) -> int:
    """
    Supprime une facture de la base de données avec gestion de transaction.

    Args:
        pool: Le pool de connexions aiomysql.
        facture_id (int): L'ID de la facture à supprimer.

    Returns:
        int: Le nombre de lignes supprimées (1 en cas de succès, 0 sinon).
    """
    conn = None
    try:
        conn = await pool.acquire()
        await conn.begin()  # Début de la transaction
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM Facture WHERE facture_id = %s", (facture_id,))
            await conn.commit()  # Validation de la transaction
            return cur.rowcount
    except Exception as e:
        if conn:
            await conn.rollback()  # Annulation de la transaction en cas d'erreur
        print(f"Erreur lors de la suppression de la facture (ID: {facture_id}): {e}")
        return 0
    finally:
        if conn:
            pool.release(conn)

async def obtenir_axe_contrat(pool, contrat_id: int) -> str | None:
    """
    Récupère l'axe géographique associé au client d'un contrat donné.
    Cette fonction ne modifie pas la base de données, donc pas de transaction explicite.

    Args:
        pool: Le pool de connexions aiomysql.
        contrat_id (int): L'ID du contrat.

    Returns:
        str | None: La valeur de l'axe du client, ou None si non trouvé ou en cas d'erreur.
    """
    conn = None
    try:
        conn = await pool.acquire()
        async with conn.cursor(aiomysql.DictCursor) as cursor: # Utilisation de DictCursor
            await cursor.execute("""
                SELECT cl.axe
                FROM Contrat c
                JOIN Client cl ON c.client_id = cl.client_id
                WHERE c.contrat_id = %s
            """, (contrat_id,))
            resultat = await cursor.fetchone()
            if resultat:
                return resultat['axe'] # Accès par clé de dictionnaire
            else:
                return None
    except Exception as e:
        print(f"Erreur lors de la récupération de l'axe du client pour contrat (ID: {contrat_id}) : {e}")
        return None
    finally:
        if conn:
            pool.release(conn)


"""
    Répartition de la facturation :
    - Une facture pour chaque traitement en géneral
    - Possibilité d'assigner une seule facture pour deux ou plusieurs traitements
"""