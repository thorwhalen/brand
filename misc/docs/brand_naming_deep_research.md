# Deep Research Report: Resources for Building a Computational Brand Name Evaluation System

**Author:** Thor Whalen  
**Date:** 2026-03-28

---

## A. Grapheme-to-Phoneme (G2P) Libraries

### A1. Core G2P Libraries Compared

**`pronouncing`** — The simplest entry point for English. A lightweight wrapper around the CMU Pronouncing Dictionary (~134k words) with no external dependencies. Provides phoneme lookup, syllable counting, stress patterns, and rhyme detection using ARPAbet encoding. Ideal for brand names that are plausible English words, but cannot handle novel neologisms that aren't in the dictionary. [1]

**`epitran`** — A mapping-and-repairs approach to G2P supporting 70+ language-script pairs. Outputs IPA and X-SAMPA. Requires Python 3.10+. Good accuracy for languages with phonemically transparent orthographies (Turkish, Swahili, Hindi), but struggles with opaque orthographies (French is not supported, English requires CMU Flite). The key advantage for brand naming: you can transcribe a candidate name *as if it were a word* in multiple languages to check what it would sound like. [2]

**`phonemizer`** — Built on `espeak-ng` (a TTS engine), supports 100+ languages. More accurate than `epitran` for complex orthographies, but requires `espeak-ng` system installation. Four backends: espeak (IPA, many languages), espeak-mbrola (SAMPA), festival (American English only, syllable-level), and segments (user-provided G2P maps). Best overall accuracy but heavier dependency footprint. [3]

**`transphone`** — A neural G2P model supporting 8,000+ languages via a multilingual pretrained model (ACL 2022). Falls back to `epitran` for some languages. Excellent for truly cross-linguistic phonemization of brand name candidates. [4]

**`DeepPhonemizer`** — Transformer-based G2P with CTC and autoregressive variants. Multilingual. High accuracy but requires model checkpoints (~100MB). Overkill for brand naming unless batch-processing thousands of candidates. [5]

**`g2p-plus`** — A meta-tool that wraps `phonemizer`, `epitran`, and other backends with unified output mapped to PHOIBLE phoneme inventories. Good for ensuring consistent cross-linguistic phoneme representations. [6]

