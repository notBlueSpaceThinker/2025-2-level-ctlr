import re
from abc import ABC, abstractmethod
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Tag

from lab_5_scraper.scraper import Config, make_request


class BaseCrawler(ABC):
    """"
    Crawler implementation.
    """
    #: Url pattern
    url_pattern: re.Pattern | str
    
    def __init__(self, config: Config) -> None:
        """
        Initialize an instance of the Crawler class.

        Args:
            config (Config): Configuration
        """
        self._config = config
        self.urls = []

    @abstractmethod
    def _extract_url(self, article_bs: Tag) -> str:
        """
        Find and retrieve url from HTML.

        Args:
            article_bs (bs4.Tag): Tag instance

        Returns:
            str: Url from HTML
        """
        pass

    @abstractmethod
    def find_articles(self) -> None:
        """
        Find articles.
        """
        pass

    @abstractmethod
    def get_search_urls(self) -> list:
        """
        Get seed_urls param.

        Returns:
            list: seed_urls param
        """
        pass


class SidnevCrawler(BaseCrawler):
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.navigation_urls = set()

    def _extract_url(self, article_bs: Tag) -> str:
        """
        Find and retrieve url from HTML.

        Args:
            article_bs (bs4.Tag): Tag instance

        Returns:
            str: Url from HTML
        """
        url = article_bs.get("href")
        return "" if not isinstance(url, str) or not url else url

    def find_articles(self) -> None:
        """
        Find articles.
        """
        navigation_page_marks = {
            "category",
            "tag",
            "page",
        }

        for seed_url in self.get_search_urls():
            try:
                response = make_request(seed_url, self._config)
            except requests.exceptions.RequestException:
                continue

            if not response.ok:
                continue

            soup = BeautifulSoup(response.text, features="lxml")
            parsed_seed = urlparse(seed_url)

            for tag in soup.find_all(["a"]):
                if len(self.urls) > self._config.get_num_articles():
                    return

                extracted_url = self._extract_url(tag)
                if not extracted_url:
                    continue

                if not re.match("https?://(www.)?", extracted_url):
                    extracted_url = urlunparse(
                        (
                            parsed_seed.scheme,
                            parsed_seed.netloc,
                            extracted_url,
                            None,
                            None,
                            None
                        )
                    )
                elif parsed_seed.netloc != urlparse(extracted_url).netloc:
                    continue

                extracted_url = extracted_url.split('#')[0]
                if not extracted_url:
                    continue

                parsed_extracted = urlparse(extracted_url)
                if set(parsed_extracted.path.split('/')).intersection(navigation_page_marks):
                    self.navigation_urls.add(extracted_url)
                    continue

                if extracted_url not in self.urls and extracted_url not in self.get_search_urls():
                    self.urls.append(extracted_url)

    def get_search_urls(self) -> list:
        """
        Get seed_urls param.

        Returns:
            list: seed_urls param
        """
        return self._config.get_seed_urls()


class SivkovaCrawler(BaseCrawler):

    def _extract_url(self, article_bs: Tag) -> str:
        """
        Find and retrieve url from HTML.

        Args:
            article_bs (bs4.Tag): Tag instance

        Returns:
            str: Url from HTML
        """
        href = article_bs.get("href", "")
        if not href:
            return ""
        
        if href.startswith("http"):
            return href
        
        if href.startswith("/"):
            href = href[1:]
        
        return "https://scrapsfromtheloft.com/" + href

    def find_articles(self) -> None:
        """
        Find articles.
        """
        needed = self._config.get_num_articles()
        
        for seed_url in self._config.get_seed_urls():
            if len(self.urls) >= needed:
                break
            
            response = make_request(seed_url, self._config)
            if not response.ok:
                continue
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            all_links = soup.find_all('a')
            
            for link in all_links:
                if len(self.urls) >= needed:
                    break
                
                article_url = self._extract_url(link)
                
                if article_url and article_url not in self.urls:
                    self.urls.append(article_url)

    def get_search_urls(self) -> list:
        """
        Get seed_urls param.

        Returns:
            list: seed_urls param
        """
        return self._config.get_seed_urls()
    

