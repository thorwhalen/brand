"""Base functions for brand"""

import re
import subprocess
import itertools
import os
from typing import Callable, Union, Iterable, MutableMapping
from time import sleep

from brand.util import print_progress

DFLT_ROOT_DIR = os.path.expanduser("~/tmp/domain_search/")

StoreType = Union[str, MutableMapping]


def name_is_available(name, timeout=7):
    """
    >>> name_is_available('google.com')
    False
    >>> name_is_available('asdfaksdjhfsd2384udifyiwue.org')
    True
    """
    try:
        if "." not in name:
            name = name + ".com"
        r = subprocess.run(["whois", name], capture_output=True, timeout=timeout)
        #     r = subprocess.run(['whois', '-Q', name], capture_output=True)
        try:
            contents = r.stdout.decode()
            search_result = re.search(f"Domain Name: {name}", contents, re.IGNORECASE)
            return search_result is None
        except Exception as e:
            print(f"!!! An error occured with name: {name}")
            print(f"The error was: {e}")
    except subprocess.TimeoutExpired:
        print(f"!!! Timedout: whois {name}")
        return False


# from graze import Graze
# g = Graze(os.path.join(rootdir, 'htmls'))


def add_to_set(store: StoreType, key, value):
    store = get_store(store)
    store[key] = store.get(key, set()) | {value}


def available_names(store: StoreType = DFLT_ROOT_DIR):
    store = get_store(store)
    return set(store["available_names.p"])


def not_available_names(store: StoreType = DFLT_ROOT_DIR):
    store = get_store(store)
    return set(store["not_available.p"])


def already_checked_names(store: StoreType = DFLT_ROOT_DIR):
    store = get_store(store)
    return available_names(store) | not_available_names(store)


def process_names(
    names,
    store: StoreType = DFLT_ROOT_DIR,
    domain_suffix=".com",
    same_line_print=False,
    available_name_msg="---> Found available name: ",
):
    skip_names = already_checked_names(store)

    for i, name in enumerate(filter(lambda x: x not in skip_names, names)):
        if i % 10 == 0:
            sleep(1)
        print_progress(f"{i}: {name}", refresh=same_line_print)
        if not name_is_available(name + domain_suffix):
            add_to_set(store, "not_available.p", name)
        else:
            if available_name_msg:
                print(available_name_msg + name)
            add_to_set(store, "available_names.p", name)


vowels = "aeiouy"
consonants = "bcdfghjklmnpqrstvwxz"
fewer_consonants = "bdfglmnprstvz"

_vowels = set(vowels)
_consonants = set(consonants)


def all_cvcvcv(consonants=fewer_consonants, vowels=vowels):
    yield from map(
        "".join,
        itertools.product(consonants, vowels, consonants, vowels, consonants, vowels),
    )


def few_uniques(w, max_uniks=4, max_unik_vowels=1, max_unik_consonants=1):
    letters = set(w)
    if len(letters) > max_uniks:
        return False
    else:
        return (
            len(letters & _vowels) == max_unik_vowels
            or len(letters & _consonants) == max_unik_consonants
        )


def ensure_dir(dirpath):
    if not os.path.isdir(dirpath):
        print(f"Making the directory: {dirpath}")
        os.makedirs(dirpath)


def _get_name_generator(name_generator) -> Callable:
    if not callable(name_generator):
        if isinstance(name_generator, str) & os.path.isfile(name_generator):
            with open(name_generator, "rt") as fp:
                lines = fp.read().split("\n")
            name_generator = lambda: iter(lines)
        else:
            name_generator = lambda: iter(name_generator)
    assert isinstance(name_generator, Callable)
    return name_generator


def get_store(store: StoreType = DFLT_ROOT_DIR):
    if isinstance(store, str):
        if os.path.isdir(store):
            from py2store import LocalPickleStore

            store = LocalPickleStore(store)
        elif os.path.isfile(store):
            import pickle

            with open(store) as fp:
                store = pickle.load(fp)
    assert isinstance(store, MutableMapping)
    return store


def try_some_cvcvcvs(
    store: StoreType = DFLT_ROOT_DIR,
    name_generator: Union[Callable, str, Iterable] = all_cvcvcv,
    filt: Callable = few_uniques,
    same_line_print: bool = False,
):

    name_generator = _get_name_generator(name_generator)
    store = get_store(store)
    names = sorted(set(filter(filt, name_generator())) - already_checked_names(store))
    print(f"{len(names)} names will be checked...")
    print("--------------------------------------------------------------------------")
    process_names(names, store, same_line_print=same_line_print)


checked_p = re.compile("- \d+: (\w+)")
available_p = re.compile("---> Found available name: (\w+)")
timedout_p = re.compile("!!! Timedout: whois (\w+).com")
error_p = re.compile("!!! An error occured with name: (\w+).com")


def logs_diagnosis(log_text):
    from collections import defaultdict

    def tag_line(line):
        m = checked_p.search(line)
        if m:
            return "checked", m.group(1)
        m = available_p.search(line)
        if m:
            return "available", m.group(1)
        m = timedout_p.search(line)
        if m:
            return "timedout", m.group(1)
        m = error_p.search(line)
        if m:
            return "error", m.group(1)
        return None, line

    w = log_text.split("\n")

    d = defaultdict(list)
    for k, v in map(tag_line, w):
        d[k].append(v)

    return dict(d)
