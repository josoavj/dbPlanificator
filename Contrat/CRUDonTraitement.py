import aiomysql

async def creation_traitement(pool, contrat_id: int, id_type_traitement: int) -> int | None:
    """
    Crée un nouveau traitement lié à un contrat et un type de traitement avec gestion de transaction.

    Args:
        pool: Le pool de connexions aiomysql.
        contrat_id (int): L'ID du contrat associé.
        id_type_traitement (int): L'ID du type de traitement.

    Returns:
        int | None: L'ID du traitement créé, ou None en cas d'échec.
    """
    conn = None
    try:
        conn = await pool.acquire()
        await conn.begin()  # Début de la transaction
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO Traitement (contrat_id, id_type_traitement) VALUES (%s, %s)",
                (contrat_id, id_type_traitement)
            )
            await conn.commit()  # Validation de la transaction
            return cur.lastrowid
    except Exception as e:
        if conn:
            await conn.rollback()  # Annulation de la transaction en cas d'erreur
        print(f"Erreur lors de la création du traitement : {e}")
        return None
    finally:
        if conn:
            pool.release(conn)

async def read_traitement(pool, traitement_id: int | None = None) -> list[dict] | dict | None:
    """
    Lit les informations d'un traitement spécifique par son ID, ou de tous les traitements.
    Cette fonction ne modifie pas la base de données, donc pas de transaction explicite.

    Args:
        pool: Le pool de connexions aiomysql.
        traitement_id (int | None): L'ID du traitement.

    Returns:
        dict | None: Un dictionnaire contenant les informations du traitement, ou None si non trouvé ou en cas d'erreur.
    """
    conn = None
    try:
        conn = await pool.acquire()
        async with conn.cursor(aiomysql.DictCursor) as cur:
            if traitement_id is None:
                await cur.execute("""
                    SELECT
                        t.traitement_id,
                        t.contrat_id,
                        t.id_type_traitement,
                        tt.typeTraitement AS nom_type_traitement
                    FROM Traitement t
                    JOIN TypeTraitement tt ON t.id_type_traitement = tt.id_type_traitement
                """)
                return await cur.fetchall()
            else:
                await cur.execute("""
                    SELECT
                        t.traitement_id,
                        t.contrat_id,
                        t.id_type_traitement,
                        tt.typeTraitement AS nom_type_traitement
                    FROM Traitement t
                    JOIN TypeTraitement tt ON t.id_type_traitement = tt.id_type_traitement
                    WHERE t.traitement_id = %s
                """, (traitement_id,))
                return await cur.fetchone()
    except Exception as e:
        print(f"Erreur lors de la lecture du traitement (ID: {traitement_id}) : {e}")
        return None if traitement_id is not None else []
    finally:
        if conn:
            pool.release(conn)

async def update_traitement(pool, traitement_id: int, contrat_id: int, id_type_traitement: int) -> int:
    """
    Modifie un traitement existant avec gestion de transaction.

    Args:
        pool: Le pool de connexions aiomysql.
        traitement_id (int): L'ID du traitement à modifier.
        contrat_id (int): Le nouvel ID du contrat.
        id_type_traitement (int): Le nouvel ID du type de traitement.

    Returns:
        int: Le nombre de lignes affectées (1 si succès, 0 sinon).
    """
    conn = None
    try:
        conn = await pool.acquire()
        await conn.begin()  # Début de la transaction
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE Traitement SET contrat_id = %s, id_type_traitement = %s WHERE traitement_id = %s",
                (contrat_id, id_type_traitement, traitement_id)
            )
            await conn.commit()  # Validation de la transaction
            return cur.rowcount
    except Exception as e:
        if conn:
            await conn.rollback()  # Annulation de la transaction en cas d'erreur
        print(f"Erreur lors de la modification du traitement (ID: {traitement_id}) : {e}")
        return 0
    finally:
        if conn:
            pool.release(conn)

async def delete_traitement(pool, traitement_id: int) -> int:
    """
    Supprime un traitement existant avec gestion de transaction.

    Args:
        pool: Le pool de connexions aiomysql.
        traitement_id (int): L'ID du traitement à supprimer.

    Returns:
        int: Le nombre de lignes supprimées (1 si succès, 0 sinon).
    """
    conn = None
    try:
        conn = await pool.acquire()
        await conn.begin()  # Début de la transaction
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM Traitement WHERE traitement_id = %s", (traitement_id,))
            await conn.commit()  # Validation de la transaction
            return cur.rowcount
    except Exception as e:
        if conn:
            await conn.rollback()  # Annulation de la transaction en cas d'erreur
        print(f"Erreur lors de la suppression du traitement (ID: {traitement_id}) : {e}")
        return 0
    finally:
        if conn:
            pool.release(conn)

async def obtenir_types_traitement(pool) -> list[dict]:
    """
    Récupère tous les types de traitement disponibles.
    Cette fonction ne modifie pas la base de données, donc pas de transaction explicite.

    Returns:
        list[dict]: Une liste de dictionnaires, chaque dictionnaire représentant un type de traitement.
    """
    conn = None
    try:
        conn = await pool.acquire()
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SELECT id_type_traitement, typeTraitement FROM TypeTraitement ORDER BY typeTraitement")
            types_data = await cursor.fetchall()
            return types_data
    except Exception as e:
        print(f"Erreur lors de la récupération des types de traitement : {e}")
        return []
    finally:
        if conn:
            pool.release(conn)
