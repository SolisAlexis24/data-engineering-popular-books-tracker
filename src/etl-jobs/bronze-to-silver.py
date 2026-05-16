import sys
import boto3
import json
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext
from pyspark.sql import functions as F 
from pyspark.sql.types import StringType
from botocore.exceptions import ClientError
from pyspark.errors import AnalysisException

model_id = ''

prompt = """Analiza estas reseñas ponderadas por likes y resume en menos de 30 palabras 
            el sentimiento general de los lectores hacia el libro. No des respuesta extra
            y no expliques la salida, solo da el resumen de las reseñas únicamente basado
            en la información a continuación en ESPAÑOL sin importar el idioma de la reseña.
            No te pases de 30 palabras y no alucines: """

def sumarize_reviews(reviews) -> str:
    """Recibe un string con las reseñas y regresa el resumen generado por IA."""
    response_text = "Sin reseñas"
    if not reviews:
        return response_text
        
    bedrock = boto3.client(
        service_name='bedrock-runtime',
        region_name='us-east-2'
    )
    try:
        conversation = [
            {
                "role" : "user",
                "content": [{"text": prompt + reviews}]
            }
        ]
        response = bedrock.converse(
            modelId = model_id,
            messages=conversation,
            inferenceConfig={
                "maxTokens": 512, 
                "temperature": 0.5, 
                "topP": 0.9
            }
        )
        response_text = response["output"]["message"]["content"][0]["text"]
    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
    finally:
        return response_text


sumarize_reviews_udf = F.udf(sumarize_reviews, StringType())

prompt_description = """Dado los géneros y la descripción de un libro, genera una descripción 
                        atractiva en español de máximo 50 palabras. No des respuesta extra, 
                        no expliques la salida, solo da la descripción. Información: """

def generate_description(genres, description) -> str:
    """Recibe los géneros y descripción del libro y regresa una descripción generada por IA."""
    response_text = "Sin descripción"
    
    if not genres and not description:
        return response_text
    
    # Combina géneros y descripción en un solo string
    input_text = f"Géneros: {genres} | Descripción: {description}"
    
    bedrock = boto3.client(
        service_name='bedrock-runtime',
        region_name='us-east-2'
    )
    try:
        conversation = [
            {
                "role": "user",
                "content": [{"text": prompt_description + input_text}]
            }
        ]
        response = bedrock.converse(
            modelId=model_id,
            messages=conversation,
            inferenceConfig={
                "maxTokens": 512,
                "temperature": 0.5,
                "topP": 0.9
            }
        )
        response_text = response["output"]["message"]["content"][0]["text"]
    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
    finally:
        return response_text

generate_description_udf = F.udf(generate_description, StringType())


args = getResolvedOptions(sys.argv, ['JOB_NAME' , 'year', 'week'])
year = int(args['year'])
week = int(args['week'])


sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
spark.conf.set("spark.sql.session.timeZone", "UTC")

job = Job(glueContext)
job.init(args['JOB_NAME'], args)

BUCKET = ""
input_path = f"{BUCKET}/1bronze/year={year}/week={week}/"
output_books   = f"{BUCKET}/2silver/book_data/"
output_weeks   = f"{BUCKET}/2silver/book_appearances/"

df_raw = spark.read \
    .option("multiline", "true") \
    .option("mode", "PERMISSIVE") \
    .option("allowControlChars", "true") \
    .json(input_path)

df_flat = df_raw.select(
    F.col("book.id").alias("id"),
    F.col("book.title").alias("title"),
    F.col("book.author").alias("author"),
    F.col("book.description").alias("description"),
    F.col("book.genres").alias("genres"),
    F.col("book.rating").alias("rating"),
    F.col("book.date").alias("pub_date"),
    F.col("reviews").alias("reviews"),
    F.lit(year).alias("year"),
    F.lit(week).alias("week"),
)

try:
    df_existing = spark.read.parquet(output_books)
    df_new_only = df_flat.join(
        df_existing.select("id"),
        on=["id"],
        how="left_anti"
    )
except AnalysisException:
    df_new_only = df_flat

df_with_text = df_flat.withColumn(
    "reviews_text",
    F.concat_ws(
        " | ",
        F.transform(
            F.col("reviews"),
            lambda r: F.concat(
                F.lit("("),
                r["likes"].cast("string"),
                F.lit(" likes) "),
                r["text"]
            )
        )
    )
)

df_with_summary = df_with_text \
    .withColumn(
        "ai_reviews_summary",
        sumarize_reviews_udf(F.col("reviews_text"))
    ) \
    .withColumn(
        "ai_description",
        generate_description_udf(
            F.concat_ws(", ", F.col("genres")),
            F.col("description")
        )
    ) \
    .drop("reviews_text", "reviews", "description")

df_with_summary.select(
    "id", "title", "author", "rating", "pub_date",
    "ai_reviews_summary", "ai_description", "genres"
).write.mode("append").parquet(output_books)

df_flat.select("id", "year", "week") \
    .write \
    .mode("append") \
    .parquet(output_weeks)
    
job.commit()