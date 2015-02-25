// FIXME: !!! hacked "AMD support" bound to fail !!!
function requirejs(name) {
    var m;
    global.define = function (_, f) { m = f(); };
    require(name);
    delete global.define;
    return m;
}

var tkr = requirejs('../runtime/javascript'),
    b = tkr.Buffer();

function assert(cond, msg) {
    if (!cond) {
        throw msg;
    }
    console.info('Ok.')
}

function assertStringEqual(s1, s2, msg) {
    assert(s1 === s2, msg || (s1 + ' !=== ' + s2));
}

b('asdf');
assertStringEqual(String(b), 'asdf');

b('foo');
assertStringEqual(String(b), 'asdffoo');

b.escape(('& is as dangerous as < or so'));
assertStringEqual(String(b), 'asdffoo&amp; is as dangerous as &lt; or so');

b('<div')
b.attr('baz', 'bar \' " & < >');
b.attr('nope', null);
b.attr('nope', undefined);
b.attr('nope', false);
b.attr('yehees', true);
b('>')
assertStringEqual(String(b), 'asdffoo&amp; is as dangerous as &lt; or so<div baz="bar &#39; &#34; &amp; &lt; &gt;" yehees="yehees">');

var o = {toString: function () { return 'kukkuu! ALASTON & & &'; }, html: function () { return this; }};
b.escape(o);
assertStringEqual(String(b), 'asdffoo&amp; is as dangerous as &lt; or so<div baz="bar &#39; &#34; &amp; &lt; &gt;" yehees="yehees">kukkuu! ALASTON & & &');
