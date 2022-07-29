# nisshi Ext - Articles

from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias, TypedDict, Any

from pathlib import PurePath
from os import remove, stat, stat_result
from os.path import exists

from functools import cache
from datetime import datetime

from nisshi import Manager as OriginalManager, Bundle, Context, PageContext
from nisshi.json import loads, dumps


__all__ = (
    "BundleContext", "Manager",
    "ArticlesConfig", "ArticleData", "ArticleContext", "ArticlePage", "Articles"
)


class ArticlesConfig(Context):
    "Context for storing data in article configuration files."

    time_format = r"%Y-%m-%d %H:%M:%S"
    "Time Format. Used in :meth:`Articles.format_time`."
    data_file_name = "articles.json"
    """This is the file that stores article data.
    This file is created in the folder containing the files that require article listings.
    Do not delete it."""
    markdown_format = "- [{title}]({file_name}) {description}  \n  *{created_at}*"
    'The format format used when ``"markdown_format"`` is passed as an argument to :meth:`ArticlePage.format_articles``.'
    html_format = '<li><a href="{file_name}">{title} {description}<br><em>{created_at}</em></li>'
    'The format format used when ``"html_format"`` is passed as an argument to :meth:`ArticlePage.format_articles``.'


class ArticleData(TypedDict):
    "The type of article data to be written to the data file in `nisshi.toml` (nisshi's config file)."

    title: str
    "Article title."
    description: str
    "Article description."
    created_at: float
    "The date the article was created."
    last_updated_at: float
    "The last update date of the article."
    file_name: str
    "The name of the article file."


class ArticleContext(PageContext):
    "Class of the context to be assigned to :attr:`ArticleContext.ctx`."

    description: str = ""
    "Article description."
    created_at: float = 0.0
    "The date and time the article was created. Defaults to ``0.0``, where ``0.0`` is automatically assigned the date and time the article file was created."
    last_updated_at: float = 0.0
    "The date the article was last modified. Defaults to ``0.0``, where ``0.0`` is automatically assigned the last modified date of the article file."


class ArticlePage(OriginalManager.page_cls):
    "Extended :class:`nisshi.page.Page` for article system."

    context_cls = ArticleContext
    manager: Manager
    _stat: stat_result
    _contain_articles = False

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._stat = stat(self.input_path)
        self.ctx.created_at = self.ctx.created_at or self._stat.st_birthtime
        self.ctx.last_updated_at = self.ctx.last_updated_at or self._stat.st_mtime

    @property
    def articles_bundle(self) -> Articles:
        "Alias for ``.manager.bundles.Articles``."
        return self.manager.bundles.Articles

    @property
    def articles(self) -> list[ArticleData]:
        "Retrieve article data."
        # 記事一覧を入れる必要があるファイルとしてキャッシュしておく。
        if self.input_path.parent not in self.manager.caches.articles:
            self.manager.caches.articles[raw_parent := str(self.input_path.parent)] = []
        else:
            raw_parent = str(self.input_path.parent)
        if self.input_path.name not in self.manager.caches.articles[raw_parent]:
            self.manager.caches.articles[raw_parent].append(self.input_path.name)

        self._contain_articles = True

        if self.articles_bundle._is_ready:
            return self.articles_bundle._data
        else:
            self.articles_bundle._input_directory = self.input_path.parent
            return self.articles_bundle._load()[1]

    def format_articles(self, format_type: str = "markdown_format") -> str:
        """Format and retrieve a list of article data.

        Args:
            key: Formatting is done using the formatting method in :class:`ArticlesConfig`.
                Replaces the value in :class:`ArticleData`.
                For example, if you put ``{title}``, it will be replaced with the title of the article."""
        articles = []
        for article in self.articles:
            articles.append(article.copy())
            for key in ("created_at", "last_updated_at"):
                articles[-1][key] = self.articles_bundle.format_time(article[key]) # type: ignore
        return "\n".join(
            self.articles_bundle.config[format_type].format(**article)
            for article in articles
        )


# バンドルの型付けを行う。
class BundleContext(Context):
    """Type for attribute ``bundles`` to store bundles of :class:`Manager`.
    The :class:`Context` with the type of the bundle to be added there for sure."""

    Articles: Articles
class Manager(OriginalManager):
    "Bundle typed :class:`nisshi.manager.Manager`."

    bundles: BundleContext
    if TYPE_CHECKING:
        page_cls: TypeAlias = ArticlePage


