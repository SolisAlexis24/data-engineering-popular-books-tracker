import requests
from bs4 import BeautifulSoup
import time
import re
import logging
from tqdm import tqdm


# Cabezeras para evitar que la conexion sea rechazada
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.goodreads.com",
}

# Expresion regular para el url de un libro
REGEX_BOOK_URL = r"https://www.goodreads.com/book/show/(\d+)[\w.\-]+$"
MOST_READ_BOOKS_URL = r"https://www.goodreads.com/book/most_read"


class most_read_scraper():
    """
    Clase que implementa un scraper para obtener informacion PUBLICA de la pagina goodreads 
    acerca de los libros mas populares cada semana publicados en la pagina MOST_READ_BOOKS_URL
    """
    def __init__(self, max_conn_retries = 3) -> None:
        self.most_read_url_list = []
        self.max_conn_retries = max_conn_retries
        self.books_data = []
        

    def scrape(self):
        if self._get_books_list() is False:
            logging.error("No se pudo obtener informacion de los libros")
            return

        for book in tqdm(self.most_read_url_list, desc="Scrapeando libros"):
            self.books_data.append(self._scrape_book(book))


    def _get_books_list(self) -> bool:
        """
        Obtiene las url relativas de los libros listados en la pagina "book/most_read"
        y los guarda en la lista most_read_url_list
        """
        base_book_url: str = "https://www.goodreads.com"
        session = requests.Session()
        session.headers.update(HEADERS)

        response = self._get_response(session, MOST_READ_BOOKS_URL)
        if response is None:
            self.most_read_url_list = []
            return False
    
        if response.status_code != 200:
            logging.error("No se ha obtenido la respuesta esperada para scrapeando most_read")
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
            Recolecta la informacion del libro proporcionado como parametro y sus resenas
            Devuelve un diccionario con el formato {"libro": info_libro, "reviews": info_reviews}
        """
        match = re.match(REGEX_BOOK_URL, URL)
        if not match:
            logging.error(f"El url {URL} es invalido, debes proporcionar el url del libro")
            return {}
        
        # El grupo de captura 1 es el ID del libro, (revisar REGEX_BOOK_URL)
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
            Obtiene la informacion del libro
            Devuelve los metadatos del libro en un diccionario
        """
        book_data = {"id":book_id,
                    "title":"", 
                    "author":"", 
                    "description":"" , 
                    "genres":[], 
                    "rating": None, 
                    "date": ""}
        # == Obteniendo los elementos HTML del libro ==
        title_element = soup.select_one("h1[data-testid='bookTitle']")
        author_element = soup.select_one("span.ContributorLink__name[data-testid='name']")
        description_element = soup.select_one("div[data-testid='description'] .Formatted")
        genres_element = soup.select("div[data-testid='genresList'] .Button__labelItem")
        rating_element = soup.select_one("div.RatingStatistics__rating")
        date_element = soup.select_one("p[data-testid='publicationInfo']")

        # == Extrayendo la informacion de los elementos ==
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
        Obtiene la informacion de las reseñas del libro
        Devuelve una lista con la informacion de las opiniones (texto y likes)
        """
        reviews = []

        for card in soup.select("article.ReviewCard"):
            text = None
            likes = None
            # == Obteniendo los elementos HTML de la opinion ==
            text_element = card.select_one(".ReviewText__content") 
            footer = card.select_one("footer.SocialFooter")
            
            # == Extrayendo la informacion de los elementos ==
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
            Obtiene los url a los libros de una seccion o genero 
            El link de la seccion o genero debe comenzar como:\n
            https://www.goodreads.com/shelf/show/\n
            A esta url base se le concatenara el genero que se indique
            en el parametro
        """
        base_genre_url: str = "https://www.goodreads.com/shelf/show/"
        base_book_url: str = "https://www.goodreads.com"
        session = requests.Session()
        session.headers.update(HEADERS)
        
        response = self._get_response(session, f"{base_genre_url} + {genre}")
        if response is None:
            return[]
        
        if response.status_code != 200:
            logging.error(f"No se ha obtenido la respuesta esperada para {genre}: \n {response.status_code}")
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
                    logging.warning(f"Timeout en {url}, reintentando en {cooldown_s}s...")
                    time.sleep(cooldown_s)
                else:
                    logging.error(f"No se pudo establecer conexión con {url}")
            except requests.exceptions.RequestException as e:
                logging.error(f"{e}")
                logging.error(f"No se pudo establecer conexión con {url}")
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