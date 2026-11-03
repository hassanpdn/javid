"""The eco-lodge's assistant (دستیار اقامتگاه بوم‌گردی): a small place to stay (5 to 20 units) with a public website
on its own address, where guests book, pay by card transfer with a photo of the receipt, follow their booking in their
own panel and review their stay; and the host's panel behind the site's door, where units, prices, the calendar,
bookings, receipts, reviews and the website's words are managed.

info.py    the lodge being shown and the website's words (lodge.json)
store.py   its own SQLite database (lodge.db) and the photos folder (LODGE_DIR)
facts.py   every number and date: prices, free nights, what is waiting, the numbers, feedback due
demo.py    builds four months of stays and the next two around the day it is built, with planted situations
api.py     the host's panel (/lodge/...)
public.py  the public website's API (/lodge/public/...), with guests' own accounts
"""
