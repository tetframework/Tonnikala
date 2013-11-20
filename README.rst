=========
Tonnikala
=========
Tonnikala is the latest reincarnation among the Python templating languages that feed on Kid-inspired XML syntax.
It rejects the Kid and Genshi notions of tagstreams and trees, and follows in footsteps of Chameleon and Kajiki 
in making the template to compile into Python bytecode directly. The syntax is very close to that of Kajiki, but
the internals are very different: Tonnikala writes code as Abstract Syntax Trees and optimizes the resulting trees
extensively. In addition, there is an optional speed-up module (currently Python 3), that provides a specialized 
class used for output buffering.

Example
=======

::
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

    print(template.render(ctx)).join())

The `render()` returns a Buffer object that you can coerce into unicode by calling the `join()` method, 
or by implicit conversion (str() on python 3, unicode() on python 2).


Contributors
============

Antti Haapala
