"""
Unit tests for the scraper.py module.
Popular Books Tracker — MISAMO inc.

Run:
    cd tests/unit
    pytest test_scraper.py -v

Or from the project root:
    pytest tests/unit/test_scraper.py -v
"""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch, call

# Add src/scraper to path so the module can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/scraper"))

from scraper import most_read_scraper  # noqa: E402


# ─── Fixtures ──────────────────────────────────────────────────────────────

SAMPLE_MOST_READ_HTML = """
<html><body>
  <a class="bookTitle" href="/book/show/12345.Some_Book">Book One</a>
  <a class="bookTitle" href="/book/show/67890.Another_Book">Book Two</a>
</body></html>
"""

SAMPLE_BOOK_HTML = """
<html><body>
  <h1 data-testid="bookTitle">The Great Gatsby</h1>
  <span class="ContributorLink__name" data-testid="name">F. Scott Fitzgerald</span>
  <div data-testid="description"><span class="Formatted">A story of the fabulously wealthy Jay Gatsby.</span></div>
  <div data-testid="genresList">
    <span class="Button__labelItem">Fiction</span>
    <span class="Button__labelItem">Classic</span>
    <span class="Button__labelItem">Genres</span>
  </div>
  <div class="RatingStatistics__rating">4.34</div>
  <p data-testid="publicationInfo">First published April 10, 1925</p>
  <article class="ReviewCard">
    <span class="ReviewText__content">Absolutely brilliant novel.</span>
    <footer class="SocialFooter">
      <span class="Button__labelItem">142 likes</span>
    </footer>
  </article>
  <article class="ReviewCard">
    <span class="ReviewText__content">A masterpiece of American literature.</span>
    <footer class="SocialFooter">
      <span class="Button__labelItem">89 likes</span>
    </footer>
  </article>
</body></html>
"""

VALID_BOOK_URL = "https://www.goodreads.com/book/show/12345.The_Great_Gatsby"
INVALID_BOOK_URL = "https://www.goodreads.com/author/show/12345"


