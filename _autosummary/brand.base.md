# brand.base

Base functions for brand

### Functions

| `add_to_set`(store, key, value)                                                                  |                                                                       |
|--------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------|
| [`ai_analyze_names`](#brand.base.ai_analyze_names)(names[, context, json_output]) | Ask the brand-expert AI to analyze names for a given context.         |
| `all_cvcvcv`([consonants, vowels])                                                               |                                                                       |
| `already_checked_names`([store])                                                                 |                                                                       |
| [`ask_ai_to_generate_names`](#brand.base.ask_ai_to_generate_names)(context)               | Ask the AI to generate names for a given context.                     |
| `available_names`([store, key])                                                                  |                                                                       |
| [`batch_check_available`](#brand.base.batch_check_available)(names, \*[, tld, ...])    | Two-pass domain availability check: fast DNS then WHOIS verification. |
| [`domain_exists`](#brand.base.domain_exists)(domain[, tld])                    | Check if a domain exists (is registered or resolves).                 |
| [`domain_exists_socket`](#brand.base.domain_exists_socket)(domain)                    | Check if a domain resolves via DNS lookup.                            |
| [`domain_exists_whois`](#brand.base.domain_exists_whois)(domain)                     | Check if a domain is registered via WHOIS lookup.                     |
| [`domain_name_is_available`](#brand.base.domain_name_is_available)(name[, tld])           |                                                                       |
| [`english_words_gen`](#brand.base.english_words_gen)([pattern])                    | Get an iterable of English words.                                     |
| `ensure_dir`(dirpath)                                                                            |                                                                       |
| `few_uniques`(w[, max_uniks, max_unik_vowels, ...])                                              |                                                                       |
| `get_store`([store])                                                                             |                                                                       |
| `logs_diagnosis`(log_text)                                                                       |                                                                       |
| [`name_is_available`](#brand.base.name_is_available)(name[, tld])                  |                                                                       |
| `not_available_names`([store, key])                                                              |                                                                       |
| `process_names`(names[, store, domain_suffix, ...])                                              |                                                                       |
| `status_code_says_it_is_available`(response, \*)                                                 |                                                                       |
| `template_based_availability_func`(template)                                                     |                                                                       |
| `try_some_names`([name_generator, store, ...])                                                   |                                                                       |
| `url_says_it_is_available`(name, name_to_url)                                                    |                                                                       |
| `url_template_base_availability`(templates)                                                      |                                                                       |

### Classes

| [`IterableNamespace`](#brand.base.IterableNamespace)   |    |
|----------------------------------------------------------------------|----|

### *class* brand.base.IterableNamespace

Bases: [`SimpleNamespace`](https://docs.python.org/3/library/types.html#types.SimpleNamespace)

### brand.base.ai_analyze_names(names, context='', , json_output=False)

Ask the brand-expert AI to analyze names for a given context.

### brand.base.ask_ai_to_generate_names(context)

Ask the AI to generate names for a given context.

### brand.base.batch_check_available(names, , tld='.com', dns_workers=20, whois_workers=5, whois_batch_sleep=1, on_available=None, on_progress=None)

Two-pass domain availability check: fast DNS then WHOIS verification.

Pass 1 (fast, parallel): DNS lookup filters out domains that resolve.
Pass 2 (slower, parallel): WHOIS verification on DNS-negative candidates.

* **Parameters:**
  * **names** – Iterable of domain names (without TLD).
  * **tld** – TLD to append (default ‘.com’).
  * **dns_workers** – Number of parallel DNS workers.
  * **whois_workers** – Number of parallel WHOIS workers.
  * **whois_batch_sleep** – Seconds to sleep between WHOIS batches.
  * **on_available** – Optional callback(name) when a name is confirmed available.
  * **on_progress** – Optional callback(phase, checked, total, available_count).
* **Returns:**
  dict with keys ‘available’, ‘not_available’, ‘dns_negative’ (pre-whois).

### brand.base.domain_exists(domain, tld='.com')

Check if a domain exists (is registered or resolves).
Uses fast DNS check first, then WHOIS if DNS fails to reduce false negatives.
Returns False if the domain is likely available (unregistered).

* **Parameters:**
  * **domain** – Domain name (e.g., ‘example’, ‘example.com’).
  * **tld** – TLD to append if none provided (default ‘.com’).
* **Returns:**
  True if domain exists (registered or resolves), False if likely available.
* **Return type:**
  [*bool*](https://docs.python.org/3/builtins/functions.html#bool)

### Examples

```pycon
>>> domain_exists('google.com')
True
>>> domain_exists('asdfaksdjhfsd2384udifyiwue.org')
False
```

### brand.base.domain_exists_socket(domain)

Check if a domain resolves via DNS lookup.

* **Parameters:**
  **domain** – Domain name (e.g., ‘example.com’).
* **Returns:**
  True if domain resolves, False otherwise.
* **Return type:**
  [*bool*](https://docs.python.org/3/builtins/functions.html#bool)

### brand.base.domain_exists_whois(domain)

Check if a domain is registered via WHOIS lookup.

* **Parameters:**
  **domain** – Domain name (e.g., ‘example.com’).
* **Returns:**
  True if domain is registered, False if likely unregistered.
* **Return type:**
  [*bool*](https://docs.python.org/3/builtins/functions.html#bool)

### brand.base.domain_name_is_available(name, tld='.com')

```pycon
>>> name_is_available('google.com')
False
>>> name_is_available('asdfaksdjhfsd2384udifyiwue.org')
True
```

### brand.base.english_words_gen(pattern='.\*')

Get an iterable of English words.

You can pre-filter the words using regular expressions.

Note that the dictionary is quite large; larger than the usual “scrabble-allowed”
dictionaries.

Note that you often want to post-filter as well.
You can do so simply by using the `filter` function.

* **Parameters:**
  **pattern** – Regular expression to filter with
* **Return type:**
  [`Iterable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterable)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

#### TIP
to sort by word length, do `sorted(english_words_gen(..., key=len))`.

### brand.base.name_is_available(name, tld='.com')

```pycon
>>> name_is_available('google.com')
False
>>> name_is_available('asdfaksdjhfsd2384udifyiwue.org')
True
```
