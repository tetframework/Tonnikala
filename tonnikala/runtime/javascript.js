define([], function () {
    'use strict';

    var map = Array.prototype.map;

    function Markup(s) {
        this.s = s;
    }
    Markup.prototype = {

        html: function () {
            return this;
        },

        toString: function () {
            return this.s;
        }

    };

    function Renderer(template) {
        this.template = template;
    }

    Renderer.prototype = {
        html: function () {
            return this.template().toString();
        },
        toString: function () {
            return this.template().toString();
        },
        appendTo: function () {
            var fragment = $(this.template().toString());
            return fragment.appendTo.apply(fragment, arguments);
        },
        prependTo: function () {
            var fragment = $(this.template().toString());
            return fragment.prependTo.apply(fragment, arguments);
        },
        insertAfter: function () {
            var fragment = $(this.template().toString());
            return fragment.insertAfter.apply(fragment, arguments);
        },
        insertBefore: function () {
            var fragment = $(this.template().toString());
            return fragment.insertBefore.apply(fragment, arguments);
        }
    };

    function doEscape(s) {
        if (s && s.html) {
            return s.html();
        }
        return new Markup(
            String(s).replace(
                /([&<>'"])/g,
                function (c) {
                    return {
                        '&': '&amp;',
                        '<': '&lt;',
                        '>': '&gt;',
                        "'": '&#39;',
                        '"': '&#34;'
                    }[c];
                }
            )
        );
    }

    function isKindOfBoolean(value) {
        return value == null || typeof(value) === 'boolean';
    }

    function Buffer() {
        this.buffer = [];
    };
    Buffer.prototype = {

        e: function (list) {
            this.buffer = this.buffer.concat(list);
        },

        a: function (obj) {
            this.buffer.push(obj);
        },

        doOutput: function () {
            var i, an = arguments.length, arg;

            for (i = 0; i < an; i++) {
                arg = arguments[i];
                if (arg && arg.buffer) {
                    this.e(arg.buffer);
                } else {
                    this.a(String(arg));
                }
            }
        },

        output: function () {
            this.doOutput.apply(this, arguments);
        },

        escape: function () {
            this.doOutput.apply(this, map.call(arguments, doEscape));
        },

        outputBooleanAttr: function (name, value) {
            if (isKindOfBoolean(value)) {
                if (value) {
                    // asserts that name is never user supplied directly
                    this.doOutput(' ' + name + '="' + name + '"');
                }
            } else {
                this.doOutput(' ' + name + '="' + doEscape(value) + '"');
            }
        },

        html: function () {
            return this;
        },

        join: function () {
            return this.buffer.join('');
        },

        toString: function () {
            return this.join();
        }

    };

    function outputAttrs(values) {
        var rv, i, vn, key, value;

        if (!values || !values.length) {
            return '';
        }

        rv = new Buffer();
        for (i = 0, vn = values.length; i < vn; i++) {
            name = values[i][0];
            value = values[i][1];
            rv.outputBooleanAttr(name, value);
        }

        return rv;
    }

    function foreach(list, fn) {
        list.forEach(fn);
    }

    function ctxbind(ctx, name) {
        if (name in ctx) {
            return ctx[name];
        }

        return window[name];
    }

    return {
        // A magical factory for creating a callable with attrs
        Buffer: function () {
            var buffer = new Buffer(),
                bo = buffer.output,
                rv = function () {
                    bo.apply(buffer, arguments);
                };
            rv.attr = buffer.outputBooleanAttr.bind(buffer);
            rv.html = buffer.html.bind(buffer);
            rv.escape = buffer.escape.bind(buffer);
            rv.toString = buffer.toString.bind(buffer);
            return rv;
        },

        outputAttrs: outputAttrs,

        escape: doEscape,

        foreach: foreach,

        renderer: Renderer,

        literal: function (val) { return new Markup(String(val)); },

        ctxbind: ctxbind
    };

});