**Recommendation for the brand skill:** Use `pronouncing` as the fast path for English (it's already in CMU dict format which `python-blick` expects). Use `epitran` for multi-language phonemization of neologisms. Consider `phonemizer` if you need French/German/complex orthographies.

### A2. Phonological Feature Libraries

**`panphon`** — The gold standard for mapping IPA segments to articulatory feature vectors (24 binary features: place, manner, voicing, etc.). Published at COLING 2016 by Mortensen et al. Provides distance metrics between phoneme strings based on feature Hamming distance. This is essential for the sound symbolism scoring module — you can compute articulatory transitions, classify phonemes by manner/place, and measure articulatory complexity. MIT licensed, actively maintained. [7]

**`soundvectors`** — A newer alternative to `panphon` that generates feature vectors dynamically from IPA descriptions via the CLTS (Cross-Linguistic Transcription Systems) catalog, rather than relying on lookup tables. More robust for unusual IPA combinations but less battle-tested. [8]

**`phoible`** — The cross-linguistic phoneme inventory database (3,000+ inventories from 2,000+ languages). Accessible via Python. Useful for checking whether a brand name's phoneme sequence is legal in target languages. [9]

---

## B. Phonotactic Probability Calculators

### B1. Vitevitch & Luce Method

The foundational method for measuring how "word-like" a string sounds. Calculates positional segment frequency and biphone probability from the CMU Pronouncing Dictionary weighted by token frequency from CELEX. Words/nonwords with high phonotactic probability sound more natural and are judged as more word-like. The original web calculator is at Kansas University [10]. A Python implementation exists in **Phonological CorpusTools (PCT)** [11].

Key paper: Vitevitch, M.S. & Luce, P.A. (2004). "A web-based interface to calculate phonotactic probability for words and nonwords in English." *Behavior Research Methods*, 36, 481-487. [10]

Critically, Vitevitch & Donoso (2012) showed that **brand names with higher phonotactic probability were rated as more likeable** — a direct validation for brand naming applications. [10]

### B2. BLICK (Bruce Hayes)

**`python-blick`** — A Python implementation of BLICK, a constraint-based phonotactic well-formedness calculator for English by Bruce Hayes (UCLA). Unlike the Vitevitch & Luce method which uses positional n-gram probabilities, BLICK uses weighted phonological constraints learned from the CMU dict. Returns a penalty score (0 = perfectly legal English word, higher = more ill-formed). Available on PyPI. [12]

Example: "blick" scores 0 (perfect), "doit" scores ~3 (somewhat odd), "nguhyee" scores ~12 (terrible). This is exactly the kind of scoring you want for brand names.

### B3. Other Approaches

**Phonological CorpusTools** — A desktop application with Python internals that computes phonotactic probability, functional load, and other measures. Can be adapted for programmatic use. [11]

**UCI Phonotactic Calculator** — A recent (2023) online tool that implements both positional and non-positional n-gram models, trained on CMU Dict + CELEX. Research shows non-positional metrics may better predict human acceptability judgments. [13]

---

## C. Sound Symbolism in Branding — Key Literature

### C1. Foundational Papers

**Klink (2000)** — "Creating Brand Names with Meaning: The Use of Sound Symbolism." *Marketing Letters*, 11(1), 5-20. The seminal paper. Found that front vowels (/i/, /e/) in brand names convey smallness, lightness, thinness, coldness, mildness, fastness, bitterness; back vowels (/o/, /u/) convey the opposites. Voiceless consonants (/p/, /t/, /k/) → smaller, sharper, faster, more feminine; voiced (/b/, /d/, /g/) → larger, heavier, slower, more masculine. [14]

**Klink (2001)** — "Creating Meaningful New Brand Names: A Study of Semantics and Sound Symbolism." Extended the 2000 findings. Consumers prefer brand names whose sounds convey desirable product attributes (e.g., "Frosh" over "Frish" for ice cream because /o/ conveys creaminess). [14]

**Yorkston & Menon (2004)** — "A Sound Idea: Phonetic Effects of Brand Names on Consumer Judgments." *Journal of Consumer Research*, 31(1). Showed that sound-symbolic associations in brand names influence product evaluations automatically and without conscious awareness. Front vowels → perceived as smaller/lighter products. [15]

**Lowrey & Shrum (2007)** — Extended sound symbolism to brand name preference. Sound-symbolically matching brand names (where phonemes match desired product attributes) are preferred over mismatching names. Cross-cultural replications. [14]

**Klink & Athaide (2012)** — "Creating Global Brand Names: The Use of Sound Symbolism." *Journal of Global Marketing*, 25(4). Demonstrated that sound-symbolic associations work cross-linguistically, making them valuable for global brand naming. [14]

### C2. Integrative Frameworks

**Motoki, Velasco, & Spence (2023)** — "The connotative meanings of sound symbolism in brand names: A conceptual framework." *Journal of Business Research*. Uses Osgood's semantic differential (Evaluation, Potency, Activity) to integrate sound symbolism findings. Provides the most complete mapping of phoneme types → brand perception dimensions. Essential reading for building a scoring system. [16]

### C3. The Bouba/Kiki Effect in Branding

Originally Köhler (1929), popularized by Ramachandran & Hubbard (2001). 95% of participants associate "bouba" with round shapes and "kiki" with spiky shapes. The effect extends to brand perception: "bouba-like" brand names (open vowels, sonorants) feel friendlier, softer, more approachable; "kiki-like" names (stops, front vowels, fricatives) feel sharper, more modern, more technical. [17]

### C4. Key Academic Venues

- *Journal of Consumer Research* — Yorkston & Menon, Lowrey & Shrum
- *Marketing Letters* — Klink's foundational work
- *Journal of Business Research* — Motoki et al. integrative framework
- *Journal of Product & Brand Management* — applied brand naming studies
- *Names: A Journal of Onomastics* — commercial onomastics

---

## D. Brand Naming Books

1. **Alexandra Watkins — *Hello, My Name Is Awesome* (2014, 2nd ed. 2019)** — The practitioner's bible. SMILE test (Suggestive, Meaningful, Imagery, Legs, Emotional) and SCRATCH test (Spelling-challenged, Copycat, Restrictive, Annoying, Tame, Curse of knowledge, Hard to pronounce). Named "Top 10 Marketing Book" by Inc. Watkins founded Eat My Words naming firm (clients: Disney, Microsoft, Adobe). [18]

2. **Rob Meyerson — *Brand Naming: The Complete Guide* (2022)** — The most comprehensive modern guide. Meyerson was head of naming at HP and director at Interbrand. Covers naming taxonomy (descriptive, suggestive, arbitrary, coined, acronymic), naming process, legal screening, and cross-cultural considerations. Also hosts the "How Brands Are Built" podcast. [19]

3. **Jeremy Miller — *Brand New Name* (2019)** — Step-by-step process for creating brand names. Strong on naming strategy and positioning.

4. **Marty Neumeier — *The Brand Gap* (2003)** — Not specifically about naming but foundational on brand strategy. Defines the gap between business strategy and creative execution. [18]

5. **Brad VanAuken — *Brand Aid*** — Comprehensive brand management guide including naming.

6. **Naseem Javed — *Naming for Power*** — One of the earliest dedicated naming guides, focused on coined/invented names for global markets.

---

## E. Cross-Linguistic Safety Resources

### E1. Multi-Language Dictionaries & APIs

**Wiktionary REST API** — Free, no auth required. Covers 170+ languages. Query `https://en.wiktionary.org/api/rest_v1/page/definition/{word}` for definitions. Can check if a brand name means something in other languages. Also available via `wiktionaryparser` Python package. [20]

**Datamuse API** — Free, no auth, no rate limit (experimental). Provides "sounds like" (`sl`), "spelled like" (`sp`), and "means like" (`ml`) queries. Uses CMU Pronouncing Dictionary for phonetic data and Google Books N-grams for frequency. The `python-datamuse` wrapper is available on PyPI. Crucial for finding words that sound like your brand name (competitive collision detection). [21]

**Google Translate API** — Paid (free tier available). Can auto-detect if a short string is recognized as a word in any of 100+ languages and return translations. Useful as a quick cross-linguistic screen.

### E2. Profanity & Sensitive Word Lists

**LDNOOBW** — "List of Dirty, Naughty, Obscene, and Otherwise Bad Words." The most widely referenced open-source profanity list. Multiple languages. Available at `github.com/LDNOOBW`. [22]

**cuss** (npm/GitHub) — Rated profanity lists covering ~1,770 English terms plus Arabic, French, Italian, Portuguese, and others. Each word has a "sureness" rating (0-2) indicating how likely it is to be profane in context. [23]

**profanity.csv** — Multilingual profanity database with severity levels, structured as CSV per language. Good for programmatic integration. [24]

**dsojevic/profanity-list** — JSON-formatted lists with severity ratings (1-4), tags, partial matching support, and exception lists. Well-structured for integration. [25]

**washyourmouthoutwithsoap** — Simple multi-language bad word lists from Google's "what wouldn't we suggest people look at" filtering. [26]

### E3. Known Brand Naming Fails (Test Cases)

Classic examples to use as validation data:
- **Mitsubishi Pajero** — "pajero" is a vulgar term in Spanish
- **Chevrolet Nova** — "no va" = "doesn't go" in Spanish (though the real impact is debated)
- **Ford Pinto** — slang for small male genitalia in Brazilian Portuguese
- **Nokia Lumia** — "lumia" = prostitute in Spanish
- **Siri** — means "buttocks" in Japanese
- **Vicks** — pronounced like a vulgar German word

---

## F. Trademark & Legal Availability

### F1. USPTO (United States)

**USPTO TSDR API** — Official API for Trademark Status and Document Retrieval. Requires an API key (free, from developer.uspto.gov). Returns registration status, owner, dates. Note: being migrated to new Open Data Portal by April 2026. [27]

**USPTO Trademark API (RapidAPI)** — Unofficial REST wrapper on RapidAPI Hub by Márton Kodok. Endpoints include `/v1/trademarkAvailable/{keyword}` (availability check) and `/v1/trademarkSearch/{keyword}` (full search). Freemium model. Updated every ~3 days. More developer-friendly than official API. [28]

**Marker API** — Commercial trademark search API (markerapi.com). Searches USPTO database. REST endpoints for trademark search, owner search, description search, expiration search. Paid subscriptions. [29]

**USPTO TESS** — The official trademark search system (tmsearch.uspto.gov). Browser-based, no programmatic API, but can be scraped. [30]

### F2. International

**EUIPO eSearch Plus** — EU trademark search. Web interface, limited programmatic access.

**WIPO Global Brand Database** — International trademarks. Web interface at branddb.wipo.int.

### F3. Company Registries

**OpenCorporates API** — The world's largest open database of companies (200M+ companies across 145 jurisdictions). Free for open data projects. REST API at `api.opencorporates.com`. Python wrapper: `opyncorporates`. Excellent for checking if a company with your candidate name already exists. [31]

---

## G. Word Frequency & Memorability

### G1. Word Frequency

**`wordfreq`** — Python library providing word frequencies in 40+ languages from multiple corpus sources (Wikipedia, Google Books, Reddit, Twitter, OpenSubtitles, Common Crawl). The `zipf_frequency()` function returns a Zipf-scale score (0 = very rare, 7+ = ultra common). Ideal for measuring how "novel" a brand name is — you want a name that has zero or near-zero frequency (distinctive) but whose component phonemes are high-frequency (familiar-sounding). Note: declared "sunset" by author Robyn Speer — no new data updates, but existing data through 2021 is stable and fine for this use case. [32]

### G2. Memorability Research

**MRC Psycholinguistic Database** — Contains imageability, concreteness, familiarity, and age-of-acquisition ratings for ~150k English words. High-imageability words are more memorable.

**Glasgow Norms** — Psycholinguistic ratings (arousal, valence, dominance, concreteness, imageability, familiarity) for 5,553 English words.

**Brysbaert Concreteness Ratings** — Concreteness ratings for 40k English words on a 1-5 scale. Words rated as more concrete (e.g., "apple") are more memorable than abstract words (e.g., "equity").

Key finding for brand naming: **concrete, imageable, emotionally arousing names are more memorable.** This is why "Apple," "Amazon," and "Shell" work — they have strong mental images. Coined names like "Xerox" or "Kodak" compensate with distinctive phonology.

### G3. String Similarity

**`jellyfish`** — Python library for phonetic encoding (Soundex, Metaphone, NYSIIS, Match Rating) and string distance (Levenshtein, Damerau-Levenshtein, Jaro-Winkler, Hamming). Use Metaphone encoding to find existing words/brands that sound like your candidate name.

**`rapidfuzz`** — Fast string similarity (Levenshtein, Jaro-Winkler, etc.) with C++ backend. 10-100x faster than `python-Levenshtein`.

---

## H. Complete Tool Inventory

### H1. Must-Have (High Impact, Available Now)

| Package | Purpose | Install | Auth? |
|---|---|---|---|
| `pronouncing` | CMU dict, syllables, stress, rhymes | `pip install pronouncing` | No |
| `panphon` | IPA → feature vectors, articulatory distance | `pip install panphon` | No |
| `python-blick` | Phonotactic well-formedness score (English) | `pip install python-BLICK` | No |
| `wordfreq` | Word frequency in 40+ languages | `pip install wordfreq` | No |
| `epitran` | Multi-language G2P | `pip install epitran` | No |
| `jellyfish` | Phonetic encoding + string distance | `pip install jellyfish` | No |
| `rapidfuzz` | Fast string similarity | `pip install rapidfuzz` | No |
| Datamuse API | Sounds-like, means-like, spelled-like queries | HTTP requests | No |
| Wiktionary API | Multi-language definitions | HTTP requests | No |

### H2. Should-Have (High Impact, Some Setup)

| Resource | Purpose | Notes |
|---|---|---|
| `phonemizer` | Accurate G2P for 100+ languages | Requires `espeak-ng` system install |
| LDNOOBW / cuss | Multi-language profanity lists | Static data files, import as lists |
| OpenCorporates API | Company name collision check | Free API key for open projects |
| USPTO Trademark API | US trademark search | Free tier on RapidAPI |
| `opyncorporates` | Python wrapper for OpenCorporates | `pip install opyncorporates` |

### H3. Nice-to-Have (Incremental Value)

| Resource | Purpose | Notes |
|---|---|---|
| `transphone` | Neural G2P for 8,000 languages | Heavier dependency, slower |
| `soundvectors` | Alternative to panphon | Newer, less tested |
| `morfessor` | Morphological segmentation | For morpheme transparency analysis |
| Brysbaert Concreteness | Concreteness ratings | Static CSV dataset |
| Glasgow Norms | Psycholinguistic word ratings | Static dataset |
| Google Custom Search API | SEO competitiveness | Requires API key + billing |
| WIPO Global Brand DB | International trademark search | Web scraping only |

---

## REFERENCES

[1] Parrish, A. `pronouncing` — A simple interface for the CMU Pronouncing Dictionary. [PyPI](https://pypi.org/project/pronouncing/) · [GitHub](https://github.com/aparrish/pronouncingpy)

[2] Mortensen, D.R. et al. `epitran` — A tool for transcribing orthographic text as IPA. [PyPI](https://pypi.org/project/epitran/) · [GitHub](https://github.com/dmort27/epitran)

[3] Bernard, M. & Titeux, H. `phonemizer` — Simple text to phones converter for multiple languages. [GitHub](https://github.com/bootphon/phonemizer) · [Docs](https://bootphon.github.io/phonemizer/)

[4] Li, X. et al. `transphone` — Phoneme tokenizer and G2P model for 8k languages. [GitHub](https://github.com/xinjli/transphone) · Paper: "Zero-shot Learning for Grapheme to Phoneme Conversion with Language Ensemble" (Findings of ACL 2022)

[5] Axel Springer. `DeepPhonemizer` — Transformer-based G2P. [GitHub](https://github.com/as-ideas/DeepPhonemizer)

[6] Goriely, Z. `g2p-plus` — Multi-backend G2P with PHOIBLE inventory matching. [GitHub](https://github.com/codebyzeb/g2p-plus)

[7] Mortensen, D.R. et al. (2016). "PanPhon: A Resource for Mapping IPA Segments to Articulatory Feature Vectors." *Proceedings of COLING 2016*, pp. 3475-3484. [GitHub](https://github.com/dmort27/panphon) · [Paper](https://aclanthology.org/C16-1328.pdf)

[8] Behrens, N. et al. (2024). "Generating Phonological Feature Vectors with SoundVectors and CLTS." *Computer-Assisted Language Comparison in Practice*, 7(2). [Article](https://calc.hypotheses.org/7224)

[9] PHOIBLE — Cross-linguistic phoneme inventory database. [phoible.org](https://phoible.org/)

[10] Vitevitch, M.S. & Luce, P.A. (2004). "A Web-based interface to calculate phonotactic probability for words and nonwords in English." *Behavior Research Methods*, 36, 481-487. [KU Phonotactic Probability Calculator](https://sll.ku.edu/phonotactic-probability) · [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC2553700/)

[11] Phonological CorpusTools. [Phonotactic Probability docs](https://corpustools.readthedocs.io/en/latest/phonotactic_probability.html)

[12] McAuliffe, M. & Hayes, B. `python-BLICK` — Phonotactic probability calculator for English. [PyPI](https://pypi.org/project/python-BLICK/) · [GitHub](https://github.com/mmcauliffe/python-BLICK) · [Original BLICK](http://linguistics.ucla.edu/people/hayes/BLICK/)

[13] Mayer, C. et al. "An online tool for computing phonotactic metrics." [Paper](https://sites.socsci.uci.edu/~cjmayer/papers/cmayer_et_al_phonotactic_calculator_submitted)

[14] Klink, R.R. (2000). "Creating Brand Names with Meaning: The Use of Sound Symbolism." *Marketing Letters*, 11(1), 5-20. [ResearchGate](https://www.researchgate.net/publication/225886900) — See also Klink (2001), Klink & Athaide (2012), Klink & Wu (2014) for extensions.

[15] Yorkston, E. & Menon, G. (2004). "Phonetic Effects of Brand Names on Consumer Judgments." *Journal of Consumer Research*, 31(1). [Stanford](https://web.stanford.edu/class/linguist62n/yorkston.pdf)

[16] Motoki, K., Velasco, C., & Spence, C. (2023). "The connotative meanings of sound symbolism in brand names: A conceptual framework." *Journal of Business Research*. [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0148296322005458)

[17] Ramachandran, V.S. & Hubbard, E.M. (2001). "Synaesthesia — A Window Into Perception, Thought and Language." *Journal of Consciousness Studies*, 8, 3-34. — See also Maurer et al. (2006) for developmental evidence.

[18] Watkins, A. (2019). *Hello, My Name Is Awesome: How to Create Brand Names That Stick* (2nd ed.). Berrett-Koehler Publishers. [Amazon](https://www.amazon.com/Hello-My-Name-Awesome-Create/dp/1626561869) · [eatmywords.com](https://eatmywords.com/brand-names-book/)

[19] Meyerson, R. (2022). *Brand Naming: The Complete Guide to Creating a Name for Your Company, Product, or Service*. [Amazon](https://www.amazon.com/Brand-Naming-Complete-Creating-Company/dp/1637421559) · Podcast: "How Brands Are Built"

[20] Wiktionary REST API. [Documentation](https://en.wiktionary.org/api/rest_v1/)

[21] Datamuse API. [Documentation](https://www.datamuse.com/api/) · Python wrapper: `python-datamuse`

[22] LDNOOBW — List of Dirty, Naughty, Obscene, and Otherwise Bad Words. [GitHub](https://github.com/LDNOOBW/List-of-Dirty-Naughty-Obscene-and-Otherwise-Bad-Words)

[23] `cuss` — Map of profane words to a sureness rating, multiple languages. [GitHub](https://github.com/words/cuss)

[24] `profanity.csv` — Multilingual profanity database with severity. [GitHub](https://github.com/4troDev/profanity.csv)

[25] `profanity-list` (dsojevic) — JSON-formatted profanity with severity, tags, exceptions. [GitHub](https://github.com/dsojevic/profanity-list)

[26] `washyourmouthoutwithsoap` — Multi-language bad word lists. [GitHub](https://github.com/thisandagain/washyourmouthoutwithsoap)

[27] USPTO TSDR API. [Developer Portal](https://developer.uspto.gov/api-catalog/tsdr-data-api) · [Trademark Search](https://www.uspto.gov/trademarks/search)

[28] USPTO Trademark API (RapidAPI). [Medium Guide Part 1](https://martonkodok.medium.com/uspto-trademark-api-search-trademark-owner-database-part-1-71274363605b) · [Part 2](https://martonkodok.medium.com/implementing-trademark-availability-and-search-using-uspto-trademark-api-part-2-19efc7e1cc6)

[29] Marker API — Trademark Search API. [markerapi.com](https://markerapi.com/)

[30] USPTO TESS. [tmsearch.uspto.gov](https://tmsearch.uspto.gov/)

[31] OpenCorporates API. [Documentation](https://api.opencorporates.com/documentation/API-Reference) · Python wrapper: [`opyncorporates`](https://github.com/pjryan126/opyncorporates) · [Bellingcat Guide](https://www.bellingcat.com/resources/2023/08/24/following-the-money-a-beginners-guide-to-using-the-opencorporates-api/)

[32] Speer, R. `wordfreq` — Word frequency in 40+ languages. [PyPI](https://pypi.org/project/wordfreq/) · [GitHub](https://github.com/rspeer/wordfreq)
