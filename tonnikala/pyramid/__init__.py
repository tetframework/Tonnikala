#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''This module allows the tonnikala templating language --
http://pypi.python.org/pypi/tonnikala/
-- to be used in the Pyramid web framework --
http://docs.pylonshq.com/

To enable the pyramid_tonnikala extension, do this:

.. code-block:: python

    from mootiro_web.pyramid_tonnikala import enable_tonnikala
    enable_tonnikala(config)

After this, files with these file extensions are considered to be
tonnikala templates: '.txt', '.xml', '.html', '.html5'.

Once the template loader is active, add the following to the
application section of your Pyramid application’s .ini file::

    [app:yourapp]
    # ... other stuff ...
    tonnikala.directory = myapp:templates

The tonnikala FileLoader class supports searching only one directory for
templates. As of 2011-01, if you want a search path, you must roll your own.
If you do... let us know.
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

@implementer(ITemplateRenderer)
class TonnikalaTemplateRenderer(object):
    def __init__(self, info, settings):
        self.info = info
        self.settings = settings

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

        template_name = os.path.join(self.settings['base_dir'], system['renderer_name'])
        template_string = pkg_resources.resource_string(self.settings['module'], template_name)

        compiled = tonnikala.loader.Loader(debug=True).load_string(template_string)
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


def enable_tonnikala(config, extensions=('.txt', '.xml', '.html', '.html5'), search_path=None):
    '''Sets up the tonnikala templating language for the specified
    file extensions.
    '''

    module_name, base_dir = search_path.split(':')

    settings = {
        'module'   : module_name,
        'base_dir' : base_dir
    }

    def renderer_factory(info):
        return TonnikalaTemplateRenderer(info, settings)

    for extension in extensions:
        config.add_renderer(extension, renderer_factory)


def add_tonnikala_extension(config, extension, search_path=None):
    if not extension.startswith('.'):
        extension = '.' + extension

    enable_tonnikala(config, extensions=(extension,), search_path=search_path)


def includeme(config):
    add_tonnikala_extension(config, '.tk')
    config.add_directive('add_tonnikala_extension', add_tonnikala_extension)