class GryaznovaCrawler(BaseCrawler):

    def _extract_url(self, article_bs: Tag) -> str:
        """
        Find and retrieve url from HTML.
        """
        href = article_bs.get('href')
        if not href:
            return ''
            
        full_url = urljoin('https://royallib.com', str(href))
        
        if re.search(r'/(book|read)/', full_url):
            return str(full_url)
            
        return ''

    def find_articles(self) -> None:
        """
        Find articles.
        """
        to_visit = list(self._config.get_seed_urls())
        visited = set()
        max_pages = 100
        pages_processed = 0
        needed = self._config.get_num_articles()

        while len(self.urls) < needed and to_visit and pages_processed < max_pages:
            current_url = to_visit.pop(0)
            if current_url in visited:
                continue
            visited.add(current_url)
            pages_processed += 1

            try:
                response = make_request(current_url, self._config)
            except requests.exceptions.RequestException:
                continue

            soup = BeautifulSoup(response.text, 'lxml')

            for a in soup.find_all('a', href=True):
                if len(self.urls) >= needed:
                    break
                
                article_url = self._extract_url(a)
                if not article_url:
                    continue

                if "/book/" in article_url:
                    if article_url not in visited and article_url not in to_visit:
                        to_visit.append(article_url)
                elif "read" in article_url:
                    if article_url not in self.urls:
                        self.urls.append(article_url)

            if len(self.urls) < needed:
                next_link = soup.find('a', rel='next')
                if next_link and next_link.get('href'):
                    href = next_link.get('href')
                    if isinstance(href, str):
                        next_url = urljoin(current_url, href)
                        if next_url != current_url and next_url not in visited:
                            to_visit.append(next_url)
                            
        self.urls = self.urls[:needed]

    def get_search_urls(self) -> list:
        """
        Get seed_urls param.

        Returns:
            list: seed_urls param
        """

        return self._config.get_seed_urls()
    

class LobancevaCrawler(BaseCrawler):

    def _extract_url(self, article_bs: Tag) -> str:
        """
        Find and retrieve url from HTML.

        Args:
            article_bs (bs4.Tag): Tag instance

        Returns:
            str: Url from HTML
        """
        base_url = self._config.get_seed_urls()[0]
        if article_bs.name == "a" and article_bs.get("href"):
            href = article_bs.get("href")
            return urljoin(base_url, href)

        link = article_bs.find("a")
        if link and link.get("href"):
            return urljoin(base_url, link.get("href"))

        return ""

    def find_articles(self) -> None:
        """
        Find articles.
        """
        seed_urls = self._config.get_seed_urls()
        target_count = self._config.get_num_articles()

        for seed_url in seed_urls:
            if len(self.urls) >= target_count:
                break

            pages_to_process = [
                (seed_url, lambda s: s.find_all("a", class_="read-more")),
                (seed_url.rstrip("/") + "/archive_news",
                lambda s: s.find_all("a", string="подробнее")),
            ]

            for page_url, find_links in pages_to_process:
                if len(self.urls) >= target_count:
                    break

                try:
                    response = make_request(page_url, self._config)
                except requests.exceptions.RequestException as e:
                    print(f"Request failed: {e}")
                    continue

                if response.status_code != 200:
                    print(f"Warning: Could not fetch {page_url}, status {response.status_code}")
                    continue

                soup = BeautifulSoup(response.text, "html.parser")
                links = find_links(soup)

                for link in links:
                    url = self._extract_url(link)
                    if url and url not in self.urls:
                        self.urls.append(url)
                        print(f"Found {len(self.urls)}: {url}")
                        if len(self.urls) >= target_count:
                            break

        print(f"Total found: {len(self.urls)} article URLs (need {target_count})")


    def get_search_urls(self) -> list:
        """
        Get seed_urls param.

        Returns:
            list: seed_urls param
        """
        return self._config.get_seed_urls()
    
