"""
Unit tests for the Lambda handler (lamda_function.py).
Popular Books Tracker — MISAMO inc.

Run:
    cd tests/unit
    pytest test_lambda_handler.py -v
"""

import sys
import os
import json
import pytest
from unittest.mock import MagicMock, patch, mock_open

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/scraper"))


# ─── Fixtures ──────────────────────────────────────────────────────────────

SAMPLE_BOOKS_DATA = [
    {
        "book": {
            "id": 1,
            "title": "Book One",
            "author": "Author A",
            "description": "Description A",
            "genres": ["Fiction"],
            "rating": 4.5,
            "date": "January 2020"
        },
        "reviews": [{"text": "Great read!", "likes": 10}]
    },
    {
        "book": {
            "id": 2,
            "title": "Book Two",
            "author": "Author B",
            "description": "Description B",
            "genres": ["Mystery"],
            "rating": 4.1,
            "date": "March 2019"
        },
        "reviews": []
    }
]


# ─── Tests ────────────────────────────────────────────────────────────────

class TestLambdaHandler:
    """
    Tests for the complete lambda_handler flow.
    Mocked: most_read_scraper, boto3.client, open, Path.unlink
    """

    @patch("lamda_function.Path")
    @patch("lamda_function.boto3.client")
    @patch("lamda_function.most_read_scraper")
    def test_successful_execution_returns_200(self, MockScraper, MockBoto3, MockPath):
        mock_scraper_instance = MagicMock()
        mock_scraper_instance.books_data = SAMPLE_BOOKS_DATA
        MockScraper.return_value = mock_scraper_instance

        mock_s3 = MagicMock()
        MockBoto3.return_value = mock_s3

        with patch("builtins.open", mock_open()):
            from lamda_function import lambda_handler
            result = lambda_handler({}, {})

        assert result["statusCode"] == 200
        assert "year" in result
        assert "week" in result

    @patch("lamda_function.boto3.client")
    @patch("lamda_function.most_read_scraper")
    def test_returns_500_when_no_books_data(self, MockScraper, MockBoto3):
        mock_scraper_instance = MagicMock()
        mock_scraper_instance.books_data = []
        MockScraper.return_value = mock_scraper_instance

        from lamda_function import lambda_handler
        result = lambda_handler({}, {})

        assert result["statusCode"] == 500
        assert "No se obtuvieron datos" in result["body"]

    @patch("lamda_function.Path")
    @patch("lamda_function.boto3.client")
    @patch("lamda_function.most_read_scraper")
    def test_s3_upload_called_with_correct_key(self, MockScraper, MockBoto3, MockPath):
        mock_scraper_instance = MagicMock()
        mock_scraper_instance.books_data = SAMPLE_BOOKS_DATA
        MockScraper.return_value = mock_scraper_instance

        mock_s3 = MagicMock()
        MockBoto3.return_value = mock_s3

        with patch("builtins.open", mock_open()):
            from lamda_function import lambda_handler
            lambda_handler({}, {})

        assert mock_s3.upload_file.called
        call_args = mock_s3.upload_file.call_args
        # The third argument (S3 key) must start with "1bronze/"
        remote_key = call_args[0][2]
        assert remote_key.startswith("1bronze/")
        assert "year=" in remote_key
        assert "week=" in remote_key

    @patch("lamda_function.Path")
    @patch("lamda_function.boto3.client")
    @patch("lamda_function.most_read_scraper")
    def test_s3_upload_failure_raises_runtime_error(self, MockScraper, MockBoto3, MockPath):
        from botocore.exceptions import NoCredentialsError

        mock_scraper_instance = MagicMock()
        mock_scraper_instance.books_data = SAMPLE_BOOKS_DATA
        MockScraper.return_value = mock_scraper_instance

        mock_s3 = MagicMock()
        mock_s3.upload_file.side_effect = NoCredentialsError()
        MockBoto3.return_value = mock_s3

        with patch("builtins.open", mock_open()):
            from lamda_function import lambda_handler
            with pytest.raises(RuntimeError, match="credenciales"):
                lambda_handler({}, {})

    @patch("lamda_function.Path")
    @patch("lamda_function.boto3.client")
    @patch("lamda_function.most_read_scraper")
    def test_response_contains_year_and_week_as_strings(self, MockScraper, MockBoto3, MockPath):
        mock_scraper_instance = MagicMock()
        mock_scraper_instance.books_data = SAMPLE_BOOKS_DATA
        MockScraper.return_value = mock_scraper_instance

        mock_s3 = MagicMock()
        MockBoto3.return_value = mock_s3

        with patch("builtins.open", mock_open()):
            from lamda_function import lambda_handler
            result = lambda_handler({}, {})

        assert isinstance(result["year"], str)
        assert isinstance(result["week"], str)
        # week must be a two-digit zero-padded string
        assert len(result["week"]) == 2

    @patch("lamda_function.Path")
    @patch("lamda_function.boto3.client")
    @patch("lamda_function.most_read_scraper")
    def test_temp_file_is_always_deleted(self, MockScraper, MockBoto3, MockPath):
        mock_scraper_instance = MagicMock()
        mock_scraper_instance.books_data = SAMPLE_BOOKS_DATA
        MockScraper.return_value = mock_scraper_instance

        mock_s3 = MagicMock()
        mock_s3.upload_file.side_effect = Exception("Unexpected error")
        MockBoto3.return_value = mock_s3

        mock_path_instance = MagicMock()
        MockPath.return_value = mock_path_instance

        with patch("builtins.open", mock_open()):
            from lamda_function import lambda_handler
            with pytest.raises(RuntimeError):
                lambda_handler({}, {})

        # Temp file must be deleted even when an error occurs
        mock_path_instance.unlink.assert_called_once_with(missing_ok=True)

    @patch("lamda_function.Path")
    @patch("lamda_function.boto3.client")
    @patch("lamda_function.most_read_scraper")
    def test_json_dump_uses_utf8_encoding(self, MockScraper, MockBoto3, MockPath):
        mock_scraper_instance = MagicMock()
        mock_scraper_instance.books_data = SAMPLE_BOOKS_DATA
        MockScraper.return_value = mock_scraper_instance

        mock_s3 = MagicMock()
        MockBoto3.return_value = mock_s3

        m = mock_open()
        with patch("builtins.open", m):
            from lamda_function import lambda_handler
            lambda_handler({}, {})

        open_call_kwargs = m.call_args
        assert open_call_kwargs[1].get("encoding") == "utf-8"