def make_mock_response(html: str, status_code: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.text = html
    return mock


# ─── Tests: Initialization ─────────────────────────────────────────────────

class TestInit:
    def test_default_values(self):
        scraper = most_read_scraper()
        assert scraper.most_read_url_list == []
        assert scraper.max_conn_retries == 3
        assert scraper.books_data == []

    def test_custom_retries(self):
        scraper = most_read_scraper(max_conn_retries=5)
        assert scraper.max_conn_retries == 5

    def test_zero_retries(self):
        scraper = most_read_scraper(max_conn_retries=0)
        assert scraper.max_conn_retries == 0


# ─── Tests: _get_books_list ────────────────────────────────────────────────

class TestGetBooksList:
    @patch("scraper.requests.Session")
    def test_returns_true_and_fills_list_on_success(self, MockSession):
        mock_response = make_mock_response(SAMPLE_MOST_READ_HTML)
        MockSession.return_value.get.return_value = mock_response

        scraper = most_read_scraper()
        result = scraper._get_books_list()

        assert result is True
        assert len(scraper.most_read_url_list) == 2
        assert "https://www.goodreads.com/book/show/12345.Some_Book" in scraper.most_read_url_list

    @patch("scraper.requests.Session")
    def test_returns_false_on_non_200(self, MockSession):
        mock_response = make_mock_response("", status_code=503)
        MockSession.return_value.get.return_value = mock_response

        scraper = most_read_scraper()
        result = scraper._get_books_list()

        assert result is False
        assert scraper.most_read_url_list == []

    @patch("scraper.requests.Session")
    def test_returns_false_when_response_is_none(self, MockSession):
        MockSession.return_value.get.side_effect = Exception("Connection error")

        scraper = most_read_scraper()
        result = scraper._get_books_list()

        assert result is False

    @patch("scraper.requests.Session")
    def test_empty_page_returns_empty_list(self, MockSession):
        mock_response = make_mock_response("<html><body></body></html>")
        MockSession.return_value.get.return_value = mock_response

        scraper = most_read_scraper()
        result = scraper._get_books_list()

        assert result is True
        assert scraper.most_read_url_list == []


# ─── Tests: _get_book_data ─────────────────────────────────────────────────

class TestGetBookData:
    def _get_soup(self, html: str):
        from bs4 import BeautifulSoup
        return BeautifulSoup(html, "html.parser")

    def test_extracts_all_fields_correctly(self):
        soup = self._get_soup(SAMPLE_BOOK_HTML)
        scraper = most_read_scraper()
        data = scraper._get_book_data(soup, 12345)

        assert data["id"] == 12345
        assert data["title"] == "The Great Gatsby"
        assert data["author"] == "F. Scott Fitzgerald"
        assert "Jay Gatsby" in data["description"]
        assert "Fiction" in data["genres"]
        assert "Classic" in data["genres"]
        assert data["rating"] == pytest.approx(4.34)
        assert data["date"] == "April 10 1925"

    def test_genres_removes_last_element(self):
        # The scraper removes the last element from genresList (the "Genres" / see more button)
        soup = self._get_soup(SAMPLE_BOOK_HTML)
        scraper = most_read_scraper()
        data = scraper._get_book_data(soup, 1)

        assert "Genres" not in data["genres"]
        assert len(data["genres"]) == 2

    def test_missing_fields_return_defaults(self):
        empty_html = "<html><body></body></html>"
        soup = self._get_soup(empty_html)
        scraper = most_read_scraper()
        data = scraper._get_book_data(soup, 99)

        assert data["id"] == 99
        assert data["title"] == ""
        assert data["author"] == ""
        assert data["description"] == ""
        assert data["genres"] == []
        assert data["rating"] is None
        assert data["date"] == ""

    def test_invalid_rating_is_ignored(self):
        html = """
        <html><body>
          <div class="RatingStatistics__rating">not-a-number</div>
        </body></html>
        """
        soup = self._get_soup(html)
        scraper = most_read_scraper()
        data = scraper._get_book_data(soup, 1)
        assert data["rating"] is None

    def test_date_strips_prefix_and_comma(self):
        html = """
        <html><body>
          <p data-testid="publicationInfo">First published January 1, 2020</p>
        </body></html>
        """
        soup = self._get_soup(html)
        scraper = most_read_scraper()
        data = scraper._get_book_data(soup, 1)
        assert data["date"] == "January 1 2020"
        assert "First published" not in data["date"]


# ─── Tests: _get_reviews_data ──────────────────────────────────────────────

class TestGetReviewsData:
    def _get_soup(self, html: str):
        from bs4 import BeautifulSoup
        return BeautifulSoup(html, "html.parser")

    def test_extracts_reviews_and_likes(self):
        soup = self._get_soup(SAMPLE_BOOK_HTML)
        scraper = most_read_scraper()
        reviews = scraper._get_reviews_data(soup)

        assert len(reviews) == 2
        assert reviews[0]["text"] == "Absolutely brilliant novel."
        assert reviews[0]["likes"] == 142
        assert reviews[1]["text"] == "A masterpiece of American literature."
        assert reviews[1]["likes"] == 89

    def test_review_without_likes_is_included_with_none(self):
        html = """
        <html><body>
          <article class="ReviewCard">
            <span class="ReviewText__content">Good book</span>
            <footer class="SocialFooter"></footer>
          </article>
        </body></html>
        """
        soup = self._get_soup(html)
        scraper = most_read_scraper()
        reviews = scraper._get_reviews_data(soup)

        assert len(reviews) == 1
        assert reviews[0]["text"] == "Good book"
        assert reviews[0]["likes"] is None

    def test_review_without_text_is_excluded(self):
        html = """
        <html><body>
          <article class="ReviewCard">
            <footer class="SocialFooter">
              <span class="Button__labelItem">10 likes</span>
            </footer>
          </article>
        </body></html>
        """
        soup = self._get_soup(html)
        scraper = most_read_scraper()
        reviews = scraper._get_reviews_data(soup)

        assert len(reviews) == 0

    def test_empty_page_returns_empty_list(self):
        soup = self._get_soup("<html><body></body></html>")
        scraper = most_read_scraper()
        reviews = scraper._get_reviews_data(soup)
        assert reviews == []


# ─── Tests: _format_likes ─────────────────────────────────────────────────

class TestFormatLikes:
    def setup_method(self):
        self.scraper = most_read_scraper()

    def test_plain_integer(self):
        assert self.scraper._format_likes("142 likes") == 142

    def test_integer_with_comma(self):
        assert self.scraper._format_likes("1,234 likes") == 1234

    def test_k_notation(self):
        assert self.scraper._format_likes("2.5k likes") == 2500

    def test_whole_k(self):
        assert self.scraper._format_likes("3k likes") == 3000

    def test_zero_likes(self):
        assert self.scraper._format_likes("0 likes") == 0


# ─── Tests: _scrape_book ───────────────────────────────────────────────────

class TestScrapeBook:
    @patch("scraper.requests.Session")
    def test_returns_empty_dict_for_invalid_url(self, MockSession):
        scraper = most_read_scraper()
        result = scraper._scrape_book(INVALID_BOOK_URL)
        assert result == {}

    @patch("scraper.requests.Session")
    def test_returns_book_and_reviews_on_success(self, MockSession):
        mock_response = make_mock_response(SAMPLE_BOOK_HTML)
        MockSession.return_value.get.return_value = mock_response

        scraper = most_read_scraper()
        result = scraper._scrape_book(VALID_BOOK_URL)

        assert "book" in result
        assert "reviews" in result
        assert result["book"]["id"] == 12345
        assert result["book"]["title"] == "The Great Gatsby"
        assert len(result["reviews"]) == 2

    @patch("scraper.requests.Session")
    def test_returns_empty_dict_on_non_200(self, MockSession):
        mock_response = make_mock_response("", status_code=404)
        MockSession.return_value.get.return_value = mock_response

        scraper = most_read_scraper()
        result = scraper._scrape_book(VALID_BOOK_URL)
        assert result == {}


# ─── Tests: _get_response ─────────────────────────────────────────────────

class TestGetResponse:
    def test_returns_response_on_success(self):
        scraper = most_read_scraper()
        mock_session = MagicMock()
        mock_response = make_mock_response("<html></html>")
        mock_session.get.return_value = mock_response

        result = scraper._get_response(mock_session, "https://example.com")
        assert result == mock_response

    def test_retries_on_timeout_and_returns_none_after_max(self):
        import requests as req
        scraper = most_read_scraper(max_conn_retries=2)
        mock_session = MagicMock()
        mock_session.get.side_effect = req.exceptions.Timeout

        result = scraper._get_response(
            mock_session, "https://example.com", timeout=1, cooldown_s=0
        )
        assert result is None
        assert mock_session.get.call_count == 3  # 1 attempt + 2 retries

    def test_returns_none_on_request_exception(self):
        import requests as req
        scraper = most_read_scraper()
        mock_session = MagicMock()
        mock_session.get.side_effect = req.exceptions.ConnectionError

        result = scraper._get_response(mock_session, "https://example.com", cooldown_s=0)
        assert result is None


# ─── Tests: scrape (full flow) ─────────────────────────────────────────────

class TestScrape:
    @patch("scraper.requests.Session")
    def test_full_scrape_populates_books_data(self, MockSession):
        # First call → most_read page; subsequent calls → book pages
        mock_session_instance = MagicMock()
        MockSession.return_value = mock_session_instance
        mock_session_instance.get.side_effect = [
            make_mock_response(SAMPLE_MOST_READ_HTML),  # most_read list
            make_mock_response(SAMPLE_BOOK_HTML),        # book 1
            make_mock_response(SAMPLE_BOOK_HTML),        # book 2
        ]

        scraper = most_read_scraper()
        scraper.scrape()

        assert len(scraper.books_data) == 2

    @patch("scraper.requests.Session")
    def test_scrape_does_not_crash_when_list_fails(self, MockSession):
        mock_session_instance = MagicMock()
        MockSession.return_value = mock_session_instance
        mock_session_instance.get.return_value = make_mock_response("", status_code=503)

        scraper = most_read_scraper()
        scraper.scrape()

        assert scraper.books_data == []
