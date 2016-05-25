Tonnikala
=========

.. image:: https://badges.gitter.im/Join%20Chat.svg
   :alt: Join the chat at https://gitter.im/tetframework/Tonnikala
   :target: https://gitter.im/tetframework/Tonnikala?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge

.. image:: https://next.travis-ci.org/tetframework/Tonnikala.svg?branch=master
   :target: https://next.travis-ci.org/tetframework/Tonnikala

.. image:: https://coveralls.io/repos/github/tetframework/Tonnikala/badge.svg?branch=master
   :target: https://coveralls.io/github/tetframework/Tonnikala?branch=master 


Tonnikala is the latest reincarnation among the Python templating 
languages that feed on Kid-inspired XML syntax. It doesn't use the tagstreams and trees
of Genshi or Kid, but follows in footsteps of Chameleon and Kajiki in making the 
template to compile into Python bytecode directly. The syntax is very close to that of 
Kajiki, but the internals are very different: Tonnikala writes code 
as Abstract Syntax Trees and optimizes the resulting trees 
extensively. In addition, there is an optional speed-up module, 
that provides a specialized class used 
for output buffering.

Examples
--------

.. code-block:: python

    from tonnikala.loader import Loader

    template_source = u"""
    <table>
        <tr py:for="row in table">
            <py:for each="key, value in row.items()"
                ><td>$key</td><td>$literal(value)</td></py:for>
        </tr>
    </table>
    """
    
    template = Loader().load_string(template_source)

    ctx = {
        'table': [dict(a=1,b=2,c=3,d=4,e=5,f=6,g=7,h=8,i=9,j=10)
            for x in range(1000)]
    }

    print(template.render(ctx))


Variable interpolation
----------------------

