#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/thumbor/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com

from collections import defaultdict

import tornado
from preggy import expect

from thumbor.context import ServerParameters
from thumbor.importer import Importer
from thumbor.storages.mixed_storage import Storage as MixedStorage
from thumbor.storages.no_storage import Storage as NoStorage

from tests.base import TestCase


class Storage(object):
    def __init__(self, security_key):
        self.storage = defaultdict(dict)
        self.security_key = security_key

    def put(self, path, contents):
        self.storage[path]['path'] = path
        self.storage[path]['contents'] = contents

    def put_crypto(self, path):
        self.storage[path]['crypto'] = self.security_key

    def put_detector_data(self, path, data):
        self.storage[path]['detector'] = data

    def get_crypto(self, path):
        if path not in self.storage:
            raise RuntimeError('%s was not found in storage' % path)

        return self.storage[path]['crypto']

    def get_detector_data(self, path):
        if path not in self.storage or 'detector' not in self.storage[path]:
            return None

        return self.storage[path]['detector']

    def get(self, path):
        if path not in self.storage:
            raise RuntimeError('%s was not found in storage' % path)

        return self.storage[path]['contents']


class BaseMidexStorageTestCase(TestCase):
    def get_storages(self):
        return Storage('security-key'), Storage('security-key'), Storage('detector')

    def get_context(self, *args, **kwargs):
        context = super(BaseMidexStorageTestCase, self).get_context(*args, **kwargs)
        self.storage = MixedStorage(None, *self.get_storages())
        self.storage.put('path1', 'contents')
        self.storage.put_crypto('path1')
        self.storage.put_detector_data('path1', 'detector')
        return context

    def get_server(self, *args, **kwargs):
        server = ServerParameters(8888, 'localhost', 'thumbor.conf', None, 'info', None)
        server.security_key = 'ACME-SEC'
        return server

    def get_importer(self, *args, **kwargs):
        return Importer(self.config)


class MixedStorageTestCase(BaseMidexStorageTestCase):
    @tornado.testing.gen_test
    def test_mixed_storage_put_includes_path(self):
        expect(self.storage.file_storage.storage['path1']['path']).to_equal('path1')
        expect(self.storage.file_storage.storage['path1']['contents']).to_equal('contents')

        contents = yield self.storage.get('path1')
        expect(contents).to_equal('contents')
        expect(self.storage.file_storage.storage['path1']).not_to_include('crypto')
        expect(self.storage.crypto_storage.storage['path1']).not_to_include('contents')
        expect(self.storage.crypto_storage.storage['path1']['crypto']).to_equal('security-key')

        contents = yield self.storage.get_crypto('path1')
        expect(contents).to_equal('security-key')

        contents = yield self.storage.get_detector_data('path1')
        expect(contents).to_equal('detector')


class MixedStorageFromConfTestCase(BaseMidexStorageTestCase):
    def get_context(self, *args, **kwargs):
        context = super(MixedStorageFromConfTestCase, self).get_context(*args, **kwargs)
        self.storage = MixedStorage(context)
        return context

    @tornado.testing.gen_test
    def test_get_data(self):
        path = yield self.storage.get('path')
        file_storage, crypto_storage, detector_storage = self.get_storages()
        expect(self.storage.file_storage).to_be_instance_of(NoStorage)
        expect(path).to_be_null()

    @tornado.testing.gen_test
    def test_get_detector_data(self):
        path = yield self.storage.get_detector_data('path')
        expect(self.storage.detector_storage).to_be_instance_of(NoStorage)
        expect(path).to_be_null()

    @tornado.testing.gen_test
    def test_get_crypto(self):
        path = yield self.storage.get_crypto('path')
        expect(self.storage.crypto_storage).to_be_instance_of(NoStorage)
        expect(path).to_be_null()
