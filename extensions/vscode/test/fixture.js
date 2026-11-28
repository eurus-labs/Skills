'use strict';
// A small catalog in the schema of catalog.json, for the tests. `node --test` may load this file as a test file;
// it holds no test, so it only exports.

function sample() {
  return {
    schemaVersion: 1,
    marketplace: { name: 'eurus-labs', version: '0.7.0', source: 'eurus-labs/Skills' },
    hosts: [{ id: 'copilot', label: 'Copilot CLI' }, { id: 'claude', label: 'Claude Code' }],
    featured: { plugin: 'planning', note: 'New in 0.6.0', text: 'From a requirement to epics.' },
    plugins: [
      {
        name: 'planning', version: '0.1.0', description: 'Turn a requirement into work.',
        skills: [
          { name: 'analyze-requirements', description: 'Analyze.', evals: { cases: 4, hosts: { claude: { cases: 4, score: 0.98, latest: '2026-11-26T07-06-53-161Z' } } } },
          { name: 'group-epics', description: 'Group.', evals: { cases: 2, hosts: { claude: { cases: 2, score: 0.5, latest: '2026-11-25T07-06-53-161Z' } } } }
        ],
        cases: [
          { name: 'analyze-requirements-fires', kind: 'fires', skills: ['analyze-requirements'], description: 'Fires.', latest: { claude: { stamp: '2026-11-26T07-06-53-161Z', score: 1, runs: 3, trusted: true } } },
          { name: 'analyze-requirements-quiet', kind: 'quiet', skills: ['analyze-requirements'], description: 'Quiet.', latest: { claude: { stamp: '2026-11-26T07-06-53-161Z', score: 0.5, runs: 3, trusted: false } } },
          { name: 'analyze-requirements-works', kind: 'behavior', skills: ['analyze-requirements'], description: 'Works.', latest: { claude: { stamp: '2026-11-26T07-06-53-161Z', score: null, runs: 3, trusted: false } } },
          { name: 'group-epics-fires', kind: 'fires', skills: ['group-epics'], description: 'Fires.', latest: {} }
        ],
        runs: [{ stamp: '2026-11-26T06-55-42-435Z', host: 'claude', score: 1, cases: 9 }, { stamp: '2026-11-26T06-58-55-832Z', host: 'claude', score: 0.69, cases: 4 }]
      },
      { name: 'docs', version: '1.9.0', description: 'Docs.', skills: [{ name: 'document-codebase', description: 'Doc.', evals: { cases: 7, hosts: {} } }], cases: [], runs: [] },
      { name: 'testing', version: '0.3.6', description: 'Tests.', skills: [], cases: [], runs: [] },
      { name: 'review', version: '0.3.0', description: 'Review.', skills: [], cases: [], runs: [] },
      { name: 'skill-authoring', version: '0.1.2', description: 'Authoring.', skills: [], cases: [], runs: [] }
    ]
  };
}

// {host: reading} as commands.readInstalled returns it.
function installed(claude, copilot) {
  const entry = (plugins) => ({ state: 'ready', marketplace: 'eurus-labs/Skills', plugins, error: null });
  return { claude: claude === undefined ? entry({}) : claude, copilot: copilot === undefined ? entry({}) : copilot };
}

module.exports = { sample, installed };
