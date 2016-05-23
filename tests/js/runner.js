process.env.NODE_PATH = __dirname + ':' + __dirname + '/tmp';
require('module').Module._initPaths();

function getCallingModule() {
    return getStack()[3];
}

function getStack() {
    var origPrepareStackTrace = Error.prepareStackTrace;
    var stack;
    Error.prepareStackTrace = function (_, s) {
        stack = s;
        return s;
    }
    var err = new Error();
    err.stack;
    Error.prepareStackTrace = origPrepareStackTrace;
    return stack;
}

global.define = function(requires, func) {
    var actuals = requires.map(function(e) { return require(e); });
    rv = func.apply(null, actuals);
    var caller = getCallingModule();
    var module = require.cache[caller.getFileName()];
    module.exports = rv;
};

if (process.argv.length != 4) {
    process.stderr.write(process.argv[0] + ": expected 2 arguments: template and context");
    process.exit(2);
}

tonnikala_runtime = require('tonnikala/runtime');
tonnikala_runtime.window = global;

template = process.argv[2];
context = JSON.parse(process.argv[3]);

rv = require(template);
console.log(rv(context).render());
