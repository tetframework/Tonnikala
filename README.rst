=========
Tonnikala
=========
Tonnikala is the latest reincarnation among the Python templating languages that feed on Kid-inspired XML syntax.
It rejects the Kid and Genshi notions of tagstreams and trees, and follows in footsteps of Chameleon and Kajiki 
in making the template to compile into Python bytecode directly. The syntax is very close to that of Kajiki, but
the internals are very different: Tonnikala writes code as Abstract Syntax Trees and optimizes the resulting trees
extensively. In addition, there is an optional speed-up module (currently Python 3), that provides a specialized 
class used for output buffering.

Examples
========

.. code-block:: python
   :linenos:

    from tonnikala.loader import Loader

    template_source = u"""
    <table>
        <tr py:for="row in table">
            <py:for each="key, value in row.items()"><td>${key}</td><td>${literal(value)}</td></py:for>
        </tr>
    </table>
    """
    
    template = Loader().load_string(template_source)

    ctx = {
        'table': [dict(a=1,b=2,c=3,d=4,e=5,f=6,g=7,h=8,i=9,j=10)
            for x in range(1000)]
    }

    print(template.render(ctx))

Template inheritance
====================

base.tk
-------

.. code-block:: python
   :linenos:

    <html>
    <title><py:block name="title_block">I am ${title}</py:block></title>
    <h1>${title_block()}</h1>
    </html>

child.tk
--------

.. code-block:: python
   :linenos:

    <py:extends href="base.tk">
    <py:block name="title_block">But I am ${title} instead</py:block>
    </py:extends>

FileLoader
==========

To load templates from files, use the tonnikala.FileLoader class:

.. code-block:: python
   :linenos:

    loader = FileLoader(paths=['/path/to/templates'])
    template = loader.load('child.tk')

A FileLoader currently implicitly caches *all* loaded templates in memory.

Template
========

To render the template:

.. code-block:: python
   :linenos:

    result = template.render(ctx)

You can specify a block, or no-argument def to render explicitly:

.. code-block:: python
   :linenos:

    result = template.render(ctx, funcname='title_block')

Status
======

Alpha, working features are 

* Structural elements ``py:if``, ``py:unless``, ``py:def``, ``py:for``, ``py:replace``, ``py:content``
* Basic template inheritance: ``py:extends`` and ``py:block``; the child template also inherits top level
  function declarations from the parent template, and the child can override global functions that 
  the parent defines and uses.
* Expression interpolation using $simple_identifier and ${complex + python + "expression"}
* Boolean attributes: ``<tag attr="${False}">``, ``<tag attr="$True">``
* Implicit escaping
* Disabling implicit escaping (``literal()``)
* Python 3 speedups

Upcoming features:

* Structural elements: ``py:vars``, ``py:switch``, ``py:case``; ``py:else`` for ``for``, ``if`` and ``switch``.
* Python 2 speedups
* Custom tags mapping to ``py:def``
* I18N with optional in-parse-tree localization
* Javascript as the target language
* Pluggable frontend syntax engines
* Pluggable expression languages akin to Chameleon
* Even better template inheritance
* Importing def blocks from another template: ``py:import``
* Documentation
* Pyramid integration

Contributors
============

Antti Haapala
