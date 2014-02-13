#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''This module allows the tonnikala templating language --
http://pypi.python.org/pypi/tonnikala/

-- to be used in the Pyramid web framework --
http://docs.pylonshq.com/
'''

from __future__ import (absolute_import, division, print_function,
    unicode_literals)

import os
from zope.interface import implementer, Interface
from pyramid.interfaces import ITemplateRenderer
from pyramid.resource import abspath_from_resource_spec
import pkg_resources
import tonnikala
import tonnikala.loader
import six


class PyramidTonnikalaLoader(tonnikala.loader.FileLoader):
    def __init__(self, settings):
        super(PyramidTonnikalaLoader, self).__init__()
        self.settings = settings

    def resolve(self, name):
        template_name = os.path.join(self.settings['base_dir'], name)
        path = pkg_resources.resource_filename(self.settings['module'], template_name)

        if os.path.exists(path):
            return path

        return super(PyramidTonnikalaLoader, self).resolve(name)


@implementer(ITemplateRenderer)
class TonnikalaTemplateRenderer(object):
    def __init__(self, info, loader, debug=True):
        self.info = info
        self.loader = loader
        self.debug = debug

    def implementation(self):
        return self

    def __call__(self, value, system, fragment=False):
        """ ``value`` is the result of the view.
        Returns a result (a string or unicode object useful as a
        response body). Values computed by the system are passed in the
        ``system`` parameter, which is a dictionary containing:

        * ``view`` (the view callable that returned the value),
        * ``renderer_name`` (the template name or simple name of the renderer),
        * ``context`` (the context object passed to the view), and
        * ``request`` (the request object passed to the view).
        """

        compiled = self.loader.load(system['renderer_name'])

        try:
            system.update(value)
        except (TypeError, ValueError):
            raise ValueError('TonnikalaTemplateRenderer was passed a '
                             'non-dictionary as value.')

        finalize = str
        if fragment:
            finalize = lambda x: x

        return finalize(compiled.render(system))

    def fragment(self, tmpl, value, system):
        system['renderer_name'] = tmpl
        return self(value, system, fragment=True)


def enable_tonnikala(config, extensions=('.txt', '.xml', '.html', '.html5'),
                     search_path=None, debug=False):
    '''Sets up the tonnikala templating language for the specified
    file extensions.
    '''

    module_name, base_dir = search_path.split(':')

    settings = {
        'module'   : module_name,
        'base_dir' : base_dir
    }

    loader = PyramidTonnikalaLoader(settings)

    def renderer_factory(info):
        return TonnikalaTemplateRenderer(info, loader, debug=debug)

    for extension in extensions:
        config.add_renderer(extension, renderer_factory)


def add_tonnikala_extension(config, extension, search_path=None):
    if not extension.startswith('.'):
        extension = '.' + extension

    enable_tonnikala(config, extensions=(extension,), search_path=search_path)


def includeme(config):
    config.add_directive('add_tonnikala_extension', add_tonnikala_extension)
