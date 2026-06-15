"""
Final project implementation.
"""

import json
import shutil
from collections.abc import Iterable

# pylint: disable=unused-import
from pathlib import Path

from core_utils.article.article import Article
from final_project.constants import CONFIG_PATH
from final_project.scraping import crawlers, parsers
from lab_5_scraper.scraper import Config
from core_utils.constants import PROJECT_ROOT

CONFIG_PATH = PROJECT_ROOT / "final_project" / "scraping" / "configs"


def prepare_environment(base_paths: Iterable[Path | str]) -> None:
    """
    Create ASSETS_PATH folder if no created and remove existing folder.

    Args:
        base_path (pathlib.Path | str): Path where articles stores
    """
    base_paths = [Path(path) for path in base_paths]

    for path in base_paths:
        if path.exists():
            shutil.rmtree(path)

    for path in base_paths:
        path.mkdir(parents=True)

def run_scraping_pipeline(names: Iterable[str], corpus_path: Path) -> None:
    """
    Runs scraping pipeline.

    Scraps trough WEB with available crawlers and parsers and
    saves meta.json and raw.txt to assets path with corresponding
    names.
    """
    configs = {
        name: Config(CONFIG_PATH / f"{name}_config.json")
        for name in names
    }
    crawlers_instances = {
        # "sidnev": crawlers.SidnevCrawler(configs["sidnev"]),
        # "davtyan": crawlers.DavtyanCrawler(configs["davtyan"]),
        # "syvkova": crawlers.SivkovaCrawler(configs["syvkova"]),
        # "lobanceva": crawlers.LobancevaCrawler(configs["lobanceva"]),
        # "marutina": crawlers.MarutinaCrawler(configs["marutina"]),
        "gryaznova": crawlers.GryaznovaCrawler(configs["gryaznova"])
    }
    parsers_instances = {
        # "sidnev": parsers.SidnevParser,
        # "davtyan": parsers.DavtyanParser,
        # "syvkova": parsers.SivkovaParser,
        # "lobanceva": parsers.LobancevaParser,
        # "marutina": parsers.MarutinaParser,
        "gryaznova": parsers.GryaznovaParser
    }

    for name, config in configs.items():
        article_id = 1
        print(f"\n{name} scraping")
        crawler = crawlers_instances[name]
        crawler.find_articles()
        for article_url in crawler.urls:
            parser = parsers_instances[name](article_url, article_id, config)
            parsed_article = parser.parse()
            if isinstance(parsed_article, Article) and len(parsed_article.text) > 200:
                article_txt_name = f"{article_id}_raw.txt"
                with open(corpus_path / name / article_txt_name, "w", encoding="utf-8") as file:
                    file.write(parsed_article.text)
                article_json_name = f"{article_id}_meta.json"
                with open(corpus_path / name / article_json_name, "w", encoding="utf-8") as meta_file:
                    json.dump(
                        parsed_article.get_meta(),
                        meta_file,
                        indent=4,
                        ensure_ascii=False,
                        separators=(",", ": ")
                    )

                if article_id % 10 == 0:
                    print(f"{article_id} articles saved")
                article_id += 1
            else:
                print(f"WARNING | Can't be parsed: {article_url}")
        print(f"{article_id} articles saved")

 
def main(corpus_path: Path, dist_path: Path) -> None:
    """
    Generate conllu file for provided corpus of texts.

    Args:
        corpus_path (Path): Path to folder containing text files.
        dist_path (Path): Path to folder for saving auto_annotated.conllu.
    """
    names = [
        # "sidnev",
        # "davtyan",
        # "syvkova",
        # "lobanceva",
        # "marutina",
        "gryaznova"
    ]
    prepare_environment([corpus_path / name for name in names])
    run_scraping_pipeline(names, corpus_path)


    result = None
    assert result, "Result is None"


if __name__ == "__main__":
    main(Path(__file__).parent / "assets" / "articles", Path(__file__).parent / "dist")