Within attributes and text, all contents starting with ``$`` followed
by a ``{``, an alphabetic character or ``_`` is considered an interpolated expression.
If the interpolated expression starts with ``${``, the expression continues until the matching ``}`` token.
Otherwise the interpolation consists of an identifier, followed by any number of attribute accesses,
indexing brackets ``[...]``, and method call operators ``(...)``, without any 
intervening whitespace (except within the brackets). The expression
parsing stops whenever the next token cannot match this rule anymore. 

While the form

.. code-block:: xml

    HELLO, ${user.name.upper()}.

is accepted, it is also perfectly OK to write

.. code-block:: xml

    HELLO, $user.name.upper().

In the above code, ``user`` is an object with ``name`` attribute or property, which
evaluates to a string; ``upper()`` method  is called on the resulting string.
Suppose the user's name is Antti Haapala, the resulting output would be 
``HELLO, ANTTI HAAPALA.``. 

The rules also ensure that you can do an interpolation as follows:

.. code-block:: xml

    Your word $digit has the integer value ${{'one': 1, 'two': 2}[digit]}
 
Now, if ``digit == 'one'``, the output of this fragment would be

.. code-block:: xml

    Your word one has the integer value 1.

An interpolated expression is auto-escaped appropriately for its context. If you do
not want to be the expression to be escaped you can bracket it with a function
call to ``literal()``, or in ``markupsafe.Markup``. The ``literal`` is especially
efficient as it is optimized away in the compile time whenever possible.


Control tags/attributes
-----------------------

Most of the control tags and attributes have a reach of one element (those which do 
not, have an effect for the whole file). For all these you have the choice of 
using them as an attribute or as an element; e.g.

.. code-block:: xml

    <py:for each="i in iterable"></py:for>

or 

.. code-block:: xml

    <div py:for="i in iterable"></div>

The latter attribute form is preferred as they are more concise, but sometimes clarity
or structure necessitates the use of the element form.


``py:if``
+++++++++ 


.. code-block:: xml

    <py:if test="condition"><span>the condition was true</span></py:if>

or 

.. code-block:: xml

    <span py:if="condition">the condition was true</span>

results in the output

.. code-block:: xml

    <span>the condition was true</span>

if the ``condition`` was true

``py:unless``
+++++++++++++

``py:unless="expression"`` is an alternative way to type ``py:if="not expression"``.

``py:for``
++++++++++

.. code-block:: xml

    <py:for each="i in range(5)"><td>$i</td></py:for>

or 

.. code-block:: xml

    <td py:for="i in range(5)">$i</td>

results in the output

.. code-block:: xml

    <td>0</td><td>1</td><td>2</td><td>3</td><td>4</td>

``py:strip``
++++++++++++

Strips the *tag* if the expression is true; keeping the contents. Keeps the tag if the expression evaluates to false.

.. code-block:: xml

    <div py:strip="True">content</div>

results in rendered output

.. code-block:: xml

    content

``py:strip=""`` is equivalen to ``py:strip="True"``.

Warning: ``py:strip`` will evaluate the expression twice: once for the opening and once for the closing tag.

``py:def``
++++++++++

Declares a callable function with optional arguments. The function, when called, will return the rendered contents
of the ``py:def`` tag.

For example a function without argments (you can omit the empty parentheses ``()``):

.. code-block:: xml

    <!-- define a function -->
    <py:def function="copyright">(C) 2015 Tonnikala contributors</py:def>

    <!-- call the function -->
    $copyright()

With arguments:

.. code-block:: xml

    <button 
         py:def="button(caption, type='submit' cls='btn-default', id=None)"
         class="btn $btn_cls"
         type="$type"
         id="$id">$caption</button>

    $button('Cancel', id='cancel')
    $button('OK', cls='btn-primary', id='ok')
    $button('Reset', type='reset')

Will render to

.. code-block:: xml

    <button class="btn btn-default" type="submit" id="cancel">Cancel</button>
    <button class="btn btn-primary" type="submit" id="ok">OK</button>
    <button class="btn btn-default" type="reset">Reset</button>

The functions created by ``py:def`` form closures - that is they remember
the variable values from the context where they were created.

.. code-block:: xml

    <li py:def="li_element(content)">$content</li>

    <ul py:def="make_list(elements, format_item=li_element)">
        <py:for each="item in elements">$format_item(item)</py:for>
    </ul>

    <py:def function="make_color_list(elements, color='#ccc')">
        <li py:def="colorized_li_element(content)" style="color: $color">$content</li>
        $make_list(elements, format_item=colorized_li_element)
    </py:def>

    $make_list(plain)
    $make_color_list(good, color="#0F0")
    $make_color_list(bad, color="#F00")

might render to

.. code-block:: xml

    <ul>
        <li>Plain item 0</li>
        <li>Plain item 1</li>
        <li>Plain item 2</li>
    </ul>
    <ul>
        <li style="color: #0F0">Good item 0</li>
        <li style="color: #0F0">Good item 1</li>
        <li style="color: #0F0">Good item 2</li>
        <li style="color: #0F0">Good item 3</li>
    </ul>
    <ul>
        <li style="color: #F00">Bad item 0</li>
        <li style="color: #F00">Bad item 1</li>
        <li style="color: #F00">Bad item 2</li>
    </ul>
    

``py:with``
+++++++++++ 


``py:with`` declares one or more lexical variable bindings to be available within the element.
This is useful in eliminating repeated calculations in a declarative context


.. code-block:: xml

    <py:with vars="a = 5; b = 6"><span>$a * $b = ${a * b}</span></py:with>

or 

.. code-block:: xml

    <span py:with="a = 5; b = 6">$a * $b = ${a * b}</span>

results in the output

.. code-block:: xml

    <span>5 * 6 = 30</span>


Template inheritance
--------------------

base.tk
+++++++

.. code-block:: xml

    <html>
    <title><py:block name="title_block">I am $title</py:block></title>
    <py:def function="foo()">I can be overridden too!</py:def>
    <h1>${title_block()}</h1>
    ${foo()}
    </html>

child.tk
++++++++

.. code-block:: xml

    <py:extends href="base.tk">
    <py:block name="title_block">But I am $title instead</py:block>
    <py:def function="foo()">I have overridden the function in parent template</py:def>
    </py:extends>

Template imports
----------------

importable.tk
+++++++++++++

.. code-block:: xml

    <html>
    <py:def function="foo()">I am an importable function</py:def>
    </html>

importer.tk
+++++++++++

.. code-block:: xml

    <html>
    <py:import href="importable.tk" alias="imp" />
    ${imp.foo()}
    </html>

FileLoader
----------

To load templates from files, use the ``tonnikala.FileLoader`` class:

.. code-block:: python

    loader = FileLoader(paths=['/path/to/templates'])
    template = loader.load('child.tk')

A ``FileLoader`` currently implicitly caches **all** loaded templates in memory.

Template
--------

To render the template:

.. code-block:: python

    result = template.render(ctx)

You can specify a block, or no-argument def to render explicitly:

.. code-block:: python

    result = template.render(ctx, funcname='title_block')

Pyramid integration
-------------------

Include `'tonnikala.pyramid'` into your config to enable Tonnikala. When included, Tonnikala adds the following configuration directives:

``add_tonnikala_extensions(*extensions)``
    Registers Tonnikala renderer for these template extensions. By default Tonnikala is not registered as a renderer for any extension.
    For example: ``config.add_tonnikala_extensions('.html', '.tk')`` would enable Tonnikala renderer for templates with either of these extensions.

``add_tonnikala_search_paths(*paths)``
    Adds the given paths to the end of Tonnikala search paths that are searched for templates. These can be absolute paths, or
    ``package.module:directory/subdirectory``-style asset specs. By default no search path is set (though of course you can
    use an asset spec for template).

``set_tonnikala_reload(reload)``
    If ``True``, makes Tonnikala not cache templates. Default is ``False``.

``set_debug_templates(debug)``
    If ``True``, makes Tonnikala skip some optimizations that make debugging harder.

These 3 can also be controlled by ``tonnikala.extensions``, ``tonnikala.search_paths`` and ``tonnikala.reload`` respectively in the deployment settings (the ``.ini`` files). 
If ``tonnikala.reload`` is not set, Tonnikala shall follow the ``pyramid.reload_templates`` setting.

Status
======

Beta, working features are

* Structural elements ``py:if``, ``py:unless``, ``py:def``, ``py:for``, 
  ``py:replace``, ``py:content``
* Basic template inheritance: ``py:extends`` and ``py:block``; the child
  template also inherits top level function declarations from the parent
  template, and the child can override global functions that the parent
  defines and uses.
* Expression interpolation using ``$simple_identifier`` and ``${complex + python + "expression"}``
* Boolean attributes: ``<tag attr="${False}">``, ``<tag attr="$True">``
* Implicit escaping
* Disabling implicit escaping (``literal()``)
* C speedups for both Python 2 and Python 3
* Importing def blocks from another template: ``py:import``
* Basic I18N using gettext.
* Pyramid integration
* Javascript as the target language (using ``js:`` prefix)
* Overriding attributes, setting attrs from dictionary: ``py:attrs``
* Understandable exceptions and readable tracebacks on CPython
* Lexical variable assignments with ``py:with``

Upcoming features:

* Structural elements: ``py:switch``, ``py:case``; ``py:else`` for ``for``, ``if`` and ``switch``.
* Custom tags mapping to ``py:def``
* I18N with optional in-parse-tree localization (partially done)
* Pluggable frontend syntax engines (partially done)
* METAL-like macros
* Pluggable expression languages akin to Chameleon
* Even better template inheritance
* Better documentation

Contributors
------------

* Antti Haapala
* Ilja Everilä
* Pete Sevander
* Hiếu Nguyễn
