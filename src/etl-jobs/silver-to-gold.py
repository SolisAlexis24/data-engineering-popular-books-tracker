import sys
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
import psycopg2
from datetime import date

# ── Job arguments ─────────────────────────────────────────────────────────
args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

CONTEO_SEMANAS = 5

# ── ISO week range ────────────────────────────────────────────────────────
today = date.today()
SEMANA_ACTUAL = today.isocalendar()[1]
ANIO_ACTUAL   = today.isocalendar()[0]
SEMANA_INICIO = SEMANA_ACTUAL - CONTEO_SEMANAS
print(f"[INFO] Weeks {SEMANA_INICIO}–{SEMANA_ACTUAL} of year {ANIO_ACTUAL}")

# ── RDS configuration ─────────────────────────────────────────────────────
RDS_HOST     = "<Your RDS endpoint here>"  # Example: books-db.abcdefg.us-east-1.rds.amazonaws.com
RDS_PORT     = 5432  # Default PostgreSQL port
RDS_DB       = "<Your database name here>"  # Example: books_gold
RDS_USER     = "<Your RDS username here>"  # Example: admin
RDS_PASSWORD = "<Your RDS password here>"  # Replace with your password

# ── 1. Read both Silver sources from the Glue Catalog ────────────────────
df_appearances = glueContext.create_dynamic_frame.from_catalog(
    database="db_books",
    table_name="book_appearances"
).toDF()

df_book_data = glueContext.create_dynamic_frame.from_catalog(
    database="db_books",
    table_name="book_data"
).toDF()

df_appearances.createOrReplaceTempView("book_appearances")
df_book_data.createOrReplaceTempView("book_data")

# ── 2. Filter appearances within the week range ───────────────────────────
# Intermediate view to avoid repeating the filter in both queries
spark.sql(f"""
    CREATE OR REPLACE TEMP VIEW appearances_filtradas AS
    SELECT a.id
    FROM book_appearances a
    WHERE a.week >= {SEMANA_INICIO}
      AND a.week <= {SEMANA_ACTUAL}
      AND a.year  = {ANIO_ACTUAL}
""")

# ── 2a. Top 10 books by appearances ──────────────────────────────────────
df_libros = spark.sql("""
    SELECT
        bd.title     AS titulo,
        af.repeticiones
    FROM (
        SELECT
            id,
            COUNT(*) AS repeticiones
        FROM appearances_filtradas
        GROUP BY id
        ORDER BY repeticiones DESC
        LIMIT 10
    ) af
    JOIN (
        SELECT id, MAX(title) AS title
        FROM book_data
        GROUP BY id
    ) bd ON af.id = bd.id
""")

# ── 2b. Top 20 genres by distinct book count ─────────────────────────────
df_generos = spark.sql("""
    SELECT
        genero,
        COUNT(DISTINCT af.id) AS repeticiones
    FROM appearances_filtradas af
    JOIN book_data bd ON af.id = bd.id
    LATERAL VIEW EXPLODE(bd.genres) g AS genero
    GROUP BY genero
    ORDER BY repeticiones DESC
    LIMIT 20
""")

# ── Validate results ──────────────────────────────────────────────────────
filas_libros  = df_libros.collect()
filas_generos = df_generos.collect()

if not filas_libros and not filas_generos:
    print("[WARN] No records found in the specified range. Aborting.")
    job.commit()
    sys.exit(0)

print(f"[INFO] {len(filas_libros)} books | {len(filas_generos)} genres found.")

# ── 3. Insert into RDS ────────────────────────────────────────────────────
conn = psycopg2.connect(
    host=RDS_HOST, port=RDS_PORT,
    dbname=RDS_DB, user=RDS_USER, password=RDS_PASSWORD
)
cur = conn.cursor()

try:
    # 3a. Shared execution metadata (one row per run)
    cur.execute("""
        INSERT INTO metadata_repeticiones (fecha_registro, conteo_semanas)
        VALUES (%s, %s)
        RETURNING id_metadata;
    """, (today, CONTEO_SEMANAS))
    id_metadata = cur.fetchone()[0]
    print(f"[OK] Metadata id={id_metadata} | weeks {SEMANA_INICIO}–{SEMANA_ACTUAL}")

    # 3b. Book appearances
    if filas_libros:
        datos_libros = [
            (id_metadata, fila['titulo'], fila['repeticiones'])
            for fila in filas_libros
        ]
        cur.executemany("""
            INSERT INTO repeticiones_libros (id_metadata, titulo, repeticiones)
            VALUES (%s, %s, %s);
        """, datos_libros)
        print(f"[OK] {len(datos_libros)} books inserted.")

    # 3c. Genre appearances
    if filas_generos:
        datos_generos = [
            (id_metadata, fila['genero'], fila['repeticiones'])
            for fila in filas_generos
        ]
        cur.executemany("""
            INSERT INTO repeticiones_generos (id_metadata, genero, repeticiones)
            VALUES (%s, %s, %s);
        """, datos_generos)
        print(f"[OK] {len(datos_generos)} genres inserted.")

    conn.commit()

except Exception as e:
    conn.rollback()
    print(f"[ERROR] Rollback executed. Detail: {e}")
    raise e
finally:
    cur.close()
    conn.close()

job.commit()
