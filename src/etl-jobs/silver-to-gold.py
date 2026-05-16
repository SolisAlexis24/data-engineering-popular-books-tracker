import sys
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
import psycopg2
from datetime import date

# ─── Argumentos del Job ───────────────────────────────────────────────
args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

CONTEO_SEMANAS = 5

# ─── Rango de semanas ISO ─────────────────────────────────────────────
hoy = date.today()
SEMANA_ACTUAL = hoy.isocalendar()[1]
ANIO_ACTUAL   = hoy.isocalendar()[0]
SEMANA_INICIO = SEMANA_ACTUAL - CONTEO_SEMANAS
print(f"[INFO] Semanas {SEMANA_INICIO}–{SEMANA_ACTUAL} del año {ANIO_ACTUAL}")

# ─── Configuración RDS ────────────────────────────────────────────────
RDS_HOST     = ""
RDS_PORT     = 0
RDS_DB       = ""
RDS_USER     = ""
RDS_PASSWORD = ""

# ─── 1. Leer ambas fuentes silver desde el catálogo de Glue ──────────
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

# ─── 2. Filtrar apariciones en el rango de semanas ───────────────────
# Vista intermedia para no repetir el filtro en ambas queries
spark.sql(f"""
    CREATE OR REPLACE TEMP VIEW appearances_filtradas AS
    SELECT a.id
    FROM book_appearances a
    WHERE a.week >= {SEMANA_INICIO}
      AND a.week <= {SEMANA_ACTUAL}
      AND a.year  = {ANIO_ACTUAL}
""")

# ─── 2a. Repeticiones de libros (Top 10) ─────────────────────────────
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

# ─── 2b. Repeticiones de géneros ─────────────────────────────────────
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

# ─── Validar resultados ───────────────────────────────────────────────
filas_libros  = df_libros.collect()
filas_generos = df_generos.collect()

if not filas_libros and not filas_generos:
    print("[WARN] Sin registros en el rango indicado. Abortando.")
    job.commit()
    sys.exit(0)

print(f"[INFO] {len(filas_libros)} libros | {len(filas_generos)} géneros encontrados.")

# ─── 3. Insertar en RDS ───────────────────────────────────────────────
conn = psycopg2.connect(
    host=RDS_HOST, port=RDS_PORT,
    dbname=RDS_DB, user=RDS_USER, password=RDS_PASSWORD
)
cur = conn.cursor()

try:
    # 3a. Metadata compartida (una sola fila por ejecución)
    cur.execute("""
        INSERT INTO metadata_repeticiones (fecha_registro, conteo_semanas)
        VALUES (%s, %s)
        RETURNING id_metadata;
    """, (hoy, CONTEO_SEMANAS))
    id_metadata = cur.fetchone()[0]
    print(f"[OK] Metadata id={id_metadata} | semanas {SEMANA_INICIO}–{SEMANA_ACTUAL}")

    # 3b. Repeticiones de libros
    if filas_libros:
        datos_libros = [
            (id_metadata, fila['titulo'], fila['repeticiones'])
            for fila in filas_libros
        ]
        cur.executemany("""
            INSERT INTO repeticiones_libros (id_metadata, titulo, repeticiones)
            VALUES (%s, %s, %s);
        """, datos_libros)
        print(f"[OK] {len(datos_libros)} libros insertados.")

    # 3c. Repeticiones de géneros
    if filas_generos:
        datos_generos = [
            (id_metadata, fila['genero'], fila['repeticiones'])
            for fila in filas_generos
        ]
        cur.executemany("""
            INSERT INTO repeticiones_generos (id_metadata, genero, repeticiones)
            VALUES (%s, %s, %s);
        """, datos_generos)
        print(f"[OK] {len(datos_generos)} géneros insertados.")

    conn.commit()

except Exception as e:
    conn.rollback()
    print(f"[ERROR] Rollback ejecutado. Detalle: {e}")
    raise e
finally:
    cur.close()
    conn.close()

job.commit()