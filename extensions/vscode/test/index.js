'use strict';
// `node --test extensions/vscode/test/` must work on Node 18 and on Node 22. Node 18 and 20 run every .js file in a
// directory they are given. Node 21 and later no longer do: they load the directory as a module, which is this
// file. So here, and only there, load every *.test.js. On Node 18 and 20 this file loads nothing, so no test runs twice.

const fs = require('fs');
const path = require('path');

const major = Number(process.versions.node.split('.')[0]);

if (major >= 21) {
  fs.readdirSync(__dirname)
    .filter((name) => name.endsWith('.test.js'))
    .sort()
    .forEach((name) => require(path.join(__dirname, name)));
}
