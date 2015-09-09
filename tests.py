#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Unittests for restretto
"""

import unittest
import restretto


class LoaderExpansionsTestCase(unittest.TestCase):

    def test_expand_action_method(self):
        spec = {'url': '/some/url', 'headers': {}}
        expanded = restretto.loader.expand_action(spec)
        expected = {'method': 'get', 'url': '/some/url', 'headers': {}}
        self.assertEqual(expanded, expected)

    def test_expand_action_url(self):
        spec = {'put': '/url', 'json': [1, 2]}
        expanded = restretto.loader.expand_action(spec)
        expected = {'method': 'put', 'url': '/url', 'json': [1, 2]}
        self.assertEqual(expanded, expected)

    def test_expanded_action(self):
        spec = {'url': '/url', 'method': 'delete'}
        expanded = restretto.loader.expand_action(spec)
        expected = spec
        self.assertEqual(expected, expanded)

    def test_empty_action(self):
        spec = {'headers': {}, 'body': ''}
        with self.assertRaises(restretto.loader.ParseError):
            restretto.loader.expand_action(spec)

    def test_missing_url(self):
        spec = {'method': 'options'}
        with self.assertRaises(restretto.loader.ParseError):
            restretto.loader.expand_action(spec)

    def test_invalid_method(self):
        spec = {'url': '/url', 'method': 'bad_method'}
        with self.assertRaises(restretto.loader.ParseError):
            restretto.loader.expand_action(spec)

    def test_get_actions_requests(self):
        spec = {'actions': [], 'requests': []}
        with self.assertRaises(Exception):
            restretto.loader.get_actions(spec)

    def test_assertion_conflict(self):
        spec = {
            'url': '/',
            'expect': [{'status': '4xx'}],
            'assert': [{'header': 'Content-Type'}]
        }
        with self.assertRaises(restretto.loader.ParseError):
            restretto.loader.expand_action(spec)

    def test_get_actions(self):
        spec = {'actions': [{'url': '/sample'}]}
        alt_spec = {'requests': [{'url': '/sample'}]}
        actions = restretto.loader.get_actions(spec)
        requests = restretto.loader.get_actions(alt_spec)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions, requests)

    def test_get_asserts(self):
        spec = {
            'url': '/url',
            'assert': [
                {'status': '200'}
            ]
        }
        expanded = restretto.loader.expand_action(spec)
        expected = {
            'url': '/url',
            'method': 'get',
            'assert': [
                {'status': '200'}
            ]
        }
        self.assertEqual(expanded, expected)

    def test_get_expect(self):
        spec = {
            'url': '/url',
            'expect': [
                {'status': '500'}
            ]
        }
        expanded = restretto.loader.expand_action(spec)
        expected = {
            'url': '/url',
            'method': 'get',
            'assert': [
                {'status': '500'}
            ]
        }
        self.assertEqual(expanded, expected)


class AssertsTestCase(unittest.TestCase):

    class Response(object):

        def __init__(self, status_code, headers={}, text=None, json=None):
            self.status_code = status_code
            self.headers = headers
            self.text = text
            self.json = json
            self.ok = status_code in range(200, 299)

    def test_response_ok(self):
        assertion = restretto.assertions.Assert()
        resp = self.Response(200)
        self.assertTrue(assertion.test(resp))

    def test_response_not_ok(self):
        assertion = restretto.assertions.Assert()
        resp = self.Response(404)
        with self.assertRaises(AssertionError):
            assertion.test(resp)

    def test_status(self):
        spec = [{'status': '500'}]
        assertion = restretto.assertions.Assert(spec)
        resp = self.Response(500)
        self.assertTrue(assertion.test(resp))
        resp = self.Response(501)
        with self.assertRaises(AssertionError):
            assertion.test(resp)

    def test_status_match(self):
        spec = [{'status': '4xx'}]
        assertion = restretto.assertions.Assert(spec)
        resp = self.Response(403)
        self.assertTrue(assertion.test(resp))
        resp = self.Response(501)
        with self.assertRaises(AssertionError):
            assertion.test(resp)

    def test_status_in(self):
        spec = [{'status': ['401']}]
        assertion = restretto.assertions.Assert(spec)
        resp = self.Response(401)
        self.assertTrue(assertion.test(resp))
        resp = self.Response(404)
        with self.assertRaises(AssertionError):
            assertion.test(resp)

    def test_header_exists(self):
        spec = [{'header': 'Content-Type'}]
        assertion = restretto.assertions.Assert(spec)
        resp = self.Response(200, headers={'Content-Type': 'text/plain'})
        self.assertTrue(assertion.test(resp))
        resp = self.Response(404, headers={'x-bar': 'y-foo'})
        with self.assertRaises(AssertionError):
            assertion.test(resp)

    def test_header_is(self):
        spec = [{'header': 'Content-Type', 'is': 'text/html'}]
        assertion = restretto.assertions.Assert(spec)
        resp = self.Response(200, headers={'Content-Type': 'text/html'})
        self.assertTrue(assertion.test(resp))
        resp = self.Response(200, headers={'Content-Type': 'text/plain'})
        with self.assertRaises(AssertionError):
            assertion.test(resp)

    def test_header_contains(self):
        spec = [{'header': 'Content-Type', 'contains': 'xml'}]
        assertion = restretto.assertions.Assert(spec)
        resp = self.Response(200, headers={'Content-Type': 'application/xml+xhtml'})
        self.assertTrue(assertion.test(resp))
        resp = self.Response(200, headers={'Content-Type': 'text/html'})
        with self.assertRaises(AssertionError):
            assertion.test(resp)

    def test_body_text(self):
        spec = [{'body': 'text'}]
        assertion = restretto.assertions.Assert(spec)
        resp = self.Response(200, text='Sample')
        self.assertTrue(assertion.test(resp))
        resp = self.Response(200, text=None)
        with self.assertRaises(AssertionError):
            assertion.test(resp)

    def test_body_text_is(self):
        spec = [{'body': 'text', 'is': 'sample'}]
        assertion = restretto.assertions.Assert(spec)
        resp = self.Response(200, text='sample')
        self.assertTrue(assertion.test(resp))
        resp = self.Response(200, text='other')
        with self.assertRaises(AssertionError):
            assertion.test(resp)

    def test_body_text_contains(self):
        spec = [{'body': 'text', 'contains': 'llo wo'}]
        assertion = restretto.assertions.Assert(spec)
        resp = self.Response(200, text='hello world')
        self.assertTrue(assertion.test(resp))
        resp = self.Response(200, text='ehlo world')
        with self.assertRaises(AssertionError):
            assertion.test(resp)


class TemplatingTestCase(unittest.TestCase):

    VARS = {
        'server': 'httpbin.org',
        'scheme': 'http',
        'extra': {
            'header': 'X-Custom',
            'value': 'custom-value',
            'payload_data': 'hello from vars'
        },
        'val': 100,
        'accept': 'application/json'
    }

    def test_template_complex(self):
        src = {
            'url': '{{scheme}}://{{server}}/base',
            'headers': {
                'Accept': '{{accept}}'
            },
            'expect': [
                {'header': '{{extra.header}}', 'is': '{{extra.value}}'},
                {'body': 'text', 'is': '{{extra.payload_data}}'}
            ],
            'json': {
                'option': 12,
                'content': ['{{val}}']
            }
        }
        result = restretto.templating.apply_context(src, self.VARS)
        expected = {
            'url': 'http://httpbin.org/base',
            'headers': {
                'Accept': 'application/json'
            },
            'expect': [
                {'header': 'X-Custom', 'is': 'custom-value'},
                {'body': 'text', 'is': 'hello from vars'}
            ],
            'json': {
                'option': 12,
                'content': ['100']
            }
        }
        self.assertEqual(result, expected)

class LoaderFileLoadTestCase(unittest.TestCase):

    def test_load_unexisting_file(self):
        with self.assertRaises(FileNotFoundError):
            restretto.loader.load("test-data/unesixtant_file.yml")

    def test_load_empty_file(self):
        data = restretto.loader.load("test-data/empty.yml")
        self.assertFalse(data)

    def test_load_bad_file(self):
        with self.assertRaises(Exception):
            restretto.loader.load("test-data/broken/bad.yml")

    def test_load_valid_file(self):
        data = restretto.loader.load("test-data/simple.yml")
        self.assertEqual(len(data), 1)

    def test_empty_actions(self):
        data = restretto.loader.load('test-data/empty-actions.yml')
        self.assertFalse(data)

    def test_missing_actions(self):
        data = restretto.loader.load('test-data/missing-actions.yml')
        self.assertFalse(data)

    def test_actions_requests_error(self):
        with self.assertRaises(restretto.loader.ParseError):
            restretto.loader.load('test-data/broken/actions-with-requests.yml')


class LoaderDirLoadTestCase(unittest.TestCase):

    def test_load_from_dir(self):
        data = restretto.loader.load("test-data/")
        self.assertEqual(len(data), 3)

    def test_load_from_unexistant_dir(self):
        with self.assertRaises(FileNotFoundError):
            restretto.loader.load("test-data/missing-dir")

    def test_load_from_bad_dir(self):
        with self.assertRaises(Exception):
            restretto.loader.load("test-data/broken")


if __name__ == "__main__":
    unittest.main()
