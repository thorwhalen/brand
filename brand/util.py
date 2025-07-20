"""Util functions"""

import os
from typing import Union, MutableMapping
from datetime import datetime
from config2py import get_app_data_folder, process_path


APP_ROOT_DIR = get_app_data_folder("brand")
DFLT_ROOT_DIR = process_path(
    os.path.join(APP_ROOT_DIR, "domain_search/"),
    ensure_dir_exists=True,
)

StoreType = Union[str, MutableMapping]


def hms_message(msg=""):
    t = datetime.now()
    return "({:02.0f}){:02.0f}:{:02.0f}:{:02.0f} - {}".format(
        t.day, t.hour, t.minute, t.second, msg
    )


def print_progress(msg, refresh=None, display_time=True):
    """
    input: message, and possibly args (to be placed in the message string, sprintf-style
    output: Displays the time (HH:MM:SS), and the message
    use: To be able to track processes (and the time they take)
    """
    if display_time:
        msg = hms_message(msg)
    if refresh:
        print(msg, end="\r")
        # stdout.write('\r' + msg)
        # stdout.write(refresh)
        # stdout.flush()
    else:
        print(msg)
