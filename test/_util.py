import logging

COLOR_RED = "\033[31;1m"
COLOR_GREEN = "\033[32;1m"
COLOR_ORANGE = "\033[33;1m"
COLOR_MAGENTA = "\033[35;1m"

COLOR_DEFAULT = "\033[m"
COLOR_DESCRIPTION = COLOR_MAGENTA
COLOR_VALUE = COLOR_GREEN
COLOR_WARNING = COLOR_RED

# if not sys.stdout.isatty():
#    COLOR_DEFAULT = ''
#    COLOR_DESCRIPTION = ''
#    COLOR_VALUE = ''
#    COLOR_WARNING = ''


def _add_color(description, value, color=COLOR_VALUE, sep=": "):
    return "".join(
        (
            COLOR_DESCRIPTION,
            description,
            COLOR_DEFAULT,
            sep,
            color,
            value,
            COLOR_DEFAULT,
        )
    )


def error(msg, cause=None, label="    ERROR"):
    msg = _add_color(label, str(msg), color=COLOR_WARNING)
    if cause:
        logging.exception(msg)
    else:
        logging.error(msg)


def info(msg, label="INFO"):
    msg = str(msg)
    if label:
        msg = _add_color(label, msg)
    logging.info(msg)
