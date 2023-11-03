from importlib.metadata import version, metadata

import platformdirs

PYPI_PACKAGE_NAME = __package__  # Lucky!!!
PYPI_VERSION = version(PYPI_PACKAGE_NAME)
PYPI_AUTHOR_EMAIL = metadata(PYPI_PACKAGE_NAME)["Author-email"]


# Ref: https://stackoverflow.com/questions/880530
def __getattr__(name):
    if name == "APP_STATE_PATH":
        return str(
            platformdirs.user_state_path(
                appname=PYPI_PACKAGE_NAME,
                appauthor=PYPI_AUTHOR_EMAIL,
                version=PYPI_VERSION,
                ensure_exists=True,
            )
        )
    elif name == "APP_LOG_PATH":
        return str(
            platformdirs.user_log_path(
                appname=PYPI_PACKAGE_NAME,
                appauthor=PYPI_AUTHOR_EMAIL,
                version=PYPI_VERSION,
                ensure_exists=True,
            )
        )
    elif name == "APP_CONFIG_PATH":
        return str(
            platformdirs.user_config_path(
                appname=PYPI_PACKAGE_NAME,
                appauthor=PYPI_AUTHOR_EMAIL,
                version=PYPI_VERSION,
                ensure_exists=True,
            )
        )
    else:
        AttributeError(f"module '{__name__}' has no attribute '{name}'")
