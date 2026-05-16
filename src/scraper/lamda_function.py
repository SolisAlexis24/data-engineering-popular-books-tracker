from scraper import most_read_scraper
import json
from datetime import date
import logging
from pathlib import Path
import boto3
from botocore.exceptions import NoCredentialsError

# Configurar logging para CloudWatch
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BUCKET = "<Your S3 bucket name here>"  # Reemplaza con el nombre de tu bucket S3

def lambda_handler(event, context):
    scraper = most_read_scraper()
    scraper.scrape()

    if not scraper.books_data:
        logger.error("No se pudo obtener informacion de los libros, terminando")
        return {"statusCode": 500, "body": "No se obtuvieron datos"}

    today = date.today()
    local_filename = f"/tmp/{today}.json"
    remote_filename = f"1bronze/year={today.year}/week={today.isocalendar().week:02d}/{today}.json"

    with open(local_filename, "w", encoding="utf-8") as file:
        json.dump(scraper.books_data, file, ensure_ascii=False, indent=2)

    s3_bucket = boto3.client("s3")
    try:
        logger.info(f"Subiendo {local_filename} a s3://{BUCKET}/{remote_filename}...")
        s3_bucket.upload_file(local_filename, BUCKET, remote_filename)
        logger.info("Carga exitosa")
    except FileNotFoundError:
        raise RuntimeError(f"El archivo local no fue encontrado")
    except NoCredentialsError:
        raise RuntimeError(f"No se encontraron credenciales de AWS configuradas")
    except Exception as e:
        raise RuntimeError(f"Error desconocido: {e}")
    finally:
        Path(local_filename).unlink(missing_ok=True)

    return {
        "statusCode": 200, 
        "body": f"Archivo subido: {remote_filename}",
        "year": str(today.year),
        "week": f"{today.isocalendar().week:02d}"
    }
