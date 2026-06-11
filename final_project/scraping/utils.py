import json
import random
import re
import time
from pathlib import Path

import requests

from core_utils.config_dto import ConfigDTO


class IncorrectSeedURLError(Exception):
    """
    Raised when seed URL does not match standard pattern 'https?://(www.)?'
    """

class NumberOfArticlesOutOfRangeError(Exception):
    """
    Raised when total number of articles is out of range from 1 to 150
    """

class IncorrectNumberOfArticlesError(Exception):
    """
    Raised when total number of articles to parse is not integer or less than 0
    """

class IncorrectHeadersError(Exception):
    """
    Raised when headers are not in a form of dictionary
    """

class IncorrectEncodingError(Exception):
    """
    Raied when encoding is not specified as a string
    """

class IncorrectTimeoutError(Exception):
    """
    Raised when timeout value is not a positive integer that less than 60
    """

class IncorrectVerifyError(Exception):
    """
    Raised when verify certificate and headless mode values are not True or False
    """

class Config:
    """
    Class for unpacking and validating configurations.
    """

    def __init__(self, path_to_config: Path) -> None:
        """
        Initialize an instance of the Config class.

        Args:
            path_to_config (pathlib.Path): Path to configuration.
        """
        self.path_to_config = path_to_config
        config_dto = self._extract_config_content()
        self._validate_config_content()

        self._seed_urls = config_dto.seed_urls
        self._num_articles = config_dto.total_articles
        self._headers = config_dto.headers
        self._encoding = config_dto.encoding
        self._timeout = config_dto.timeout
        self._should_verify_certificate = config_dto.should_verify_certificate
        self._headless_mode = config_dto.headless_mode

    def _extract_config_content(self) -> ConfigDTO:
        """
        Get config values.

        Returns:
            ConfigDTO: Config values
        """
        with open(self.path_to_config, encoding="utf-8") as config_data:
            self._config = ConfigDTO(**json.load(config_data))
        return self._config

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters are not corrupt.
        """
        config = self._config

        if not isinstance(config.seed_urls, list) or not config.seed_urls:
            raise IncorrectSeedURLError(
                "Seed URLs must be a list of strings"
            )

        for url in config.seed_urls:
            if not isinstance(url, str) or not re.match(r"https?://(www.)?", url):
                raise IncorrectSeedURLError(
                    "Seed URL does not match standard pattern 'https?://(www.)?'"
                )

        if not isinstance(config.total_articles, int) or config.total_articles <= 0:
            raise IncorrectNumberOfArticlesError(
                "Total number of articles to parse is not integer or less than 0"
            )

        if config.total_articles < 1:
            raise NumberOfArticlesOutOfRangeError(
                "Total number of articles is out of range from 1 to 150"
            )

        if not isinstance(config.headers, dict):
            raise IncorrectHeadersError(
                "Headers are not in a form of dictionary"
            )

        if not isinstance(config.encoding, str):
            raise IncorrectEncodingError(
                "Encoding is not specified as a string"
            )

        if not isinstance(config.timeout, int) or config.timeout < 0 or config.timeout >= 60:
            raise IncorrectTimeoutError(
                "Timeout value is not a positive integer that less than 60"
            )

        if not isinstance(config.should_verify_certificate, bool) \
        or not isinstance(config.headless_mode, bool):
            raise IncorrectVerifyError(
                "Verify certificate and headless mode values are not True or False"
            )


    def get_seed_urls(self) -> list[str]:
        """
        Retrieve seed urls.

        Returns:
            list[str]: Seed urls
        """
        return self._seed_urls

    def get_num_articles(self) -> int:
        """
        Retrieve total number of articles to scrape.

        Returns:
            int: Total number of articles to scrape
        """
        return self._num_articles

    def get_headers(self) -> dict[str, str]:
        """
        Retrieve headers to use during requesting.

        Returns:
            dict[str, str]: Headers
        """
        return self._headers

    def get_encoding(self) -> str:
        """
        Retrieve encoding to use during parsing.

        Returns:
            str: Encoding
        """
        return self._encoding

    def get_timeout(self) -> int:
        """
        Retrieve number of seconds to wait for response.

        Returns:
            int: Number of seconds to wait for response
        """
        return self._timeout

    def get_verify_certificate(self) -> bool:
        """
        Retrieve whether to verify certificate.

        Returns:
            bool: Whether to verify certificate or not
        """
        return self._should_verify_certificate

    def get_headless_mode(self) -> bool:
        """
        Retrieve whether to use headless mode.

        Returns:
            bool: Whether to use headless mode or not
        """
        return self._headless_mode

    def set_seed_urls(self, seed_urls: list[str]) -> None:
        """
        Set seed urls to parse.

        Args:
            seed_urls (list[str]): New seed urls
        """
        self._seed_urls = seed_urls


def make_request(url: str, config: Config) -> requests.models.Response:
    """
    Deliver a response from a request with given configuration.

    Args:
        url (str): Site url
        config (Config): Configuration

    Returns:
        requests.models.Response: A response from a request
    """
    # time.sleep(random.uniform(0.5, 1))
    response = requests.get(
        url=url,
        headers=config.get_headers(),
        timeout=config.get_timeout(),
        verify=config.get_verify_certificate(),
        )

    return response
