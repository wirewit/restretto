#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Unittests for restretto
"""

import unittest
import restretto
import restretto.cli


class ResourceTestCase(unittest.TestCase):

    def test_parse_from_str(self):
        spec = '/some/uri'
        res = restretto.Resource(spec)
        expected = {'method': 'get', 'url': spec}
        self.assertEqual(res.request, expected)

    def test_expand_resource_method(self):
        spec = {'url': '/some/url', 'headers': {}}
        action = restretto.Resource(spec)
        expected = {'method': 'get', 'url': '/some/url', 'headers': {}}
        self.assertEqual(action.request, expected)

    def test_expand_resource_url(self):
        spec = {'put': '/url', 'json': [1, 2]}
        expanded = restretto.Resource(spec)
        expected = {'method': 'put', 'url': '/url', 'json': [1, 2]}
        self.assertEqual(expanded.request, expected)

    def test_expanded_resource(self):
        spec = {'url': '/url', 'method': 'delete'}
        expanded = restretto.Resource(spec)
        expected = spec
        self.assertEqual(expected, expanded.request)

    def test_empty_resource(self):
        spec = {'headers': {}, 'body': ''}
        with self.assertRaises(restretto.errors.ParseError):
            restretto.Resource(spec)

    def test_missing_url(self):
        spec = {'method': 'options'}
        with self.assertRaises(restretto.errors.ParseError):
            restretto.Resource(spec)

    def test_invalid_method(self):
        spec = {'url': '/url', 'method': 'bad_method'}
        with self.assertRaises(restretto.errors.ParseError):
            restretto.Resource(spec)

    def test_assertion_conflict(self):
        spec = {
            'url': '/',
            'expect': [{'status': '4xx'}],
            'assert': [{'header': 'Content-Type'}]
        }
        with self.assertRaises(restretto.errors.ParseError):
            restretto.Resource(spec)

    def test_get_asserts(self):
        spec = {
            'url': '/url',
            'assert': [
                {'status': '200'}
            ]
        }
        action = restretto.Resource(spec)
        expected_request = {
            'url': '/url',
            'method': 'get',
        }
        expected_asserts = [
            {'status': '200'}
        ]
        self.assertEqual(action.request, expected_request)
        self.assertEqual(action.asserts, expected_asserts)

    def test_get_expect(self):
        spec = {
            'url': '/url',
            'expect': [
                {'status': '500'}
            ]
        }
        action = restretto.Resource(spec)
        expected_request = {
            'url': '/url',
            'method': 'get',
        }
        expected_asserts = [
            {'status': '500'}
        ]
        self.assertEqual(action.request, expected_request)
        self.assertEqual(action.asserts, expected_asserts)


class SessionTestCase(unittest.TestCase):

    def test_context(self):
        ctx = {'server': 'httpbin.org', 'token': 'secret'}
        spec = {
            'title': 'Sample',
            'baseUri': 'http://{{server}}',
            'headers': {
                "X-Auth-Token": "{{token}}"
            },
            'actions': []
        }
        session = restretto.Session(spec, ctx)
        self.assertEqual(session.baseUri, 'http://httpbin.org')
        self.assertEqual(session.headers, {'X-Auth-Token': 'secret'})


class AssertsTestCase(unittest.TestCase):

    class Response(object):

        def __init__(self, status_code, headers={}, text=None, json=None):
            self.status_code = status_code
            self.headers = headers
            self.text = text
            self.json = json
            self.ok = status_code in range(200, 299)
            self.reason = 'reason'

        def __bool__(self):
            return self.ok

    def test_response_ok(self):
        assertion = restretto.assertions.Assert()
        resp = self.Response(200)
        self.assertTrue(assertion.test(resp))

    def test_response_not_ok(self):
        assertion = restretto.assertions.Assert()
        resp = self.Response(404)
        with self.assertRaises(restretto.errors.ExpectError):
            assertion.test(resp)

    def test_status(self):
        spec = [{'status': '500'}]
        assertion = restretto.assertions.Assert(spec)
        resp = self.Response(500)
        self.assertTrue(assertion.test(resp))
        resp = self.Response(501)
        with self.assertRaises(restretto.errors.ExpectError):
            assertion.test(resp)

    def test_status_match(self):
        spec = [{'status': '4xx'}]
        assertion = restretto.assertions.Assert(spec)
        resp = self.Response(403)
        self.assertTrue(assertion.test(resp))
        resp = self.Response(501)
        with self.assertRaises(restretto.errors.ExpectError):
            assertion.test(resp)

    def test_status_in(self):
        spec = [{'status': ['401']}]
        assertion = restretto.assertions.Assert(spec)
        resp = self.Response(401)
        self.assertTrue(assertion.test(resp))
        resp = self.Response(404)
        with self.assertRaises(restretto.errors.ExpectError):
            assertion.test(resp)

    def test_header_exists(self):
        spec = [{'header': 'Content-Type'}]
        assertion = restretto.assertions.Assert(spec)
        resp = self.Response(200, headers={'Content-Type': 'text/plain'})
        self.assertTrue(assertion.test(resp))
        resp = self.Response(404, headers={'x-bar': 'y-foo'})
        with self.assertRaises(restretto.errors.ExpectError):
            assertion.test(resp)

    def test_header_is(self):
        spec = [{'header': 'Content-Type', 'is': 'text/html'}]
        assertion = restretto.assertions.Assert(spec)
        resp = self.Response(200, headers={'Content-Type': 'text/html'})
        self.assertTrue(assertion.test(resp))
        resp = self.Response(200, headers={'Content-Type': 'text/plain'})
        with self.assertRaises(restretto.errors.ExpectError):
            assertion.test(resp)

    def test_header_contains(self):
        spec = [{'header': 'Content-Type', 'contains': 'xml'}]
        assertion = restretto.assertions.Assert(spec)
        resp = self.Response(200, headers={'Content-Type': 'application/xml+xhtml'})
        self.assertTrue(assertion.test(resp))
        resp = self.Response(200, headers={'Content-Type': 'text/html'})
        with self.assertRaises(restretto.errors.ExpectError):
            assertion.test(resp)

    def test_body_text(self):
        spec = [{'body': 'text'}]
        assertion = restretto.assertions.Assert(spec)
        resp = self.Response(200, text='Sample')
        self.assertTrue(assertion.test(resp))
        resp = self.Response(200, text=None)
        with self.assertRaises(restretto.errors.ExpectError):
            assertion.test(resp)

    def test_body_text_is(self):
        spec = [{'body': 'text', 'is': 'sample'}]
        assertion = restretto.assertions.Assert(spec)
        resp = self.Response(200, text='sample')
        self.assertTrue(assertion.test(resp))
        resp = self.Response(200, text='other')
        with self.assertRaises(restretto.errors.ExpectError):
            assertion.test(resp)

    def test_body_text_contains(self):
        spec = [{'body': 'text', 'contains': 'llo wo'}]
        assertion = restretto.assertions.Assert(spec)
        resp = self.Response(200, text='hello world')
        self.assertTrue(assertion.test(resp))
        resp = self.Response(200, text='ehlo world')
        with self.assertRaises(restretto.errors.ExpectError):
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
        'accept': 'application/json',
        "nested": {
            "simple": "string",
            "items": [1, 2, 3],
            "obj": {
                "inner": True,
                "nested_items": ["a", "b"],
                "nested_obj": {
                    "x": "y"
                }
            }
        }
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
        result = restretto.utils.apply_context(src, self.VARS)
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
                'content': [100]
            }
        }
        self.assertEqual(result, expected)

    def test_nested_and_list(self):
        src = {
            "simple": "{{ server }}",
            "concatenated": "{{scheme}}://{{server}}",
            "items": [
                "{{accept}}",
                "{{extra.header}}:{{extra.value}}"
            ],
            "nested": "{{nested}}"
        }
        result = restretto.utils.apply_context(src, self.VARS)
        expected = {
            "simple": "httpbin.org",
            "concatenated": "http://httpbin.org",
            "items": [
                "application/json",
                "X-Custom:custom-value"
            ],
            "nested": self.VARS["nested"]
        }
        self.assertEqual(result, expected)

class LoaderFileLoadTestCase(unittest.TestCase):

    def test_load_unexisting_file(self):
        with self.assertRaises(FileNotFoundError):
            restretto.load("test-data/unesixtant_file.yml")

    def test_load_empty_file(self):
        data = restretto.load("test-data/empty.yml")
        self.assertFalse(data)

    def test_load_bad_file(self):
        with self.assertRaises(Exception):
            restretto.load("test-data/broken/bad.yml")

    def test_load_valid_file(self):
        data = restretto.load("test-data/valid/simple.yml")
        self.assertEqual(len(data), 1)

    def test_empty_resources(self):
        data = restretto.load('test-data/empty-resources.yml')
        self.assertFalse(data)

    def test_missing_resources(self):
        data = restretto.load('test-data/missing-resources.yml')
        self.assertFalse(data)


class LoaderDirLoadTestCase(unittest.TestCase):

    def test_load_from_dir(self):
        data = restretto.load("test-data/valid")
        self.assertEqual(len(data), 3)

    def test_load_from_unexistant_dir(self):
        with self.assertRaises(FileNotFoundError):
            restretto.load("test-data/missing-dir")

    def test_load_from_bad_dir(self):
        with self.assertRaises(Exception):
            restretto.load("test-data/broken")


class OptionsTestCase(unittest.TestCase):

    def test_convert_single(self):
        encoded = "key=val"
        options = restretto.cli.options(encoded)
        self.assertEqual(options, {"key": "val"})

    def test_convert_multi(self):
        encoded = "key=val,other=second, yet=another again "
        options = restretto.cli.options(encoded)
        expected = {
            "key": "val",
            "other": "second",
            "yet": "another again"
        }
        self.assertEqual(options, expected)

    def test_convert_empty_val(self):
        encoded = "oops=, second=two"
        expected = {
            "oops": "",
            "second": "two"
        }
        options = restretto.cli.options(encoded)
        self.assertEqual(options, expected)

    def test_convert_empty_key(self):
        with self.assertRaises(restretto.cli.ArgumentTypeError):
            restretto.cli.options("=value")

    def test_convert_empty_keyval(self):
        with self.assertRaises(restretto.cli.ArgumentTypeError):
            restretto.cli.options(" = ")


if __name__ == "__main__":
    unittest.main()
