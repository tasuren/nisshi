# nisshi - Main

from os.path import exists

from http.server import HTTPServer, SimpleHTTPRequestHandler

import click

from nisshi import __version__, Manager, Config
from nisshi.config import CURRENT


from sys import path
path.append(CURRENT)


def _build(
    config_file: str, hot_reload: bool,
    address: tuple[str, int] = ("", 0)
):
    # ビルドをします。また、ホットリロードやサーバーの立ち上げをします。
    manager = Manager(Config.from_file(config_file, True))
    manager.console.quiet = False

    if exists(manager.config.script_folder):
        manager.load_extension(manager.config.script_folder)

    if hot_reload:
        manager.build_all()
        # ファイル監視をするための設定をする。
        if address is None:
            manager.build_hot_reload()
        else:
            manager.console.log("Starting web server: http://%s:%s" % address)
            class PatchedHTTPRequestHandler(SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    kwargs["directory"] = manager.config.output_folder
                    super().__init__(*args, **kwargs)
                def log_message(self, format, *args):
                    manager.console.log("Serve", self.address_string(), (format % args))
            app = HTTPServer(address, PatchedHTTPRequestHandler)
            manager.build_hot_reload(app.serve_forever)
            app.shutdown()
    else:
        manager.build_all()


@click.group(invoke_without_command=True)
@click.option("-v", "--version", default=False, is_flag=True, help="Displays the version.")
def cli(version: bool):
    "A simple static website generator made in Python."
    if version:
        print(f"nisshi v{__version__}")


@cli.command()
@(_config_file_option := click.option(
    "--config-file", type=click.Path(dir_okay=False, readable=True),
    default="nisshi.toml", help="The path to the configuration file."
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


def main():
    cli()


main()