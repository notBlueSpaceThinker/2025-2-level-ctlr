"""
Pipeline for CONLL-U formatting.
"""

# pylint: disable=too-few-public-methods, unused-import, undefined-variable, too-many-nested-blocks
import json
import pathlib
import re

from networkx import DiGraph

from core_utils.article.article import Article, get_article_id_from_filepath
from core_utils.constants import ASSETS_PATH
from core_utils.article.io import from_raw, from_meta
from core_utils.pipeline import (
    AbstractCoNLLUAnalyzer,
    CoNLLUDocument,
    LibraryWrapper,
    PipelineProtocol,
    TreeNode,
    UnifiedCoNLLUDocument,
)

class InconsistentDatasetError(Exception):
    """
    Raised when IDs contain slips,
    number of meta and raw files is not equal,
    files are empty.
    """
class EmptyDirectoryError(Exception):
    """
    Raised when directory is empty.
    """

class CorpusManager:
    """
    Work with articles and store them.
    """

    def __init__(self, path_to_raw_txt_data: pathlib.Path) -> None:
        """
        Initialize an instance of the CorpusManager class.

        Args:
            path_to_raw_txt_data (pathlib.Path): Path to raw txt data
        """
        self.path_to_raw_txt_data = path_to_raw_txt_data
        self._storage = {}
        self._validate_dataset()
        self._scan_dataset()

    def _validate_dataset(self) -> None:
        """
        Validate folder with assets.
        """
        if not self.path_to_raw_txt_data.exists():
            raise FileNotFoundError(
                "File does not exist"
            )

        if not self.path_to_raw_txt_data.is_dir():
            raise NotADirectoryError(
                "Path does not lead to directory"
            )

        found_files: dict[str, list] = {}
        for file_path in self.path_to_raw_txt_data.iterdir():
            file_name = file_path.name

            if re.match(r"\d*_raw\.txt|\d*_meta\.json", file_name):
                if not file_path.stat().st_size:
                    raise InconsistentDatasetError(
                        f"File is empty: {file_name}"
                    )
                id, file_type = file_name.split("_")
                found_files.setdefault(file_type, []).append(int(id))

        if not found_files:
            raise EmptyDirectoryError(
                "Directory is empty"
            )

        raw_ids = found_files.get("raw.txt")
        meta_ids = found_files.get("meta.json")
        if not raw_ids:
            raise InconsistentDatasetError(
                "Dataset contains no raw files"
            )
        if not meta_ids:
            raise InconsistentDatasetError(
                "Dataset contains no meta files"
            )
        if len(meta_ids) != len(raw_ids):
            raise InconsistentDatasetError(
                "Number of meta and raw files is not equal"
            )
        if len(raw_ids) != sorted(raw_ids)[-1]:
            raise InconsistentDatasetError(
                "Raw file IDs contain slips"
            )
        if len(meta_ids) != sorted(meta_ids)[-1]:
            raise InconsistentDatasetError(
                "Meta file IDs contain slips"
            )


    def _scan_dataset(self) -> None:
        """
        Register each dataset entry.
        """
        for meta_file_path in self.path_to_raw_txt_data.glob("*_meta.json"):
            article_id = get_article_id_from_filepath(meta_file_path)
            self._storage[article_id] = from_meta(meta_file_path, Article(None, article_id))
        for raw_file_path in self.path_to_raw_txt_data.glob("*_raw.txt"):
            article_id = get_article_id_from_filepath(raw_file_path)
            self._storage[article_id] = from_raw(raw_file_path, self._storage[article_id])


    def get_articles(self) -> dict:
        """
        Get storage params.

        Returns:
            dict: Storage params
        """
        return self._storage


class TextProcessingPipeline(PipelineProtocol):
    """
    Preprocess and morphologically annotate sentences into the CONLL-U format.
    """

    def __init__(
        self, corpus_manager: CorpusManager, analyzer: LibraryWrapper | None = None
    ) -> None:
        """
        Initialize an instance of the TextProcessingPipeline class.

        Args:
            corpus_manager (CorpusManager): CorpusManager instance
            analyzer (LibraryWrapper | None, optional): Analyzer instance. Defaults to None.
        """

    def run(self) -> None:
        """
        Perform basic preprocessing and write processed text to files.
        """


