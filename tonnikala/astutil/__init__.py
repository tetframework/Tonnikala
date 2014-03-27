import ast

NoneValue = object()

mappednames = [
    False,
    True,
    NotImplemented,
    Ellipsis
]

try:
    basestring
except:
    basestring = (str, bytes)

numbers = (int, float)

def coerce(obj):
    if any(i is obj for i in mappednames):
        return Name(str(obj))

    if obj is NoneValue:
        return Name('None')

    if isinstance(obj, basestring):
        return Str(obj)

    if isinstance(obj, numbers):
        return Num(obj)

    if isinstance(obj, list):
        return List(obj)

    if isinstance(obj, dict):
        return Dict(obj)

    if isinstance(obj, tuple):
        return Tuple(obj)

    return obj


def coerce_list(obj):
    return [ coerce(i) for i in obj ]


def coerce_dict(obj, valuesonly=False):
    kcoerce = coerce
    if valuesonly:
        kcoerce = lambda x: x

    return { kcoerce(k): coerce(v) for (k, v) in obj.items() }


def maybe_ast(obj):
    if obj is None:
        return

    return obj._get_ast()


def _get_list_ast(obj):
    return [ i._get_ast() for i in obj ]


class AstNode(object):
    def _make_lvalue(self):
        raise TypeError("Cannot make an lvalue of %s (non-expression)" % self.__class__.__name__)


class Expression(AstNode):
    def __call__(self, *a, **kw):
        return Call(self, *a, **kw)

    def _assign(self, value):
        return Assign(self, value)

    def __getattr__(self, name):
        return Attribute(self, name)

    def _make_lvalue(self):
        raise TypeError("Cannot make an lvalue of %s" % self.__class__.__name__)


class Statement(AstNode):
    pass


def make_statement(node):
    if isinstance(node, Expression):
        return Expr(node)

    return node


class Expr(Statement):
    def __init__(self, value):
        self.value = coerce(value)

    def _get_ast(self):
        return ast.Expr(self.value._get_ast())


class Num(Expression):
    def __init__(self, n=None):
        self.n = n

    def _get_ast(self):
        return ast.Num(self.n)


class Str(Expression):
    def __init__(self, s=None):
        self.s = s

    def _get_ast(self):
        return ast.Str(s=self.s)


class Assign(Statement):
    def __init__(self, target, source):
        self.target = target._make_lvalue()
        self.source = coerce(source)

    def _get_ast(self):
        return ast.Assign(
            [ self.target._get_ast() ],
            self.source._get_ast()
        )


class Call(Expression):
    def __init__(self, func, *a, **kw):
        self.func = func

        self.a = None
        self.kw = None
        if '_kwargs' in kw:
            self.kw = coerce_dict(kw.pop('_kwargs'))
        if '_args' in kw:
            self.a = coerce_list(kw.pop('_args'))

        self.args = coerce_list(a)
        self.kwargs = coerce_dict(kw, valuesonly=True)

    def _get_ast(self):
        kwlist = []
        for k, v in self.kwargs.items():
            kwlist.append(ast.keyword(
                arg=k,
                value=v._get_ast()
            ))

        return ast.Call(
            func=self.func._get_ast(),
            args=_get_list_ast(self.args),
            keywords=kwlist,
            starargs=maybe_ast(self.a),
            kwargs=maybe_ast(self.a)
        )


ctx_type_to_factory = {
    'load':  ast.Load,
    'store': ast.Store
}


class Name(Expression):
    def __init__(self, id=None, ctx='load'):
        if not isinstance(id, str):
            id = id.decode('UTF-8')

        self.name = id
        self.ctx = ctx

    def _make_lvalue(self):
        return Name(id=self.name, ctx='store')

    def _get_ast(self):
        ctx = ctx_type_to_factory[self.ctx]()
        return ast.Name(self.name, ctx)


class Attribute(Expression):
    def __init__(self, value=None, attr=None, ctx='load'):
        self.value = coerce(value)
        self.attr = attr
        self.ctx = ctx

    def _make_lvalue(self):
        return Attribute(self.value, self.attr, 'store')

    def _get_ast(self):
        ctx = ctx_type_to_factory[self.ctx]()
        return ast.Attribute(self.value._get_ast(), self.attr, ctx)


class Dict(Expression):
    def __init__(self, value=None):
        value = value or {}
        keys = []
        values = []
        for k, v in value.items():
            keys.append(k)
            values.append(v)

        self.keys   = coerce_list(keys)
        self.values = coerce_list(values)

    def _get_ast(self):
        return ast.Dict(_get_list_ast(self.keys), _get_list_ast(self.values))


class Tuple(Expression):
    def __init__(self, value=None, ctx='load'):
        value = list(value) or []
        self.values = coerce_list(value)
        self.ctx = ctx

    def _get_ast(self):
        ctx = ctx_type_to_factory[self.ctx]()
        return ast.Tuple(_get_list_ast(self.values), ctx)

    def _make_lvalue(self):
        return Tuple([ i._make_lvalue() for i in self.values ], 'store')


class List(Expression):
    def __init__(self, value=None, ctx='load'):
        value = value or []
        self.values = coerce_list(value)
        self.ctx = ctx

    def _get_ast(self):
        ctx = ctx_type_to_factory[self.ctx]()
        return ast.List(_get_list_ast(self.values), ctx)

    def _make_lvalue(self):
        return List([ i._make_lvalue() for i in self.values ], 'store')


try:
    from collections.abc import MutableSequence
except ImportError:
    from collections import MutableSequence


class StatementList(MutableSequence):
    def __init__(self, initial=None):
        self.list = []
        if initial:
            self += initial

    def coerce(self, o):
        return make_statement(o)

    def __getitem__(self, i):
        return self.list[i]

    def __setitem__(self, i, v):
        self.list[i] = self.coerce(v)

    def __delitem__(self, i):
        del self.list[i]

    def __len__(self):
        return len(self.list)

    def insert(self, i, o):
        return self.list.insert(i, self.coerce(o))

    def __iadd__(self, value):
        if isinstance(value, AstNode):
            self.append(value)
        else:
            super(StatementList, self).__iadd__(value)

        return self


class For(Statement):
    def __init__(self, vars=None, iterable=None, body=[], orelse=[]):
        self.body = StatementList(body)
        self.orelse = StatementList(orelse)
        self.vars = vars
        self.iterable = coerce(iterable)

    @property
    def vars(self):
        return self._vars

    @vars.setter
    def vars(self, value):
        if value is not None:
            value = coerce(value)._make_lvalue()

        self._vars = value

    def _get_ast(self):
        return ast.For(
            self._vars._get_ast(),
            self.iterable._get_ast(),
            _get_list_ast(self.body),
            _get_list_ast(self.orelse)
        )


class If(Statement):
    def __init__(self, condition=None, body=[], orelse=[]):
        self.body = StatementList(coerce_list(body))
        self.orelse = StatementList(coerce_list(orelse))
        self.condition = coerce(condition)

    def _get_ast(self):
        return ast.If(
            self.condition._get_ast(),
            _get_list_ast(self.body),
            _get_list_ast(self.orelse)
        )


class Return(Statement):
    def __init__(self, expression=None):
        self.expression = coerce(expression)

    def _get_ast(self):
        return ast.Return(self.expression._get_ast())


if __name__ == '__main__':
    forri = For(Name('a'), [ 1, 2, 3 ])
    forri.body += Name('print')(Name('a'))

    iffi = If(True)
    iffi.body += forri

    tree = iffi._get_ast()
    print(ast.dump(tree))
    import astor
    print(astor.codegen.to_source(tree))
