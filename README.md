<!-- TOC start (generated with https://github.com/derlin/bitdowntoc) -->

- [brand](#brand)
- [How to use](#how-to-use)
   * [Name Availability Check](#name-availability-check)
   * [Generate English Words](#generate-english-words)
   * [ask_ai_to_generate_names](#ask_ai_to_generate_names)
- [More examples](#more-examples)
   * [Example script](#example-script)
   * [name_is_available](#name_is_available)
   * [The store](#the-store)
   * [process_names](#process_names)
- [Motivation](#motivation)

<!-- TOC end -->

<!-- TOC --><a name="brand"></a>
# brand

Tools to find names for things.

Both to generate names, but also check if they're "available" 
(e.g. as domain names, project names, github organization names, etc.)

To install:	```pip install brand```

<!-- TOC --><a name="how-to-use"></a>
# How to use

Check out this [demo notebook](https://github.com/thorwhalen/brand/blob/master/misc/brand_demo.ipynb).

<!-- TOC --><a name="name-availability-check"></a>
## Name Availability Check

```python
from brand import is_available_as
```

Check out the available categories you can check (this will evolve over time, as we add methods).

```python
list(is_available_as)
```

```
['domain_name', 'github_org', 'npm_package', 'pypi_project', 'youtube_channel']
```

```python
>>> is_available_as.github_org('thorwhalen')
False
>>> is_available_as.github_org('__hopefully_this_one_is_available__')
True
>>> is_available_as.pypi_project('numpy')
False
>>> is_available_as.pypi_project('__hopefully_this_one_is_available__')
True
```

<!-- TOC --><a name="generate-english-words"></a>
## Generate English Words

```python
from brand import english_words_gen

# all two letter words starting with 'z'
list(english_words_gen('^z.$'))
```

```
['zr', 'zn', 'zb', 'zu']
```

<!-- TOC --><a name="ask_ai_to_generate_names"></a>
## ask_ai_to_generate_names

```python
from brand import ask_ai_to_generate_names

ask_ai_to_generate_names(
    'For a company that will develop AI-based tools for the financial industry'
)
```

```
['FinAI',
 'MoneyMind',
 'InvestBotics',
 ...
 'FinanceComradeAI',
 'WallStWizardAI']
 ```

<!-- TOC --><a name="more-examples"></a>
# More examples

<!-- TOC --><a name="example-script"></a>
## Example script

`search_names.py` shows an example of how to assemble 
`brand` functionalities to write a script that will search
names of the form `CVCVCV` (`C` for consonant, `V` for vowel)
with no more than `4` unique letters and where either the 
consonants or the vowels are all the same.

```
...
(10)12:49:07 - 2255: nesebe
(10)12:49:08 - 2256: nesede
(10)12:49:09 - 2257: nesefe
---> Found available name: nesefe
(10)12:49:09 - 2258: nesege
---> Found available name: nesege
(10)12:49:09 - 2259: nesele
---> Found available name: nesele
(10)12:49:11 - 2260: neseme
---> Found available name: neseme
(10)12:49:11 - 2261: nesene
```

<!-- TOC --><a name="name_is_available"></a>
## name_is_available

`name_is_available` checks if a name is available using the system's
`whois` command.

```python
from brand import name_is_available
assert name_is_available('google.com') is False
assert name_is_available('asdfaksdjhfsd2384udifyiwue.org') is True
```

<!-- TOC --><a name="the-store"></a>
## The store

First, you'll need to provide a "store". 
That is, a dict-like object that will hold the names you've checked so far, 
under keys `available_names.p` and `not_available.p` (which contains the names
that were checked, but not available). 

The functions use this both to not check what you've already checked, 
and to store its results as they check names.

A store can be an actual `dict`, or a dict-like interface to files or a DB.

We advise to use `py2store` (which is installed with `brand`) to make dict-like
interfaces to your storage system of choice.

When you ask `brand` to make a store with no further specifications, 
it makes a directory and places files in there for you.

```python
import brand
s = brand.get_store()
```

Now you can use that store to see what's already available from 
past work (if anything).

```python
available = brand.available_names(s)
not_available = brand.not_available_names(s)
len(available), len(not_available)
```

<!-- TOC --><a name="process_names"></a>
## process_names

`process_names` will take some `names` (specified as an iterable, 
generator function, or pickle file) and check if each is available, 
saving the results in the given store.

```python
try_these = ['google.com', 'gaggle.com', 'giggle.org', 'asdfiou3t.org']
process_names(try_these)
```


<!-- TOC --><a name="motivation"></a>
# Motivation

Choosing a good name for companies, products, or projects is crucial because it forms the foundation of your brand identity, making a lasting first impression on your audience. A well-chosen name can communicate your values, evoke the right emotions, and set you apart from competitors. It needs to be memorable, easy to pronounce, and relevant to your target market. Moreover, ensuring that the name is available across key domains and platforms avoids legal issues, protects your brand, and maintains a consistent presence online. In short, a strong name is vital for building recognition, trust, and loyalty.

Finding a good name is challenging because it must balance a range of constraints and objectives. It may need to reflect the values, sentiment, or aspirations of a targeted audience, while avoiding associations that might alienate others. Even when choosing a name with semantic flexibility—keeping it vague to allow the brand to evolve—you still want it to be pronounceable, visually appealing, and memorable. On top of these considerations, the name often needs to be available as a domain, social media handle, or product name, which can be frustrating when your ideal choice is already taken. These constraints can slow down the creative process, leading to compromises and sometimes resulting in names that lack inspiration or are later regretted.

The brand package is designed to streamline the often difficult and time-consuming process of naming by automating both name generation and availability checking. With its name generation feature, the package helps users come up with creative, relevant, and flexible names that align with their brand's goals and target audience. It offers options to create names that are memorable, pronounceable, and visually appealing, while also allowing for semantic flexibility.

In addition to generating names, the brand package integrates powerful tools for checking name availability across important platforms such as domain names, social media handles, and other key online spaces. This automated checking saves users the hassle of manually searching for name availability on each platform, ensuring that the chosen name is free to use without conflicts. By addressing both the creative and logistical challenges of naming, the brand package accelerates the process and helps avoid the pitfalls of last-minute compromises, ultimately leading to stronger, more meaningful brand identities.