class MarutinaCrawler(BaseCrawler):

    def _extract_url(self, article_bs: Tag) -> str:
        """
        Find and retrieve url from HTML.

        Args:
            article_bs (bs4.Tag): Tag instance

        Returns:
            str: Url from HTML
        """
        href = article_bs.get("href", "")
        if not isinstance(href, str):
            return ""
        if not href:
            return ""
        if href.startswith("http"):
            return href
        return "https://old.mxat.ru/" + href.lstrip('/')

    def find_articles(self) -> None:
        """
        Find articles.
        """
        for seed_url in self._config.get_seed_urls():
            try:
                response = make_request(seed_url, self._config)
            except requests.RequestException:
                continue
            if not response.ok:
                continue
            soup = BeautifulSoup(response.text, "lxml")
            for tag in soup.find_all("a", href=True):
                href = tag.get("href", "").strip()
                skip_patterns = ["search", "award", "javascript:", "#"]
                if not href or any(x in href.lower() for x in skip_patterns):
                    continue
                if any(x in href for x in ["/press/", "/news/", "/history/", "/details/"]):
                    full_url = self._extract_url(tag)
                    if (
                        "performance" in full_url.lower() 
                        or "project" in full_url.lower()
                        or full_url.endswith("/history/")
                    ):
                        continue
                    if full_url and full_url not in self.urls:
                        self.urls.append(full_url)
                if len(self.urls) >= self._config.get_num_articles():
                    return

    def get_search_urls(self) -> list:
        """
        Get seed_urls param.

        Returns:
            list: seed_urls param
        """
        return self._config.get_seed_urls()
    

class DavtyanCrawler(BaseCrawler):
    """
    Crawler implementation.
    """

    #: Url pattern
    url_pattern: re.Pattern | str

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self._nav_page_markers = [
            "library",
            "ural.html",
            "novyi_mi.html",
            "nj.html",
            "bereg.html",
            "nov_yun.html",
            "nlo.html",
            "nz.html",
            "neva.html",
            "kreschatik.html",
            "interpoezia.html",
            "inostran.html",
            "ier.html",
            "znamia.html",
            "zin.html",
            "zin.html",
            "zerkalo.html",
            "zvezda.html",
            "druzhba.html",
            "ra.html",
            "volga.html",
            "vestnik.html",
            "prosodia.html",
            "a.html",
            "sp.html",
            "homo_legens.html",
            "arion.html",
            "volga21.html",
            "din.html",
            "zz.html",
            "continent.html",
            "km.html",
            "logos.html",
            "nrk.html",
            "nlik.html",
            "october.html",
            "oz.html",
            "sib.html",
            "slovo.html",
            "slo.html",
            "studio.html",
            "urnov.html",
            "legal-info.html",
            "contacts.html"
        ]

    def _extract_url(self, article_bs: Tag) -> str:
        """
        Find and retrieve url from HTML.

        Args:
            article_bs (bs4.Tag): Tag instance

        Returns:
            str: Url from HTML
        """
        url = article_bs.get("href")
        return "" if not isinstance(url, str) or not url else url

    def find_articles(self) -> None:
        """
        Find articles.
        """
        for seed_url in self.get_search_urls():
            try:
                response = make_request(seed_url, self._config)
            except requests.exceptions.ConnectTimeout:
                # print(f"Failed to proceed: {seed_url}")
                continue
            if not response.ok:
                continue
            soup = BeautifulSoup(response.text, features="lxml")
            parsed_seed_url = urlparse(seed_url)
            for tag in soup.find_all(["a"]):
                if len(self.urls) > self._config.get_num_articles():
                    return
                extracted_url = self._extract_url(tag)
                if not extracted_url:
                    continue
                extracted_url = urljoin(seed_url, extracted_url)
                if re.search(r"/\d+\.html", extracted_url):
                    continue
                if parsed_seed_url.netloc != urlparse(extracted_url).netloc:
                    continue
                if any(nav_mark in extracted_url for nav_mark in self._nav_page_markers):
                    continue
                if extracted_url not in self.urls and extracted_url not in self.get_search_urls():
                    try:
                        check_response = make_request(extracted_url, self._config)
                    except requests.exceptions.ConnectTimeout:
                        continue
                    if check_response.ok:
                        print(f"Added: {extracted_url} | Urls: {len(self.urls)}")
                        self.urls.append(extracted_url)

    def get_search_urls(self) -> list:
        """
        Get seed_urls param.

        Returns:
            list: seed_urls param
        """
        return self._config.get_seed_urls()
