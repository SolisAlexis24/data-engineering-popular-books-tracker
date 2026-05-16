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

## Installation

Use `uv` to install dependencies from `pyproject.toml` and create a local editable package.

```bash
cd src/scraper
pip install -U pip
pip install uv
uv install
uv develop
```

If you need a minimal runtime install without the editable package, install only the dependencies from the project lock:

```bash
cd src/scraper
pip install -U pip
pip install uv
uv install --no-dev
```

## AWS Lambda layer with uv

To package dependencies into a Lambda layer instead of installing them locally, use `uv` and the repository lock file.

1. Install `uv` if it is not already available:

```bash
pip install uv
```

2. From `src/scraper`, create a layer directory and install dependencies into it:

```bash
cd src/scraper
mkdir -p lambda-layer/python
uv install --target ./lambda-layer/python
```

3. Create the layer archive:

```bash
cd lambda-layer
zip -r ../scraper-layer.zip python
```

4. Upload `scraper-layer.zip` to AWS Lambda as a layer and attach it to your function.

This keeps execution dependencies out of the local package install and allows Lambda to load the libraries from the shared layer.

## Usage

### Running the scraper directly

Use `most_read_scraper` from `scraper.py`:

```python
from scraper import most_read_scraper

scraper = most_read_scraper()
scraper.scrape()
print(scraper.books_data)
```

### How it works

- `most_read_scraper.scrape()` retrieves the list of most-read book URLs.
- It iterates through each book URL and scrapes book details and reviews.
- Data is stored in `scraper.books_data` as a list of dictionaries.

## AWS Lambda usage

The Lambda handler is defined in `lamda_function.py`.

### Expected behavior

1. Instantiate `most_read_scraper`.
2. Run `scraper.scrape()`.
3. If no book data is collected, return HTTP 500.
4. Save scraped output to `/tmp/{today}.json`.
5. Upload the file to S3 at `1bronze/year={year}/week={week}/{date}.json`.
6. Delete the temporary local file.

### Required configuration

- Set the `BUCKET` constant in `lamda_function.py` to your S3 bucket name.
- Ensure AWS credentials are available in the Lambda execution environment.

### Lambda handler

The function exported for AWS Lambda is:

```python
def lambda_handler(event, context):
    ...
```

### Error handling

The Lambda function handles:

- missing scraped data
- local file not found
- missing AWS credentials
- generic exceptions during upload

## Notes and limitations

- The scraper is built for Goodreads HTML structure as of this implementation. Changes to page markup may break selectors.
- The scraper uses public pages only and does not require Goodreads API access.
- The genre URL helper `get_books_urls_from_genre()` constructs a shelf URL but may need refinement for full genre scraping.

## Dependencies

- `beautifulsoup4`
- `boto3`
- `requests`
- `tqdm`

## License

This repository does not include a license declaration. Add a license file if needed for your project.
