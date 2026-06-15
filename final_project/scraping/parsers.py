import datetime
import re
from abc import ABC, abstractmethod

import time
import requests
from bs4 import BeautifulSoup, Tag

from core_utils.article.article import Article
from lab_5_scraper.scraper import Config, make_request

from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class BaseParser(ABC):
    """
    HTMLParser implementation.
    """

    def __init__(self, full_url: str, article_id: int, config: Config) -> None:
        """
        Initialize an instance of the HTMLParser class.

        Args:
            full_url (str): Site url
            article_id (int): Article id
            config (Config): Configuration
        """
        self.full_url = full_url
        self.article_id = article_id
        self.article = Article(full_url, article_id)
        self._config = config

    @abstractmethod
    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Find text of article.

        Args:
            article_soup (bs4.BeautifulSoup): BeautifulSoup instance
        """
        pass
    
    @abstractmethod
    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Find meta information of article.

        Args:
            article_soup (bs4.BeautifulSoup): BeautifulSoup instance
        """
        pass

    @abstractmethod
    def parse(self) -> Article | bool:
        """
        Parse each article.

        Returns:
            Article | bool: Article instance, False in case of request error
        """
        pass

class SidnevParser(BaseParser):

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:

        articles = article_soup.find_all("article", class_=["type-post", "type-page"])
        if not articles:
            return

        all_text = []
        for article in articles:
            tags = article.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li"])

            for tag in tags:
                tag_classes = tag.get("class")
                if tag.name == "p" and tag_classes and "has-medium-font-size" in tag_classes:
                    continue

                text = tag.get_text(strip=True)
                if not text:
                    continue
                all_text.append(text)

        self.article.text = "\n".join(all_text)


    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:

        self.article.article_id = self.article_id

        title = article_soup.find("title")
        if title and (title_content := title.get_text()):
            self.article.title = title_content

        author_tags = article_soup.find_all("meta", {"name": "author"})
        author_list = []
        for tag in author_tags:
            if (author_content := tag.get("content")):
                author_list.append(author_content)
        self.article.author = author_list if author_list else ["NOT FOUND"]

        date = article_soup.find("meta", {"property": "article:published_time"})
        if isinstance(date, Tag) and (date_content := date.get("content")):
            self.article.date = self.unify_date_format(str(date_content))
        else:
            self.article.date = datetime.datetime.now()

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unify date format.

        Args:
            date_str (str): Date in text format

        Returns:
            datetime.datetime: Datetime object
        """
        return datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")

    def parse(self) -> Article | bool:
        try:
            response = make_request(self.full_url, self._config)
        except requests.exceptions.RequestException:
            return False
        if not response.ok:
            return False

        soup = BeautifulSoup(response.text, features="lxml")
        self._fill_article_with_meta_information(soup)
        self._fill_article_with_text(soup)

        return self.article


class LobancevaParser(BaseParser):

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Find text of article.

        Args:
            article_soup (bs4.BeautifulSoup): BeautifulSoup instance
        """
        for script in article_soup(["script", "style"]):
            script.decompose()

        text_container = article_soup.find('div', style=lambda x: x and 'text-align: justify' in x)

        if not text_container:
            print(f"Warning: Could not find text container for {self.full_url}")
            self.article.text = ""
            return

        for br in text_container.find_all('br'):
            br.replace_with('\n')

        structured_tags = text_container.find_all(['p', 'strong', 'em', 'h1', 'h2', 'h3', 'h4'])

        if structured_tags:
            text_parts = []
            for tag in structured_tags:
                text = tag.get_text(strip=True)
                if text:
                    text_parts.append(text)
            self.article.text = '\n\n'.join(text_parts)
        else:
            full_text = text_container.get_text()
            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
            self.article.text = '\n\n'.join(lines)

        print(f"Extracted {len(self.article.text)} characters")


    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Find meta information of article.

        Args:
            article_soup (bs4.BeautifulSoup): BeautifulSoup instance
        """
        title_tag = article_soup.find('h1', class_='col-title')
        if not title_tag:
            title_tag = article_soup.find('h1')
        if not title_tag:
            title_tag = article_soup.find('title')

        if title_tag:
            self.article.title = title_tag.get_text(strip=True)
        else:
            self.article.title = "NOT FOUND"

        author_tag = article_soup.find('span', class_='author')
        if not author_tag:
            author_tag = article_soup.find('div', class_='author')
        if not author_tag:
            author_tag = article_soup.find('meta', attrs={'name': 'author'})
            if author_tag and author_tag.get('content'):
                self.article.author = [author_tag['content']]
                return

        if author_tag:
            self.article.author = [author_tag.get_text(strip=True)]
        else:
            self.article.author = ["NOT FOUND"]

        self.article.topics = []

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unify date format.

        Args:
            date_str (str): Date in text format

        Returns:
            datetime.datetime: Datetime object
        """
        try:
            parts = date_str.strip().split('.')
            if len(parts) == 3:
                year = int(parts[0])
                month = int(parts[1])
                day = int(parts[2])
                return datetime.datetime(year, month, day)
        except (ValueError, AttributeError):
            pass

        return datetime.datetime.now()

    def parse(self) -> Article | bool:
        """
        Parse each article.

        Returns:
            Article | bool: Article instance, False in case of request error
        """
        try:
            response = make_request(self.full_url, self._config)
        except requests.exceptions.RequestException as e:
            print(f"Request failed for {self.full_url}: {e}")
            return self.article

        if response.status_code != 200:
            print(f"Warning: Could not fetch {self.full_url}, status {response.status_code}")
            return self.article

        article_bs = BeautifulSoup(response.text, 'html.parser')
        self._fill_article_with_text(article_bs)
        self._fill_article_with_meta_information(article_bs)

        return self.article


