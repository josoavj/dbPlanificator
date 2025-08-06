import aiomysql

async def create_signalement(pool, planning_detail_id: int, motif: str, type_signalement: str) -> int | None:
    """
    Crée un nouveau signalement dans la base de données avec gestion de transaction.

    Args:
        pool: Le pool de connexions aiomysql.
        planning_detail_id (int): L'ID du détail de planification associé.
        motif (str): Le motif du signalement.
        type_signalement (str): Le type de signalement.

    Returns:
        int | None: L'ID du signalement nouvellement créé, ou None en cas d'échec.
    """
    conn = None
    try:
        conn = await pool.acquire()
        await conn.begin()  # Début de la transaction
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO Signalement (planning_detail_id, motif, type) VALUES (%s, %s, %s)",
                (planning_detail_id, motif, type_signalement)
            )
            await conn.commit()  # Validation de la transaction
            return cur.lastrowid
    except Exception as e:
        if conn:
            await conn.rollback()  # Annulation de la transaction en cas d'erreur
        print(f"Erreur lors de la création du signalement : {e}")
        return None
    finally:
        if conn:
            pool.release(conn)

async def read_signalement(pool, signalement_id: int | None = None) -> list[dict] | dict | None:
    """
    Lit les informations d'un signalement spécifique par son ID, ou de tous les signalements.
    Cette fonction ne modifie pas la base de données, donc pas de transaction explicite.

    Args:
        pool: Le pool de connexions aiomysql.
        signalement_id (int | None): L'ID du signalement à lire (optionnel).

    Returns:
        list[dict] | dict | None: Une liste de dictionnaires pour tous les signalements,
                                  un dictionnaire pour un signalement spécifique,
                                  ou None en cas d'échec.
    """
    conn = None
    try:
        conn = await pool.acquire()
        async with conn.cursor(aiomysql.DictCursor) as cur:
            if signalement_id is None:
                await cur.execute("SELECT * FROM Signalement")
                return await cur.fetchall()
            else:
                await cur.execute("""
                    SELECT
                        s.signalement_id,
                        s.motif,
                        s.type,
                        s.date_creation,
                        pd.planning_detail_id,
                        pd.date_planification,
                        p.traitement_id,
                        tt.typeTraitement AS nom_type_traitement
                    FROM Signalement s
                    JOIN PlanningDetails pd ON s.planning_detail_id = pd.planning_detail_id
                    JOIN Planning p ON pd.planning_id = p.planning_id
                    JOIN TypeTraitement tt ON p.id_type_traitement = tt.id_type_traitement
                    WHERE s.signalement_id = %s
                """, (signalement_id,))
                return await cur.fetchone()
    except Exception as e:
        print(f"Erreur lors de la lecture du signalement : {e}")
        return None if signalement_id is not None else []
    finally:
        if conn:
            pool.release(conn)

async def update_signalement(pool, signalement_id: int, planning_detail_id: int, motif: str, type_signalement: str) -> int:
    """
    Modifie un signalement existant avec gestion de transaction.

    Args:
        pool: Le pool de connexions aiomysql.
        signalement_id (int): L'ID du signalement à mettre à jour.
        planning_detail_id (int): Le nouvel ID du détail de planification.
        motif (str): Le nouveau motif.
        type_signalement (str): Le nouveau type de signalement.

    Returns:
        int: Le nombre de lignes affectées (1 si succès, 0 sinon).
    """
    conn = None
    try:
        conn = await pool.acquire()
        await conn.begin()  # Début de la transaction
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE Signalement SET planning_detail_id = %s, motif = %s, type = %s WHERE signalement_id = %s",
                (planning_detail_id, motif, type_signalement, signalement_id)
            )
            await conn.commit()  # Validation de la transaction
            return cur.rowcount
    except Exception as e:
        if conn:
            await conn.rollback()  # Annulation de la transaction en cas d'erreur
        print(f"Erreur lors de la mise à jour du signalement : {e}")
        return 0
    finally:
        if conn:
            pool.release(conn)

async def delete_signalement(pool, signalement_id: int) -> int:
    """
    Supprime un signalement existant avec gestion de transaction.

    Args:
        pool: Le pool de connexions aiomysql.
        signalement_id (int): L'ID du signalement à supprimer.

    Returns:
        int: Le nombre de lignes supprimées (1 si succès, 0 sinon).
    """
    conn = None
    try:
        conn = await pool.acquire()
        await conn.begin()  # Début de la transaction
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM Signalement WHERE signalement_id = %s", (signalement_id,))
            await conn.commit()  # Validation de la transaction
            return cur.rowcount
    except Exception as e:
        if conn:
            await conn.rollback()  # Annulation de la transaction en cas d'erreur
        print(f"Erreur lors de la suppression du signalement : {e}")
        return 0
    finally:
        if conn:
            pool.release(conn)
