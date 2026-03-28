"""Tests for the brand pipeline architecture."""

import os
import json
import shutil
import tempfile

import pytest

import brand
from brand.stages import Generate, Score, Filter, stage_from_dict, stages_to_dicts


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_scorers_registered(self):
        assert len(brand.scorers) > 20
        assert 'syllables' in brand.scorers
        assert 'dns_com' in brand.scorers
        assert 'novelty' in brand.scorers

    def test_generators_registered(self):
        assert len(brand.generators) >= 7
        assert 'cvcvcv' in brand.generators
        assert 'from_list' in brand.generators
        assert 'morpheme_combiner' in brand.generators

    def test_templates_available(self):
        templates = brand.list_templates()
        assert len(templates) == 10
        assert 'quick_screen' in templates
        assert 'tech_startup' in templates
        assert 'full_audit' in templates

    def test_scorer_metadata(self):
        meta = brand.scorers['dns_com']
        assert meta.requires_network is True
        assert meta.cost == 'cheap'

        meta = brand.scorers['syllables']
        assert meta.requires_network is False
        assert meta.cost == 'cheap'

    def test_custom_scorer_registration(self):
        @brand.scorers.register('_test_length', description='test scorer')
        def _test_length(name):
            return len(name)

        assert '_test_length' in brand.scorers
        assert brand.scorers['_test_length']('hello') == 5

    def test_registry_keyerror(self):
        with pytest.raises(KeyError, match='No scorer.*nonexistent'):
            brand.scorers['nonexistent']


# ---------------------------------------------------------------------------
# Scorer tests
# ---------------------------------------------------------------------------


class TestScorers:
    def test_syllables(self):
        assert brand.scorers['syllables']('banana') == 3
        assert brand.scorers['syllables']('a') == 1

    def test_novelty(self):
        assert brand.scorers['novelty']('the') == 0.0
        assert brand.scorers['novelty']('xyzqwk') == 1.0

    def test_existing_word(self):
        assert brand.scorers['existing_word']('apple') is True
        assert brand.scorers['existing_word']('xyzqwk') is False

    def test_substring_hazards(self):
        assert 'anal' in brand.scorers['substring_hazards']('analytics')
        assert brand.scorers['substring_hazards']('figiri') == []

    def test_sound_symbolism(self):
        result = brand.scorers['sound_symbolism']('figiri')
        assert isinstance(result, dict)
        assert 'profile' in result
        assert 'front_vowel_ratio' in result

    def test_keyboard_distance(self):
        assert brand.scorers['keyboard_distance']('asdf') == 1.0
        assert brand.scorers['keyboard_distance']('a') == 0.0

    def test_letter_balance(self):
        result = brand.scorers['letter_balance']('brand')
        assert result['ascender_ratio'] == 0.4
        assert result['has_descenders'] is False

    def test_name_length(self):
        assert brand.scorers['name_length']('brand') == 5

    def test_spelling_transparency(self):
        assert brand.scorers['spelling_transparency']('cat') > 0.5
        assert brand.scorers['spelling_transparency']('through') < 0.5


# ---------------------------------------------------------------------------
# Generator tests
# ---------------------------------------------------------------------------


class TestGenerators:
    def test_cvcvcv(self):
        names = list(brand.generators['cvcvcv'](consonants='b', vowels='a'))
        assert names == ['bababa']

    def test_from_list(self):
        names = list(brand.generators['from_list'](names=['alpha', 'beta']))
        assert names == ['alpha', 'beta']

    def test_morpheme_combiner(self):
        names = list(
            brand.generators['morpheme_combiner'](
                prefixes=['lum'], suffixes=['ix', 'io']
            )
        )
        assert sorted(names) == ['lumio', 'lumix']

    def test_pattern(self):
        names = list(
            brand.generators['pattern'](pattern='CV', consonants='b', vowels='a')
        )
        assert names == ['ba']

    def test_cvcvcv_filtered(self):
        names = list(
            brand.generators['cvcvcv_filtered'](consonants='b', vowels='ae')
        )
        assert 'bababa' in names


# ---------------------------------------------------------------------------
# Stage serialization tests
# ---------------------------------------------------------------------------


