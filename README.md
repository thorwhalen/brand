# brand
Finding available domain names

To install:	```pip install brand```

# How to use

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

## The functions available to you

## name_is_available

`name_is_available` checks if a name is available using the system's
`whois` command.

```python
from brand import name_is_available
assert name_is_available('google.com') is False
assert name_is_available('asdfaksdjhfsd2384udifyiwue.org') is True
```

### The store

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

### process_names

`process_names` will take some `names` (specified as an iterable, 
generator function, or pickle file) and check if each is available, 
saving the results in the given store.

```python
try_these = ['google.com', 'gaggle.com', 'giggle.org', 'asdfiou3t.org']
process_names(try_these)
```
