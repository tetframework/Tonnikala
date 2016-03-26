#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module allows the tonnikala templating language --
http://pypi.python.org/pypi/tonnikala/

-- to be used in the Pyramid web framework --
http://docs.pylonshq.com/
"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import pkg_resources
from pyramid.compat import is_nonstr_iter
from pyramid.settings import asbool, aslist

import tonnikala.loader


class PyramidTonnikalaLoader(tonnikala.loader.FileLoader):
    def __init__(self):
        super(PyramidTonnikalaLoader, self).__init__()
        self.search_paths = []

    def add_search_path(self, module, directory):
        """
        Add a search path for the loader. Module if not None,
        is a package, relative to which we are locating the
        module.
        """

        self.search_paths.append((module, directory))

    def resolve(self, name):
        """
        Resolve the name using the given search paths.
        """

        if ':' in name:
            try:
                module, path = name.split(':', 1)
                name = pkg_resources.resource_filename(module, path)
                if name and os.path.exists(name):
                    return name

            except Exception:
                pass

        for module, directory in self.search_paths:
            path = os.path.join(directory, name)
            if module:
                path = pkg_resources.resource_filename(module, path)

            if os.path.exists(path):
                return path

        return super(PyramidTonnikalaLoader, self).resolve(name)


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

        name = system['renderer_name']
        compiled = self.loader.load(name)

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


class TonnikalaRendererFactory(object):
    def __init__(self):
        self.debug = False
        self.loader = PyramidTonnikalaLoader()

    def set_reload(self, flag):
        self.loader.set_reload(flag)

    def add_search_path(self, module, path):
        self.loader.add_search_path(module, path)

    def __call__(self, info):
        return TonnikalaTemplateRenderer(info, self.loader, debug=self.debug)


def add_tonnikala_extensions(config, *extensions):
    for extension in extensions:
        if not extension.startswith('.'):
            extension = '.' + extension

        config.add_renderer(extension,
                            config.registry.tonnikala_renderer_factory)


def add_tonnikala_search_paths(config, *paths):
    for path in paths:
        module_name, dummy, base_dir = path.partition(':')
        if not base_dir:
            base_dir = module_name
            module_name = None

        config.registry.tonnikala_renderer_factory.add_search_path(module_name,
                                                                   base_dir)


def set_tonnikala_reload(config, flag):
    """
    Sets the reload flag for tonnikala template renderer.
    If True, the templates are reload if changed
    """

    config.registry.tonnikala_renderer_factory.set_reload(flag)


def includeme(config):
    if hasattr(config.registry, 'tonnikala_renderer_factory'):
        return

    config.registry.tonnikala_renderer_factory = TonnikalaRendererFactory()

    config.add_directive('add_tonnikala_extensions', add_tonnikala_extensions)
    config.add_directive('add_tonnikala_search_paths',
                         add_tonnikala_search_paths)
    config.add_directive('set_tonnikala_reload', set_tonnikala_reload)

    settings = config.registry.settings

    if 'tonnikala.extensions' in settings:
        extensions = settings['tonnikala.extensions']
        if not is_nonstr_iter(extensions):
            extensions = aslist(extensions, flatten=True)

        config.add_tonnikala_extensions(*extensions)

    if 'tonnikala.search_paths' in settings:
        paths = settings['tonnikala.search_paths']
        if not is_nonstr_iter(paths):
            paths = aslist(paths, flatten=True)

        config.add_tonnikala_search_paths(*paths)

    tk_reload = settings.get('tonnikala.reload')
    if tk_reload is None:
        tk_reload = settings.get('pyramid.reload_templates')

    config.set_tonnikala_reload(asbool(tk_reload))
