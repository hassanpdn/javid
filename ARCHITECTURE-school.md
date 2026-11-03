# School assistant: architecture and the reasons behind it

The whole application is described in [ARCHITECTURE.md](ARCHITECTURE.md). This file is only the school, whose code
sits at the root of the project because it was the first assistant.

## In one minute

A non-profit elementary school: a manager, an office, a counselor, teachers, parents and students. The office drowns in
letters from the education office; the manager needs one picture of the day; the counselor needs to notice a child
before it is too late; parents want to know how their own child is doing. The demo is set up for any school from its
first screen (name, boys or girls, city, people).

## The demo story

1. Set up the demo for a school in four short steps.
2. The office: the letter agent reads the letters one by one (real percentage on the bar), sorts each, drafts the
   answer to a statistics request with numbers from the database, and sends decisions to the manager.
3. The manager: a morning summary, today's attendance, a teacher late three times (a warning letter drafted with every
   late day and its time), letters waiting for a decision.
4. The counselor: a child whose signals add up, with private notes that never leave the counselor's panel.
5. A parent: asks about their own child; the answer has only their child's facts, checked; asking about another child
   or a comparison is refused.
6. Anyone: asks the floating assistant about the school's regulations; the answer quotes the articles it used.

## The shape

```
 pages/ (ManagerPanel, StaffPanel, CounselorPanel, ParentPanel, ChatPage, SetupPage, LoginPage)
        │
        ▼
 app.py (login, /chat, setup)   manager.py   staff.py (letter agent)   counselor.py   parent.py   parent_chat.py
        │                                    │
        ▼                                    ▼
 students.py (per-student facts and signals)   stats.py (numbers for statistics letters)   checks.py   offline.py
        │
        ▼
 db.py → school.db (seed.py builds it)        common.py / ingest.py → vector store db/ (regulations by article)
```

| File | What it does |
|---|---|
| `school.py` | The school being shown and every name built from it. No name is ever written in code or prompts. |
| `db.py`, `seed.py` | Schema and helpers; the demo school with planted stories. |
| `staff.py` | The letter agent: sort, draft, refer; every step logged with its reason. |
| `manager.py` | The manager's overview, briefing, warnings, decisions. |
| `counselor.py`, `students.py` | Signals per student by simple, explainable rules; private notes stay here. |
| `parent.py`, `parent_chat.py` | The parent's panel and questions about their own child. |
| `app.py` `/chat`, `common.py`, `ingest.py` | Questions about the regulations: retrieval by article, filtered by role. |
| `checks.py`, `offline.py` | Checks on model text; the texts used when the AI is off or down. |

## The rules, in code

- **Signals** (`students.py`): unexcused absences in 14 days, falling assessments, health-form flags. Simple rules a
  counselor can read; the model never decides them.
- **Statistics replies**: the numbers come from `stats.py`; the model's draft must keep each grade's numbers in order
  (`checks.grade_lines_match`), else a template is used.
- **Warning letters**: every late date must appear with its own time (`checks.missing_dated_times`).
- **Parent answers**: only this child's facts (id from the login), no diagnosis, no comparison, no private notes
  (`checks.unsafe_for_parent`), every number checked.
- **Regulation answers**: the question is rewritten formally, the articles are searched with a role filter, the
  answer must cite the articles it used; with the AI off, the best article is quoted as it is.

## Why it is built this way

- **Privacy by construction**: parent flows never load counselor notes or health flags, so they cannot leak even if
  the model misbehaves (`tests/test_privacy.py`).
- **The agent logs every step and its reason**, so the office can see why a letter was sorted as it was.
- **Role switches**: parents and students can be turned off at once, making it an internal tool for staff only (the
  offline install, `PRODUCTION.md`).

## Questions you will be asked

- *"Can a parent see another child?"* No: the child's id comes from the parent's login, never from the question; a
  question about another child or a comparison is refused by code.
- *"Where do the regulation answers come from?"* From the regulations in `docs/`, cut by article, searched by meaning
  and filtered by who is asking; each answer names its articles.

## Tests

The school's behaviour is covered by `test_auth`, `test_privacy`, `test_model_output`, `test_offline`,
`test_workflow`, `test_school`, `test_features`, `test_validation`, `test_concurrency`, `test_dates`, `test_checks`,
`test_parent_chat` and `test_demo_stories`, plus browser tests for every role (`frontend/e2e`).
