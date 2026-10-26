"""The fabric wholesaler's assistant: a second assistant next to the school one, with its own business details,
database, logins and three Excel files (stock, sales, accounts) that it reads as its source of data.

business.py  the wholesaler this demo is for (name and people), like school.py for the school
store.py     its own SQLite database (fabric.db): users, sessions and everything read from the Excel files
excel.py     builds the three simulated workbooks, reads them into the database, appends new invoices
facts.py     every number the panels and the model use, computed by code
api.py       the /fabric/... endpoints
"""