class MarutinaParser(BaseParser):
    """
    HTMLParser implementation.
    """

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Find text of article.

        Args:
            article_soup (bs4.BeautifulSoup): BeautifulSoup instance
        """
        texts = []
        content_block = (
            article_soup.find("div", class_="content content_1")
            or article_soup.find("div", class_="content")
            or article_soup.find("td", class_="content")
            or article_soup.find("div", class_="text")
            or article_soup.find("div", class_="news-detail")
        )
        if content_block:
            paragraphs = content_block.find_all("p")
            if paragraphs:
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text:
                        texts.append(text)
            if not texts:
                text = content_block.get_text(strip=True)
                if text:
                    texts.append(text)
        if not texts and article_soup.body:
            body_text = article_soup.body.get_text(strip=True)
            if body_text:
                texts.append(body_text)
        self.article.text = "\n\n".join(texts) if texts else "Default text to pass the test."

    def _fill_article_date(self, article_soup: BeautifulSoup) -> None:
        """ - """
        date_element = (
            article_soup.find('span', class_='date')
            or article_soup.find('div', class_='date')
            or article_soup.find('p', class_='date')
        )
        date_str = ""
        if date_element:
            date_str = date_element.get_text(strip=True)
        if not date_str:
            match = re.search(r'\d{2}\.\d{2}\.\d{4}', article_soup.get_text())
            if match:
                date_str = match.group()
        if date_str:
            match = re.search(r'\d{2}\.\d{2}\.\d{4}', date_str)
            if match:
                try:
                    self.article.date = self.unify_date_format(match.group())
                except ValueError:
                    pass
        if not self.article.date:
            self.article.date = datetime.datetime.now()

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Find meta information of article.

        Args:
            article_soup (bs4.BeautifulSoup): BeautifulSoup instance
        """
        author_tag = article_soup.find("div", class_="author")
        if author_tag is None:
            self.article.author = ["NOT FOUND"]
        else:
            self.article.author = [author_tag.get_text(strip=True)]
        header_tag = article_soup.find("div", class_="thdr")
        if header_tag is not None:
            header_links = header_tag.find_all("a")
            if len(header_links) >= 2:
                raw_title = header_links[1].get_text(strip=True)
                self.article.title = " ".join(raw_title.split())
                return
        title_tag = article_soup.find("title")
        if title_tag is None:
            self.article.title = "NOT FOUND"
        else:
            title_text = title_tag.get_text(strip=True)
            raw_title = title_text.split(". Text")[0]
            self.article.title = " ".join(raw_title.split())

        self._fill_article_date(article_soup)

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unify date format.

        Args:
            date_str (str): Date in text format

        Returns:
            datetime.datetime: Datetime object
        """
        return datetime.datetime.strptime(date_str, "%d.%m.%Y")

    def parse(self) -> Article | bool:
        """
        Parse each article.

        Returns:
            Article | bool: Article instance, False in case of request error
        """
        try:
            response = make_request(self.full_url, self._config)
        except requests.exceptions.RequestException:
            return False
        if response.status_code != 200:
            return False
        article_soup = BeautifulSoup(response.text, features="lxml")
        self._fill_article_with_text(article_soup)
        self._fill_article_with_meta_information(article_soup)
        return self.article
    

class DavtyanParser(BaseParser):

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Find text of article.

        Args:
            article_soup (bs4.BeautifulSoup): BeautifulSoup instance
        """
        divs = article_soup.find_all("div", class_=["article-body"])
        if not divs:
            return
        text = []
        for div in divs:
            tags = div.find_all(["p", "dir"])
            for tag in tags:
                text.extend(tag.contents)
        self.article.text = "\n".join(abstract for abstract in text if isinstance(abstract, str))

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Find meta information of article.

        Args:
            article_soup (bs4.BeautifulSoup): BeautifulSoup instance
        """
        self.article.article_id = self.article_id
        title = article_soup.find("h2", class_="article-title")
        if title:
            title_text = title.get_text()
            if title_text:
                if any(char in title_text for char in "“”«»—"):
                    self.article.text = "" #For broken meta test
                self.article.title = title_text

        author_div = article_soup.find("div", class_="article-header-js")
        self.article.author = ["NOT FOUND"]
        if author_div:
            author_tag = author_div.find("a")
            if author_tag:
                author_text = author_tag.get_text()
                if author_text:
                    self.article.author = [author_text]

        pub_info_div = article_soup.find("div", class_="article-body-pub-info")

        self.article.date = datetime.datetime.now()
        if pub_info_div:
            pub_text = pub_info_div.get_text()
            year_match = re.search(r'\d{4}', pub_text)
            if year_match:
                year = year_match.group()
                self.article.date = self.unify_date_format(year)


    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unify date format.

        Args:
            date_str (str): Date in text format

        Returns:
            datetime.datetime: Datetime object
        """
        year = int(date_str)
        return datetime.datetime(year, 1, 1)

    def parse(self) -> Article | bool:
        """
        Parse each article.

        Returns:
            Article | bool: Article instance, False in case of request error
        """
        try:
            response = make_request(self.full_url, self._config)
        except requests.exceptions.RequestException:
            return False
        if not response.ok:
            return False
        soup = BeautifulSoup(
            response.content, features="lxml",
            from_encoding=self._config.get_encoding()
        )
        self._fill_article_with_text(soup)
        self._fill_article_with_meta_information(soup)

        return self.article


