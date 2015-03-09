process.env.NODE_PATH = __dirname + ':' + __dirname + '/tmp';
require('module').Module._initPaths();

// private
function getCaller() {
    var stack = getStack()

    // Remove superfluous function calls on stack
    stack.shift() // getCaller --> getStack
    stack.shift() // omfg --> getCaller

    // Return caller's caller
    return stack[1]
}

function getStack() {
    // Save original Error.prepareStackTrace
    var origPrepareStackTrace = Error.prepareStackTrace

    // Override with function that just returns `stack`
    Error.prepareStackTrace = function (_, stack) {
        return stack
    }

    // Create a new `Error`, which automatically gets `stack`
    var err = new Error()

    // Evaluate `err.stack`, which calls our new `Error.prepareStackTrace`
    var stack = err.stack

    // Restore original `Error.prepareStackTrace`
    Error.prepareStackTrace = origPrepareStackTrace

    // Remove superfluous function call on stack
    stack.shift() // getStack --> Error

    return stack
}

global.define = function(requires, func) {
    var actuals = requires.map(function(e) { return require('./' + e); });
    rv = func.apply(null, actuals);
    var caller = getCaller();
    var module = caller.receiver;
    module.exports = rv;
};

if (process.argv.length != 4) {
    process.stderr.write(process.argv[0] + ": expected 2 arguments: template and context");
    process.exit(2);
}

// original_require = require;
// global.require = function (module) {
//    return original_require('./' + module);
// };

tonnikala_runtime = require('./tonnikala/runtime')
tonnikala_runtime.window = global

template = process.argv[2];
context = JSON.parse(process.argv[3]);

rv = require('./' + template);
console.log(rv(context).render());
