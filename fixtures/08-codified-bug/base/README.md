# tally

A tiny expense log for the command line. Entries are stored in `tally.json` in the current
directory, or in the file `TALLY_FILE` names.

```console
$ python3 -m tally add 12.50 food
added 12.50 food
$ python3 -m tally total
12.50
$ python3 -m tally total --category rent
0
$ python3 -m tally undo
removed 12.50 food
```

`undo` removes the most recent entry, so a typo can be taken back straight away.