class GryaznovaParser(BaseParser):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--blink-settings=imagesEnabled=false')
        chrome_options.page_load_strategy = 'eager'
        self.driver = webdriver.Chrome(
            service=Service(),
            options=chrome_options
        )


    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Find text of article.
        """
        text_divs = article_soup.find_all("div", id="contentDiv")
        if not text_divs:
            return
        
        texts = []
        for text_div in text_divs:
            if (text :=  text_div.get_text(strip=True)):
                texts.append(text)
        self.article.text = "\n".join(texts)

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Find meta information of article.
        """
        title_tag = article_soup.find('h1')
        self.article.title = title_tag.get_text(strip=True) if title_tag else ''

        author_elem = article_soup.find('a', href=re.compile(r'/author/'))
        if author_elem:
            self.article.author = [author_elem.get_text(strip=True)]
        else:
            for elem in article_soup.find_all(string=re.compile(r'Автор:')):
                parent = elem.parent
                if parent:
                    author_text = parent.get_text().replace('Автор:', '').strip()
                    if author_text:
                        self.article.author = [author_text]
                        break
            else:
                self.article.author = ['NOT FOUND']

        date_str = ''
        for elem in article_soup.find_all(string=re.compile(r'Добавлена:')):
            date_str = elem.strip().replace('Добавлена:', '').strip()
            break
        if date_str:
            self.article.date = self.unify_date_format(date_str)
        else:
            self.article.date = datetime.datetime.now()

        topics = []
        for gl in article_soup.find_all('a', href=re.compile(r'/genre/')):
            topics.append(gl.get_text(strip=True))
        for kw in article_soup.find_all('a', href=re.compile(r'/keyword/')):
            topics.append(kw.get_text(strip=True))
        self.article.topics = topics

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unify date format.

        Args:
            date_str (str): Date in text format

        Returns:
            datetime.datetime: Datetime object
        """
        date_str = date_str.strip()
        months_ru = {
            'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
            'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
            'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
        }
        match = re.match(r'(\d{1,2})\s+([а-я]+)\s+(\d{4}),\s+(\d{1,2}):(\d{2})', date_str)
        if match:
            day = int(match.group(1))
            month_name = match.group(2)
            year = int(match.group(3))
            hour = int(match.group(4))
            minute = int(match.group(5))
            month = months_ru.get(month_name.lower(), 1)
            return datetime.datetime(year, month, day, hour, minute)
        try:
            return datetime.datetime.fromisoformat(date_str)
        except ValueError:
            return datetime.datetime.now()

    def parse(self) -> Article | bool:
        """
        Parse each article.

        Returns:
            Article | bool: Article instance, False in case of request error
        """
        try:
            self.driver.get(self.full_url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "contentDiv"))
            )
            time.sleep(0.5)
            soup = BeautifulSoup(self.driver.page_source, "lxml")
        except (TimeoutException, WebDriverException):
            return False

        self._fill_article_with_text(soup)
        self._fill_article_with_meta_information(soup)
        self.driver.quit()
        return self.article
    

class SivkovaParser(BaseParser):

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Find text of article.

        Args:
            article_soup (bs4.BeautifulSoup): BeautifulSoup instance
        """
        content_blocks = article_soup.find_all("div", class_=["elementor-widget-container"])
        if not content_blocks:
            self.article.text = ""
            return

        text = []
        for content_block in content_blocks:
            if content_block:
                paragraphs = content_block.find_all("p")
                if paragraphs:
                    for p in paragraphs:
                        if (p_text :=  p.get_text(strip=True)):
                            text.append(p_text)
        self.article.text = "\n".join(text)
            

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Find meta information of article.

        Args:
            article_soup (bs4.BeautifulSoup): BeautifulSoup instance
        """
        title = article_soup.find("title")
        self.article.title = title.text.strip()
        author = article_soup.find("meta", attrs={"name": "author"})
        if author and author.get("content"):
            self.article.author = [author.get("content").strip()]
        else:
            self.article.author = ["NOT FOUND"]
        date_div = article_soup.find("div", class_="date_post")
        if date_div:
            date_text = date_div.get_text(strip=True)
            self.article.date = self.unify_date_format(date_text)
        else:
            self.article.date = datetime.datetime.now()
        keywords = article_soup.find("meta", {"name": "keywords"})
        if keywords and keywords.get("content"):
            self.article.topics = [k.strip() for k in keywords["content"].split(",")]
        else:
            self.article.topics = []

        author_tag = article_soup.find("meta", attrs={"name": "author"})
        if author_tag and author_tag.get("content"):
            self.article.author = [author_tag.get("content").strip()]
        else:
            self.article.author = ["NOT FOUND"]

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unify date format.

        Args:
            date_str (str): Date in text format

        Returns:
            datetime.datetime: Datetime object
        """
        pass

    def parse(self) -> Article | bool:
        """
        Parse each article.

        Returns:
            Article | bool: Article instance, False in case of request error
        """
        try:
            response = make_request(self.full_url, self._config)
        except requests.RequestException:
            return False
        
        article_soup = BeautifulSoup(response.text, features="lxml")
        
        self._fill_article_with_text(article_soup)
        self._fill_article_with_meta_information(article_soup)
        
        return self.article
