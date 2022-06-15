# PySSG - Main

from http.server import HTTPServer, SimpleHTTPRequestHandler

import click

from pyssg import __version__, Manager, Page, Config


def _build(config_file: str, hot_reload: bool, address: tuple[str, int] | None = None):
    # ビルドをします。また、ホットリロードやサーバーの立ち上げをします。
    manager = Manager[Page](Config.from_file(config_file))
    manager.console.quiet = False

    if hot_reload:
        # ファイル監視をするための設定をする。
        if address is None:
            manager.build_hot_reload()
        else:
            class PatchedHTTPRequestHandler(SimpleHTTPRequestHandler):
                def log_message(self, format, *args):
                    manager.console.log("Serve", self.address_string(), (format % args)[:-2])
            app = HTTPServer(address, PatchedHTTPRequestHandler)
            manager.build_hot_reload(app.serve_forever)
            app.shutdown()
    else:
        manager.build()


@click.group(invoke_without_command=True)
@click.option("-v", "--version", default=False, is_flag=True, help="Displays the version.")
def cli(version: bool):
    "A simple static website generator made in Python."
    if version:
        print(f"PySSG v{__version__}")


@cli.command()
@(_config_file_option := click.option(
    "--config-file", type=click.Path(exists=True, dir_okay=False, readable=True),
    default="pyssg.toml", help="The path to the configuration file."
))
@click.option(
    "--hot-reload", default=False, is_flag=True,
    help="Automatically builds when changes are made to the contents of the source folder."
)
def build(config_file: str, hot_reload: bool):
    "All markdowns in the source folder are converted to HTML and output to the output folder."
    _build(config_file, hot_reload)


@cli.command()
@_config_file_option
@click.option("-p", "--port", help="The port.", default=8000)
@click.option("-h", "--host", help="The host.", default="127.0.0.1")
def serve(config_file: str, port: int, host: str):
    "Run HTTP servers simultaneously using `http.server` from the standard Python library."
    _build(config_file, True, (host, port))


cli()