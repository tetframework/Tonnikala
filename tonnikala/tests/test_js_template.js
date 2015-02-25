// FIXME: !!! hacked "AMD support" bound to fail !!!
function requirejs(name) {
    var m;
    global.define = function (_, f) { m = f(); };
    require(name);
    delete global.define;
    return m;
}

var tkr = requirejs('../runtime/javascript');

function tmpl(__tonnikala__) {

    var __tonnikala__Buffer = __tonnikala__.Buffer

    return function (__tonnikala__context) {

        var __tonnikala__output__ = __tonnikala__Buffer(),

            cls = __tonnikala__context["cls"],

            foobar = __tonnikala__context["foobar"];

        __tonnikala__output__('<html>');

        __tonnikala__.foreach(foobar, function (i) {

            __tonnikala__output__.escape((foo));

            __tonnikala__output__('<a');

            __tonnikala__output__(' href="');

            __tonnikala__output__.escape((foo));

            __tonnikala__output__('bar&#34;');

            __tonnikala__output__('"');

            __tonnikala__output__.attr('class', (cls));

            __tonnikala__output__(' class="');

            __tonnikala__output__.escape((cls));

            __tonnikala__output__('"');

            __tonnikala__output__('></a>');

        });

        function foo(arg, arg2) {

            var __tonnikala__output__ = __tonnikala__Buffer();

            __tonnikala__output__('hello, ');

            __tonnikala__output__.escape((arg));

            return __tonnikala__output__;

        }

        __tonnikala__output__('</html>');

        return __tonnikala__output__;

    };

};

// Should not throw
console.log(String(tmpl(tkr)({cls: "asdf", foobar: ['a', 'b', 'c']})));