class UDPipeAnalyzer(LibraryWrapper):
    """
    Wrapper for udpipe library.
    """

    #: Analyzer
    _analyzer: AbstractCoNLLUAnalyzer

    def __init__(self) -> None:
        """
        Initialize an instance of the UDPipeAnalyzer class.
        """

    def _bootstrap(self) -> AbstractCoNLLUAnalyzer:
        """
        Load and set up the UDPipe model.

        Returns:
            AbstractCoNLLUAnalyzer: Analyzer instance
        """

    def analyze(self, texts: list[str]) -> list[CoNLLUDocument | str]:
        """
        Process texts into CoNLL-U formatted markup.

        Args:
            texts (list[str]): Collection of texts

        Returns:
            list[CoNLLUDocument | str]: List of documents
        """

    def to_conllu(self, article: Article) -> None:
        """
        Save content to ConLLU format.

        Args:
            article (Article): Article containing information to save
        """

    def from_conllu(self, article: Article) -> CoNLLUDocument:
        """
        Load ConLLU content from article stored on disk.

        Args:
            article (Article): Article to load

        Returns:
            CoNLLUDocument: Document ready for parsing
        """

    def get_document(self, doc: CoNLLUDocument) -> UnifiedCoNLLUDocument:
        """
        Present ConLLU document's sentence tokens as a unified structure.

        Args:
            doc (CoNLLUDocument): ConLLU document

        Returns:
            UnifiedCoNLLUDocument: Dictionary of token features within document sentences
        """


class POSFrequencyPipeline:
    """
    Count frequencies of each POS in articles, update meta info and produce graphic report.
    """

    def __init__(self, corpus_manager: CorpusManager, analyzer: LibraryWrapper) -> None:
        """
        Initialize an instance of the POSFrequencyPipeline class.

        Args:
            corpus_manager (CorpusManager): CorpusManager instance
            analyzer (LibraryWrapper): Analyzer instance
        """

    def _count_frequencies(self, article: Article) -> dict[str, int]:
        """
        Count POS frequency in Article.

        Args:
            article (Article): Article instance

        Returns:
            dict[str, int]: POS frequencies
        """

    def run(self) -> None:
        """
        Visualize the frequencies of each part of speech.
        """


class PatternSearchPipeline(PipelineProtocol):
    """
    Search for the required syntactic pattern.
    """

    def __init__(
        self, corpus_manager: CorpusManager, analyzer: LibraryWrapper, pos: tuple[str, ...]
    ) -> None:
        """
        Initialize an instance of the PatternSearchPipeline class.

        Args:
            corpus_manager (CorpusManager): CorpusManager instance
            analyzer (LibraryWrapper): Analyzer instance
            pos (tuple[str, ...]): Root, Dependency, Child part of speech
        """

    def _make_graphs(self, doc: CoNLLUDocument) -> list[DiGraph]:
        """
        Make graphs for a document.

        Args:
            doc (CoNLLUDocument): Document for patterns searching

        Returns:
            list[DiGraph]: Graphs for the sentences in the document
        """

    def _add_children(
        self, graph: DiGraph, subgraph_to_graph: dict, node_id: int, tree_node: TreeNode
    ) -> None:
        """
        Add children to TreeNode.

        Args:
            graph (DiGraph): Sentence graph to search for a pattern
            subgraph_to_graph (dict): Matched subgraph
            node_id (int): ID of root node of the match
            tree_node (TreeNode): Root node of the match
        """

    def _find_pattern(self, doc_graphs: list) -> dict[int, list[TreeNode]]:
        """
        Search for the required pattern.

        Args:
            doc_graphs (list): A list of graphs for the document

        Returns:
            dict[int, list[TreeNode]]: A dictionary with pattern matches
        """

    def run(self) -> None:
        """
        Search for a pattern in documents and writes found information to JSON file.
        """


def main() -> None:
    """
    Entrypoint for pipeline module.
    """
    CorpusManager(ASSETS_PATH)


if __name__ == "__main__":
    main()
    # pattern = r"\d*_raw\.txt|\d*_meta\.json"
    # print(re.match(pattern,"1_22meta.json"))
