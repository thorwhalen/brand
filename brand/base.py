"""Base functions for brand"""

import re
import subprocess
import itertools
import os
from typing import Callable, Union, Iterable, MutableMapping
from time import sleep

import lexis

from brand.util import print_progress

DFLT_ROOT_DIR = os.path.expanduser("~/tmp/domain_search/")

StoreType = Union[str, MutableMapping]


def english_words_gen(pattern='.*') -> Iterable[str]:
    """
    Get an iterable of English words.

    You can pre-filter the words using regular expressions.

    Note that the dictionary is quite large; larger than the usual "scrabble-allowed"
    dictionaries.

    Note that you often want to post-filter as well.
    You can do so simply by using the `filter` function.

    :param pattern: Regular expression to filter with

    Tip: to sort by word length, do ``sorted(english_words_gen(..., key=len))``.

    """
    pattern = re.compile(pattern)
    return filter(pattern.search, lexis.Lemmas())


def domain_name_is_available(name, timeout=7, tld='.com'):
    """
    >>> name_is_available('google.com')
    False
    >>> name_is_available('asdfaksdjhfsd2384udifyiwue.org')
    True
    """
    try:
        if "." not in name:
            name = name + tld
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


name_is_available = domain_name_is_available  # back-compatibility alias

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


# --------------------------------------------------------------------------------------
# AI-based generation

brand_name_analysis_criteria = """
• Meaningfulness & Flexibility: A name that communicates your brand’s core values creates immediate emotional resonance; however, if it’s too literal or specific, it can pigeonhole the brand, making future diversification or pivots more challenging.
• Distinctiveness: A unique name helps the brand stand out in a crowded market, ensuring it isn’t easily confused with competitors.
• Memorability: An easily recalled name fosters word-of-mouth promotion and ensures that the brand remains top-of-mind for consumers.
• Pronounceability & Spelling: A name that is simple to say and spell reduces confusion, aids in effective communication, and enhances online searchability.
• Simplicity: Short, concise names are generally more user-friendly and can be more easily integrated into marketing materials and digital platforms.
• Future-Proofing: The chosen name should be adaptable enough to support brand evolution and expansion, avoiding constraints imposed by overly descriptive terms.
• Legal Availability: It’s essential that the name can be trademarked and isn’t already in use to prevent costly legal disputes and ensure exclusive brand identity.
• SEO & Digital Friendliness: A distinctive and searchable name enhances online visibility, making it easier for consumers to find and engage with the brand.
• Cultural Sensitivity: The name should translate well across different languages and cultures, avoiding negative connotations or misinterpretations in global markets.
• Visual & Aesthetic Appeal: A name that lends itself to a compelling visual identity can enhance logo design and overall brand presentation, reinforcing recognition.
"""


def ask_ai_to_generate_names(context):
    """Ask the AI to generate names for a given context."""
    import oa  # pip install oa  (will required an openai api key to be specified)

    template = f"""
    You are an expert in branding and you are helping a client come up with a name for
    {{thing}}.
    Suggest {{n:30}} names between {{min_length:1}} and {{max_length:15}} characters long.

    Only output the names, one per line with no words before or after it, 
    since I will be parsing the output.

    You should choose these names in consideration of the following criteria:
    {brand_name_analysis_criteria}
    """
    string_response = oa.ask.ai.suggest_names(context)
    try:
        return string_response.split("\n")
    except Exception as e:
        raise ValueError(
            f"An error occured: {e}. "
            f"Here's the raw response of the AI:\n{string_response}"
        )


def ai_analyze_names(
    names: Union[str, Iterable[str]], context: str = '', *, json_output=False
):
    """Ask the brand-expert AI to analyze names for a given context."""
    import oa  # pip install oa  (will required an openai api key to be specified)

    template = f"""
    You are a brand consultant and you are helping a client come up with a name for 
    their nes product or business. 
    The context (may) be give below (if empty, just consider a general context).

    The client has some ideas for names, given below. 
    You need to analyze the names, score them, and list them from best to worst, 
    explaining what the pros and cons of each name are.
    Score should be from 1 to 9, with 1 being worst and 9 being best.

    You will base your analysis on the following criteria:
    {brand_name_analysis_criteria}

    Names:
    {{names}}

    Context: {{context:}}
    """

    if not isinstance(names, str):
        names = "\n".join(names)

    if json_output:
        ask_ai = oa.prompt_json_function(
            template,
            json_schema={
                'name': 'RankedAnalysisSchema',
                'properties': {
                    'items': {
                        'items': {
                            'properties': {
                                'analysis': {'type': 'string'},
                                'name': {'type': 'string'},
                                'score': {
                                    'maximum': 9,
                                    'minimum': 1,
                                    'type': 'integer',
                                },
                            },
                            'required': ['name', 'score', 'analysis'],
                            'type': 'object',
                        },
                        'type': 'array',
                    }
                },
                'required': ['items'],
                'type': 'object',
            },
        )
    else:
        ask_ai = oa.prompt_function(template)

    return ask_ai(names=names, context=context)


# --------------------------------------------------------------------------------------
# availability check

import requests
from functools import partial
from typing import Callable

ResponseBoolFunc = Callable[[requests.Response], bool]


def status_code_says_it_is_available(
    response,
    *,
    is_available_status_codes=(404, 410),
    is_not_available_status_codes=(200, 301),
):
    """ """
    if response.status_code in is_available_status_codes:
        return True
    elif response.status_code in is_not_available_status_codes:
        return False
    else:
        raise ValueError(f"unexpected status code: {response.status_code}")


status_code_says_it_is_available: ResponseBoolFunc


def url_says_it_is_available(
    name,
    name_to_url: str,
    response_bool_func: ResponseBoolFunc = status_code_says_it_is_available,
    *,
    request_func=requests.get,
):
    url = name_to_url(name)
    response = request_func(url)
    return response_bool_func(response)


def template_based_availability_func(template: str):
    return partial(url_says_it_is_available, name_to_url=template.format)


from types import SimpleNamespace


class IterableNamespace(SimpleNamespace):
    def __iter__(self):
        for attr in dir(is_available_as):
            if not attr.startswith('_'):
                yield attr


def url_template_base_availability(templates: dict):
    return IterableNamespace(
        **{k: template_based_availability_func(v) for k, v in templates.items()}
    )


pypi_package_is_available = template_based_availability_func(
    "https://pypi.org/project/{}/"
)

is_available_as = url_template_base_availability(
    dict(
        # www_dot_com="http://www.{}.com",  # produces ConnectionError
        # domain_name="https://www.namecheap.com/domains/registration/results/?domain={}",  # Example using Namecheap for domain check
        github_org="https://github.com/{}",
        # twitter_profile="https://twitter.com/{}",  # response is always 200
        # instagram_user="https://www.instagram.com/{}/",
        # reddit_user="https://www.reddit.com/user/{}",  # response is always 200
        pypi_project="https://pypi.org/project/{}",
        npm_package="https://www.npmjs.com/package/{}",
        # facebook_page="https://www.facebook.com/{}",  # response is always 200
        # linkedin_company="https://www.linkedin.com/company/{}/",  # code 999
        youtube_channel="https://www.youtube.com/{}",
    )
)

# add some more complex ones
is_available_as.domain_name = domain_name_is_available


# github_org_is_available = template_based_availability_func("https://github.com/{}")
is_available_as.__doc__ = """
    >>> is_available_as.github_org('i2mint')
    False
    >>> is_available_as.github_org('__hopefully_this_does_not_exist__')
    True
"""