class TestStages:
    def test_generate_roundtrip(self):
        g = Generate('cvcvcv', params={'consonants': 'bdf'})
        d = g.to_dict()
        assert d['type'] == 'generate'
        g2 = Generate.from_dict(d)
        assert g2.generator == 'cvcvcv'
        assert g2.params == {'consonants': 'bdf'}

    def test_score_roundtrip(self):
        s = Score(['syllables', ('dns', {'tlds': ['.com']})])
        d = s.to_dict()
        assert d['type'] == 'score'
        s2 = Score.from_dict(d)
        assert s2.scorers[0] == 'syllables'
        assert s2.scorers[1] == ('dns', {'tlds': ['.com']})

    def test_filter_roundtrip(self):
        f = Filter(top_n=100, by='novelty', rules={'dns_com': True})
        d = f.to_dict()
        assert d['type'] == 'filter'
        f2 = Filter.from_dict(d)
        assert f2.top_n == 100
        assert f2.rules == {'dns_com': True}

    def test_stage_from_dict(self):
        s = stage_from_dict({'type': 'generate', 'generator': 'cvcvcv'})
        assert isinstance(s, Generate)

    def test_stages_to_from_dicts(self):
        stages = [Generate('cvcvcv'), Score(['syllables']), Filter(top_n=10)]
        dicts = stages_to_dicts(stages)
        assert len(dicts) == 3
        assert dicts[0]['type'] == 'generate'


# ---------------------------------------------------------------------------
# Pipeline tests
# ---------------------------------------------------------------------------


class TestPipeline:
    def test_simple_pipeline(self):
        results = brand.run_pipeline(
            [
                Generate('from_list', params={'names': ['alpha', 'beta', 'gamma']}),
                Score(['syllables', 'name_length']),
            ]
        )
        assert len(results['candidates']) == 3
        assert results['candidates'][0]['scores']['syllables'] > 0

    def test_pipeline_with_filter(self):
        results = brand.run_pipeline(
            [
                Generate(
                    'from_list',
                    params={'names': ['a', 'ab', 'abc', 'abcd', 'abcde']},
                ),
                Score(['name_length']),
                Filter(top_n=2, by='name_length'),
            ]
        )
        assert len(results['candidates']) == 2
        # Top 2 by length (descending) should be 'abcde' and 'abcd'
        names = [c['name'] for c in results['candidates']]
        assert 'abcde' in names
        assert 'abcd' in names

    def test_pipeline_with_rules_filter(self):
        results = brand.run_pipeline(
            [
                Generate(
                    'from_list', params={'names': ['hi', 'hello', 'hey']},
                ),
                Score(['name_length']),
                Filter(rules={'name_length': {'op': '>=', 'value': 3}}),
            ]
        )
        names = [c['name'] for c in results['candidates']]
        assert 'hi' not in names  # length 2
        assert 'hello' in names
        assert 'hey' in names

    def test_pipeline_with_names_param(self):
        results = brand.run_pipeline(
            [Score(['syllables'])],
            names=['alpha', 'beta'],
        )
        assert len(results['candidates']) == 2

    def test_pipeline_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            results = brand.run_pipeline(
                [
                    Generate(
                        'from_list', params={'names': ['alpha', 'beta']},
                    ),
                    Score(['syllables']),
                ],
                project_name='test_persist',
                pipeline_dir=tmpdir,
            )
            proj_dir = results['project_dir']
            assert os.path.exists(os.path.join(proj_dir, 'pipeline.json'))
            assert os.path.exists(os.path.join(proj_dir, 'final', 'results.json'))

            # Verify pipeline.json is valid
            with open(os.path.join(proj_dir, 'pipeline.json')) as f:
                pipeline_def = json.load(f)
            assert 'stages' in pipeline_def

    def test_template_loading(self):
        stages = brand.pipeline.load_template('quick_screen')
        assert len(stages) == 2
        assert isinstance(stages[0], Score)
        assert isinstance(stages[1], Filter)

    def test_evaluate_name(self):
        result = brand.evaluate_name('figiri')
        assert result['name'] == 'figiri'
        assert 'syllables' in result['scores']
        assert result['scores']['syllables'] == 3

    def test_different_templates_different_results(self):
        """Two templates should produce different scorer sets."""
        names = ['figiri', 'lumex', 'voxen']

        r1 = brand.run_pipeline('quick_screen', names=names)
        r2 = brand.run_pipeline(
            [
                Score(['syllables', 'name_length']),
                Filter(top_n=2, by='name_length'),
            ],
            names=names,
        )

        scores1 = set(r1['candidates'][0]['scores'].keys())
        scores2 = set(r2['candidates'][0]['scores'].keys())
        assert scores1 != scores2
        assert len(r1['candidates']) != len(r2['candidates'])
