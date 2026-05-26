import requests
from bs4 import BeautifulSoup
import time
import re
import logging
from tqdm import tqdm


# Headers to prevent connection rejection
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.goodreads.com",
}

# Regular expression for book URL validation
REGEX_BOOK_URL = r"https://www.goodreads.com/book/show/(\d+)[\w.\-]+$"
MOST_READ_BOOKS_URL = r"https://www.goodreads.com/book/most_read"


class most_read_scraper():
    """
    Scraper for collecting PUBLIC information from Goodreads about the most
    popular books each week, published at MOST_READ_BOOKS_URL.
    """
    def __init__(self, max_conn_retries = 3) -> None:
        self.most_read_url_list = []
        self.max_conn_retries = max_conn_retries
        self.books_data = []


    def scrape(self):
        if self._get_books_list() is False:
            logging.error("Could not retrieve book information")
            return

        for book in tqdm(self.most_read_url_list, desc="Scraping books"):
            self.books_data.append(self._scrape_book(book))


    def _get_books_list(self) -> bool:
        """
        Retrieves the relative URLs of books listed on the "book/most_read" page
        and stores them in the most_read_url_list attribute.
        """
        base_book_url: str = "https://www.goodreads.com"
        session = requests.Session()
        session.headers.update(HEADERS)

        response = self._get_response(session, MOST_READ_BOOKS_URL)
        if response is None:
            self.most_read_url_list = []
            return False

        if response.status_code != 200:
            logging.error("Unexpected response status while scraping most_read")
            logging.error(response.status_code)
            self.most_read_url_list = []
            return False

        soup = BeautifulSoup(response.text, "html.parser")
        self.most_read_url_list = [
            base_book_url + str(a.get("href"))
            for a in soup.select("a.bookTitle")
        ]
        return True



    def _scrape_book(self, URL: str) -> dict:
        """
        Collects information for the given book URL and its reviews.
        Returns a dictionary with the format {"book": book_info, "reviews": review_info}.
        """
        match = re.match(REGEX_BOOK_URL, URL)
        if not match:
            logging.error(f"URL {URL} is invalid; must be a book URL")
            return {}

        # Capture group 1 is the book ID (see REGEX_BOOK_URL)
        book_id = int(match.group(1))

        session = requests.Session()
        session.headers.update(HEADERS)

        response = self._get_response(session, URL)
        if response is None:
            return{}

        if response.status_code != 200:
            logging.error(f"{response.status_code}")
            return {}

        soup = BeautifulSoup(response.text, "html.parser")
        book_data = self._get_book_data(soup, book_id)
        reviews = self._get_reviews_data(soup)

        return {
            "book": book_data,
            "reviews": reviews
        }


    def _get_book_data(self, soup: BeautifulSoup, book_id) -> dict:
        """
        Extracts book metadata from the parsed page.
        Returns a dictionary with the book's attributes.
        """
        book_data = {"id":book_id,
                    "title":"",
                    "author":"",
                    "description":"" ,
                    "genres":[],
                    "rating": None,
                    "date": ""}
        # == Locating book HTML elements ==
        title_element = soup.select_one("h1[data-testid='bookTitle']")
        author_element = soup.select_one("span.ContributorLink__name[data-testid='name']")
        description_element = soup.select_one("div[data-testid='description'] .Formatted")
        genres_element = soup.select("div[data-testid='genresList'] .Button__labelItem")
        rating_element = soup.select_one("div.RatingStatistics__rating")
        date_element = soup.select_one("p[data-testid='publicationInfo']")

        # == Extracting data from elements ==
        if title_element:
            book_data["title"] = title_element.get_text(strip=True)
        if author_element:
            book_data["author"] = author_element.get_text(strip=True)
        if description_element:
            book_data["description"] = description_element.get_text(strip=True)
        if genres_element:
            if len(genres_element) > 1:
                genres_element.pop()
            book_data["genres"] = [g.get_text(strip=True) for g in genres_element]
        if rating_element:
            try:
                book_data["rating"] = float(rating_element.get_text(strip=True))
            except ValueError:
                pass
        if date_element:
            date = date_element.get_text(strip=True)
            date = date.replace("First published ", '')
            date = date.replace(',', '')
            book_data["date"] = date

        return book_data


    def _get_reviews_data(self, soup: BeautifulSoup) -> list:
        """
        Extracts review information from the book page.
        Returns a list with review data (text and likes).
        """
        reviews = []

        for card in soup.select("article.ReviewCard"):
            text = None
            likes = None
            # == Locating review HTML elements ==
            text_element = card.select_one(".ReviewText__content")
            footer = card.select_one("footer.SocialFooter")

            # == Extracting data from elements ==
            if text_element:
                text = text_element.get_text(strip=True)

            buttons = footer.select("span.Button__labelItem") if footer else None
            if buttons:
                for btn in buttons:
                    bt_text = btn.get_text(strip=True)
                    if "likes" in bt_text:
                        likes = self._format_likes(bt_text)
                        break

            if text:
                reviews.append({
                    "text": text,
                    "likes": likes,
                })

        return reviews

    def get_books_urls_from_genre(self, genre: str) -> list[str]:
        """
        Retrieves URLs for books in a given shelf/genre section.
        The genre link must begin with:
            https://www.goodreads.com/shelf/show/
        The genre parameter is appended to this base URL.
        """
        base_genre_url: str = "https://www.goodreads.com/shelf/show/"
        base_book_url: str = "https://www.goodreads.com"
        session = requests.Session()
        session.headers.update(HEADERS)

        response = self._get_response(session, f"{base_genre_url} + {genre}")
        if response is None:
            return[]

        if response.status_code != 200:
            logging.error(f"Unexpected response for genre {genre}: \n {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        books_urls = [
            base_book_url + str(a.get("href"))
            for a in soup.select("a.bookTitle")
        ]

        return books_urls


    def _get_response(self, session: requests.Session,
                      url: str,
                      timeout : int = 10,
                      cooldown_s: int = 10) -> requests.Response | None:
        response = None
        for attempt in range(self.max_conn_retries + 1):
            try:
                response = session.get(url, timeout=timeout)
                break
            except requests.exceptions.Timeout:
                if attempt < self.max_conn_retries:
                    logging.warning(f"Timeout on {url}, retrying in {cooldown_s}s...")
                    time.sleep(cooldown_s)
                else:
                    logging.error(f"Could not connect to {url}")
            except requests.exceptions.RequestException as e:
                logging.error(f"{e}")
                logging.error(f"Could not connect to {url}")
        return response


    def _format_likes(self, likes: str) -> int:
        likes = likes.strip()
        likes = likes.replace("likes", "")
        if ',' in likes:
            likes = likes.replace(',','')
        elif 'k' in likes:
            likes = likes.replace('k','')
            return int(float(likes) * 1000)
        return int(likes)