class Articles(Bundle):
    """This bundle is used to configure the article system.
    This bundle is automatically added when the article system extension is loaded.

    Args:
        manager: The manager instance."""

    def __init__(self, manager: Manager) -> None:
        self.manager = manager

        self.config = ArticlesConfig(self.manager.config.get("articles", {}))
        if "articles" not in self.manager.caches:
            self.manager.caches.articles = {}

        self._input_directory: PurePath | None = None
        self._data: list[ArticleData] = []
        self._stack: list[ArticlePage] = []
        self._cleaned: list[tuple[PurePath, PurePath]] = []
        self._is_ready = False

    @cache
    def format_time(self, time_: int) -> str:
        """Format the timestamp passed.

        Args:
            time_: The timestamp."""
        return datetime.fromtimestamp(time_) \
            .strftime(self.config.time_format)

    def _load(self) -> tuple[PurePath, list[ArticleData]]:
        # 記事データを読み込みます。これが呼ばれる時は`._input_directory`が`None`ではない必要があります。
        assert self._input_directory is not None
        if exists(data_path := self._input_directory.joinpath(self.config.data_file_name)):
            with open(data_path, "r") as f:
                data = loads(f.read())
        else:
            data = []
        return data_path, data

    def _process(self) -> None:
        if self._input_directory is None or (
            (raw_parent := str(self._input_directory)) not in self.manager.caches.articles
        ):
            self._stack.clear()
            return
        if not self._stack:
            return
        assert self._input_directory is not None

        # 集めたデータをJSONでしまえる形にまとめる。
        self._data = [
            ArticleData(
                title=page.ctx.title, description=page.ctx.description,
                created_at=page.ctx.created_at,
                last_updated_at=page.ctx.last_updated_at,
                file_name=page.output_path.name
            ) for page in self._stack
        ]
        self._stack.clear()

        # JSONファイルとマージする。
        data: list[ArticleData]
        data_path, data = self._load()
        for index, item in enumerate(data):
            for new_index, new in enumerate(self._data):
                if item["file_name"] == new["file_name"]:
                    data[index] = new
                    del self._data[new_index]
                    break
        data.extend(self._data)
        self._data = data
        self._data = sorted(self._data, key=lambda p: p["created_at"], reverse=True)
        self._write(data_path)

        # 記事一覧を更新する。
        self._rebuild_files_with_articles_list(raw_parent)

        self._data.clear()

    def _write(self, data_path: str | PurePath) -> None:
        # データを書き込む。
        if self._data:
            with open(data_path, "w") as f:
                f.write(dumps(self._data))
        else:
            remove(data_path)

    def _rebuild_files_with_articles_list(self, raw_parent: str) -> None:
        # 記事一覧を必要とするファイルのビルドを行います。これを実行する時は、`._input_directory`が`None`ではない必要があります。
        assert self._input_directory
        self._is_ready = True
        print(1)
        self.manager.console.log(
            "Now that the `%s` has been updated, rebuild the files with the article list."
            % raw_parent
        )
        for file_name in self.manager.caches.articles[raw_parent]:
            self.manager.build(self._input_directory.joinpath(file_name), True)
        self._is_ready = False

    @Bundle.listen()
    def on_after_build_page(self, page: ArticlePage):
        if page.ctx.description and not page._contain_articles:
            self._stack.append(page)
        if not self.manager.is_building_all:
            self._input_directory = page.input_path.parent
            self._process()

    @Bundle.listen()
    def on_after_build_directory(self, input_directory: PurePath, _) -> None:
        self._input_directory = input_directory
        self._process()

    @Bundle.listen()
    def on_after_build_all(self) -> None:
        # 削除されたファイルに関連するデータを消す。
        for input_path, output_path in self._cleaned:
            index_found = False

            if (raw_parent := str(input_path.parent)) in self.manager.caches.articles:
                # キャッシュが存在するならキャッシュを消す。
                for index, file_name in enumerate(self.manager.caches.articles[raw_parent]):
                    for ext in self.manager.config.input_exts:
                        if file_name == input_path.with_suffix(f".{ext}").name:
                            del self.manager.caches.articles[raw_parent][index]
                            index_found = True
                            break
                    else:
                        continue
                    break
                if index_found:
                    continue

                # 記事データを消す。
                if exists(data_path := input_path.parent.joinpath(self.config.data_file_name)):
                    self._input_directory = input_path.parent
                    with open(data_path, "r") as f:
                        self._data = loads(f.read())
                    for index, item in enumerate(self._data):
                        if item["file_name"] == output_path.name:
                            del self._data[index]
                            break
                    else:
                        continue
                    self._write(data_path)
                    self._rebuild_files_with_articles_list(str(input_path.parent))
                    self._input_directory

        self._cleaned.clear()

    @Bundle.listen()
    def on_clean(
        self, input_path: PurePath | None,
        output_path: PurePath,
        is_directory: bool
    ) -> None:
        if is_directory:
            return
        if input_path is None:
            input_path = self.manager.swap_path(output_path, self.manager.config.input_folder)
        self._cleaned.append((input_path, output_path))
        if not self.manager.is_building_all:
            self.on_after_build_all()


def setup(manager: Manager) -> None:
    manager.add_bundle(Articles(manager))