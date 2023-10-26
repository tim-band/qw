"""
The qw (Quality Workflow) tool.

Helps enforce regulatory compliance for projects managed on GitHub.
"""

import sys
from enum import Enum
from typing import Annotated, Optional

import git
import typer
from loguru import logger

from qw.base import QwError
from qw.local_store.directories import find_git_base_dir, get_or_create_qw_dir
from qw.local_store.main import get_configuration, write_to_config
from qw.remote_repo.factory import get_service
from qw.remote_repo.service import (
    Service,
    get_repo_url,
    hostname_to_service,
    remote_address_to_host_user_repo,
)

app = typer.Typer()


class LogLevel(Enum):
    """Log Level."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"


LOGELEVEL_TO_LOGURU = {
    LogLevel.DEBUG: 10,
    LogLevel.INFO: 20,
    LogLevel.WARNING: 30,
    LogLevel.ERROR: 40,
}


@app.callback()
def main(
    loglevel: Annotated[
        Optional[LogLevel],
        typer.Option(
            help="Level of logging to output",
        ),
    ] = None,
):
    """
    Process global options.

    Processes the options passed before the command.
    """
    logger.remove()
    if loglevel is not None:
        logger.add(sys.stderr, level=LOGELEVEL_TO_LOGURU[loglevel])


@app.command()
def init(
    repo: Annotated[
        Optional[str],
        typer.Option(
            help="The URL (or remote name) for the repo containing"
            " the issues. If not supplied the remotes named"
            " 'upstream' and 'origin' will be tried.",
        ),
    ] = None,
    service: Annotated[
        Optional[Service],
        typer.Option(
            help="Which service is hosting the issue tracker. Not"
            " required if the repo URL begins 'github' or 'gitlab'.",
        ),
    ] = None,
    force: Annotated[
        Optional[bool],
        typer.Option(
            help="Replace any existing configuration.",
        ),
    ] = False,
) -> None:
    """Initialize this tool and the repository (as far as possible)."""
    base = find_git_base_dir()
    gitrepo = git.Repo(base)
    repo = get_repo_url(gitrepo, repo)
    qw_dir = get_or_create_qw_dir(base, force=force)
    (host, username, reponame) = remote_address_to_host_user_repo(repo)
    if service is None:
        service = hostname_to_service(host)
    write_to_config(qw_dir, repo, reponame, service, username)


@app.command()
def check():
    """Check whether all the traceability information is present."""
    conf = get_configuration()
    service = get_service(conf)
    logger.info(str(conf))
    logger.info(service.get_issue(1).title)


if __name__ == "__main__":
    try:
        app()
        sys.exit(0)
    except QwError as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(2)
