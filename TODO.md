REPO:
- Do we even need the 'workflows/' directory??
- Update the README.md
- Do we need PDUtil.spec?
- Do we even need rlrrschema.json??
- Clean up repository
- Manage workflows so that executable can be built from Github

CODE:
- Replace .bat with more compatible .sh (or even better, find a way to remove the .bat and the .spec)
- Should midicompanion go into PyRLRR?
- Redo pd_gui.py
- Reduce number of libraries we are using

DOCKERFILE:
- Setup to build, test, and run application

WORKFLOWS:
- Setup workflow to upload release build from Dockerfile
- Setup CodeQL Security Analysis