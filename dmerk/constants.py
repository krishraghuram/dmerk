from importlib.metadata import version, metadata

import platformdirs

PYPI_PACKAGE_NAME = __package__  # Lucky!!!
PYPI_VERSION = version(PYPI_PACKAGE_NAME)
PYPI_AUTHOR_EMAIL = metadata(PYPI_PACKAGE_NAME)["Author-email"]

APP_STATE_PATH = str(
    platformdirs.user_state_path(
        appname=PYPI_PACKAGE_NAME,
        appauthor=PYPI_AUTHOR_EMAIL,
        version=PYPI_VERSION,
        ensure_exists=True,
    )
)
APP_LOG_PATH = str(
    platformdirs.user_log_path(
        appname=PYPI_PACKAGE_NAME,
        appauthor=PYPI_AUTHOR_EMAIL,
        version=PYPI_VERSION,
        ensure_exists=True,
    )
)
APP_CONFIG_PATH = str(
    platformdirs.user_config_path(
        appname=PYPI_PACKAGE_NAME,
        appauthor=PYPI_AUTHOR_EMAIL,
        version=PYPI_VERSION,
        ensure_exists=True,
    )
)
