# Scraper

This package provides a simple Goodreads scraper for collecting public information about the most-read books and saving the results as JSON. It also includes an AWS Lambda handler to run the scraper in a serverless environment and upload output files to an S3 bucket.

## Project structure

- `scraper.py` - Contains the `most_read_scraper` class and scraping logic.
- `lamda_function.py` - AWS Lambda handler that runs the scraper, writes results to `/tmp`, and uploads the JSON output to S3.
- `pyproject.toml` - Package metadata and Python dependency declarations.

## Features

- Fetches the Goodreads "most read" book list from `https://www.goodreads.com/book/most_read`.
- Scrapes book metadata including title, author, description, genres, rating, and publication info.
- Extracts reviews from each book page, including review text and like counts.
- Supports retry logic for network calls.
- Lambda-ready entrypoint for uploading a JSON file to an S3 bucket.

## Source code
To use this code, it is recommended to create a virtual environment with ```uv venv```, then install the required dependencies using ```uv sync```.

### ```scraper.py```
This scraper aims to extract information about books and the reviews related to them on the Goodreads platform within the "most read" section, which is updated weekly. This is for purely academic and research purposes.
Users' personal information is completely discarded, and only the review content and the support it received are taken into account. If Goodreads changes its layout, the script may break.

Usage:
1. Create an object of the ```most_read_scraper``` class.
2. Run the ```scrape``` method, which saves the obtained information in the ```books_data``` attribute.

### Running on AWS Lambda
1. Create a role to be able to publish the generated layer to Lambda.
2. Install the dependencies in the folder (no need to create it beforehand).
```
uv pip install \
  "beautifulsoup4==4.14.3" \
  "requests==2.33.0" \
  "tqdm==4.67.3" \
  --target layer/python/lib/python3.13/site-packages \
  --python-version 3.13 \
  --only-binary=:all:
```

4. Create a package of the dependencies
```
cd layer && zip -r ../layer.zip . && cd ..
```
5. Import the created layer to Lambda
```
aws lambda publish-layer-version \
  --layer-name "scraper-dependencies" \
  --zip-file fileb://layer.zip \
  --compatible-runtimes python3.13 \
  --compatible-architectures x86_64
```
6. Create a basic Lambda function with a minimum timeout of 3 minutes and 512 MB of memory.
7. Create a package of the functions to be used in Lambda
```
zip function.zip lambda_function.py scraper.py
```
8. Update the code of the function already created in step 4.
```
aws lambda update-function-code \
 --function-name LAMBDA_FUNC_NAME \
 --zip-file fileb://function.zip
```