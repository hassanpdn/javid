"""The law office's assistant (دستیار دفتر وکالت): a fifth assistant beside the others, with its own office details,
database and logins.

office.py  the office this demo is for (name, the lawyer, the associate, the secretary)
store.py   its own SQLite database (law.db): users, sessions, clients, cases, notices and their deadlines, the log
demo.py    builds an office's open cases around today, with planted situations to find
facts.py   every date and number: deadlines with official holidays, today's work, the owner's checks
read.py    a notice (ابلاغیه) from pasted text: case number, branch, kind, dates; every value checked against the text
api.py     the /law/... endpoints
"""
