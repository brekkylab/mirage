# ========= Copyright 2026 @ Strukto.AI All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2026 @ Strukto.AI All Rights Reserved. =========

import base64
import datetime as dt
import io
import json
import random
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
OUT = HERE / "v1.json"
BLOBS = HERE / "blobs"

SEED = 1337
WINDOW_START = dt.date(2025, 11, 3)
WINDOW_END = dt.date(2026, 3, 16)
DAY_BASE_HOUR = 9
WORKDAY_SECONDS = 9 * 3600
REPLY_GAP_MIN = 30
REPLY_GAP_MAX = 300
SCALE = 0.21
P_THREAD = 0.12
P_REACT = 0.22

# Cast: (id, handle, real_name, role, departure_date_or_None). Handles are
# first names (capitalized). Departed users deactivate on their departure
# date; they emit no messages after it and are filtered from users.list.
CAST = [
    ("U7", "priya", "Priya Nair", "CEO", None),
    ("U8", "marcus", "Marcus Webb", "CTO", None),
    ("U1", "alice", "Alice Anderson", "Head of Product", None),
    ("U2", "bob", "Bob Brown", "Eng Lead", None),
    ("U3", "carol", "Carol Clark", "Design Lead", None),
    ("U4", "dave", "Dave Davis", "Backend Engineer", None),
    ("U11", "henry", "Henry Ho", "Senior ML Engineer", None),
    ("U13", "jack", "Jack Jones", "DevRel", None),
    ("U14", "kara", "Kara King", "Data Engineer", None),
    ("U16", "mia", "Mia Moore", "BizOps", None),
    ("U17", "noah", "Noah Nguyen", "Solutions Engineer", None),
    ("U6", "erin", "Erin Evans", "Growth Lead", dt.date(2025, 12, 19)),
    ("U9", "frank", "Frank Foster", "Account Executive", dt.date(2025, 12,
                                                                 19)),
    ("U10", "grace", "Grace Green", "Customer Success", dt.date(2026, 1, 16)),
    ("U12", "iris", "Iris Ito", "Product Manager", dt.date(2026, 1, 30)),
    ("U15", "liam", "Liam Lee", "Founding Engineer", dt.date(2026, 2, 13)),
]
BOT = ("U5", "buildbot", "Build Bot", True)

HANDLE2ID = {h: uid for uid, h, _, _, _ in CAST}
ID2HANDLE = {uid: h for uid, h, _, _, _ in CAST}
DEPARTURE = {uid: dep for uid, _, _, _, dep in CAST}
FIRST = {uid: h.capitalize() for uid, h, _, _, _ in CAST}
ALL_HUMANS = [h for _, h, _, _, _ in CAST]

# Channels: (id, name, private, created, archived_date_or_None,
# active_start, active_end). Always-on channels span the whole window; the
# new-product channels start at the pivot; product-reply is archived; sales
# goes silent after the layoff (hard stop so its 90-day window stays clean).
CHANNELS = [
    ("C1", "general", False, WINDOW_START, None, WINDOW_START, WINDOW_END),
    ("C2", "random", False, WINDOW_START, None, WINDOW_START, WINDOW_END),
    ("C3", "engineering", False, WINDOW_START, None, WINDOW_START, WINDOW_END),
    ("C4", "design", False, WINDOW_START, None, WINDOW_START, WINDOW_END),
    ("C5", "leadership", True, WINDOW_START, None, WINDOW_START, WINDOW_END),
    ("C6", "product-reply", False, WINDOW_START, dt.date(2026, 1,
                                                         12), WINDOW_START,
     dt.date(2026, 1, 12)),
    ("C7", "product-runtime", False, dt.date(2026, 1,
                                             8), None, dt.date(2026, 1,
                                                               8), WINDOW_END),
    ("C8", "eng-agents", False, dt.date(2026, 2,
                                        2), None, dt.date(2026, 2,
                                                          2), WINDOW_END),
    ("C9", "sales", False, WINDOW_START, None, WINDOW_START,
     dt.date(2025, 12, 19)),
    ("C10", "design-partners", False, dt.date(2026, 2, 9), None,
     dt.date(2026, 2, 9), WINDOW_END),
]

CH_PARTICIPANTS = {
    "general": ALL_HUMANS,
    "random": ALL_HUMANS,
    "engineering": ["bob", "dave", "liam", "kara", "henry", "marcus"],
    "design": ["carol", "alice", "jack", "noah"],
    "leadership": ["priya", "marcus", "alice", "mia"],
    "product-reply": ["iris", "alice", "dave", "bob", "grace", "carol"],
    "product-runtime": ["priya", "marcus", "henry", "alice", "jack", "noah"],
    "eng-agents": ["henry", "dave", "kara", "bob", "liam", "noah"],
    "sales": ["frank", "erin", "grace", "mia", "noah"],
    "design-partners": ["noah", "henry", "jack", "carol"],
}

CH_MEAN = {
    "general": 2.2,
    "random": 2.6,
    "engineering": 3.2,
    "design": 1.4,
    "leadership": 1.1,
    "product-reply": 1.7,
    "product-runtime": 2.6,
    "eng-agents": 2.2,
    "sales": 1.7,
    "design-partners": 1.7,
}

# DMs: (id, dir_user_handle, [participants], created, end_date_or_None, banter)
DMS = [
    ("D1", "marcus", ["priya", "marcus"], WINDOW_START, None, False),
    ("D2", "mia", ["priya", "mia"], WINDOW_START, None, False),
    ("D3", "erin", ["priya", "erin"], WINDOW_START, dt.date(2025, 12,
                                                            19), False),
    ("D4", "iris", ["alice", "iris"], WINDOW_START, dt.date(2026, 1,
                                                            30), False),
    ("D5", "bob", ["marcus", "bob"], WINDOW_START, None, False),
    ("D6", "liam", ["bob", "liam"], WINDOW_START, dt.date(2026, 2, 13), False),
    ("D7", "dave", ["bob", "dave"], WINDOW_START, None, True),
    ("D8", "jack", ["carol", "jack"], WINDOW_START, None, False),
    ("D9", "noah", ["henry", "noah"], WINDOW_START, None, False),
    ("D10", "kara", ["kara", "dave"], WINDOW_START, None, True),
]
DM_MEAN = 0.55

EMOJI = [
    "+1",
    "thumbsup",
    "eyes",
    "tada",
    "rocket",
    "fire",
    "heart",
    "pray",
    "raised_hands",
    "100",
    "white_check_mark",
    "thinking_face",
    "clap",
]

# Templated vocab pools. Phrase templates carry {tokens}; fill() draws a value
# per token so the same template renders many distinct lines (kills the
# verbatim repetition a small fixed bank produces). All values stay ASCII so
# the fixture text is byte-identical between the Python (json.dumps
# ensure_ascii=False) and TypeScript (JSON.stringify) render paths.
VOCAB: dict[str, list[str]] = {
    "comp": [
        "auth",
        "billing",
        "ingestion",
        "routing",
        "gateway",
        "connector",
        "sync",
        "indexer",
        "scheduler",
        "webhook",
        "cache",
        "queue",
        "search",
        "upload",
    ],
    "env": ["staging", "canary", "prod", "dev", "preview"],
    "svc": ["api", "worker", "gateway", "scheduler", "ingester", "router"],
    "branch": ["main", "release", "develop", "hotfix"],
    "feat":
    ["onboarding", "settings", "dashboard", "billing", "connector", "runtime"],
    "food": ["taco", "ramen", "poke", "pizza", "bbq"],
    "hr": ["10am", "1pm", "2pm", "3pm", "4pm"],
    "day": ["monday", "tuesday", "wednesday", "thursday", "friday"],
    "team": ["eng", "design", "sales", "product"],
    "topic": ["engagement", "planning", "offsite"],
    "cast": ["true crime", "tech", "history", "comedy"],
    "vertical": ["retail", "fintech", "health", "logistics", "media"],
    "lang": ["python", "typescript", "go", "java"],
    "biztopic": ["board", "investor", "hiring", "runway", "roadmap"],
    "metric": ["activation", "churn", "pipeline", "usage", "retention"],
    "doctype": ["draft", "deck", "memo", "spec", "proposal"],
    "when": ["later", "this afternoon", "tomorrow", "after lunch"],
}
NUMS = [("pr", 100, 999), ("dep", 2000, 2999), ("pct", 90, 99), ("k", 2, 40)]

# Thread replies come from this acknowledgment bank rather than the channel
# phrase pool, so a reply reads like an actual response to its parent.
REPLIES = [
    "on it",
    "nice, thanks for flagging",
    "lgtm",
    "i will review after standup",
    "good catch",
    "makes sense to me",
    "can you add a test for that",
    "approved, ship it",
    "let us pair on this",
    "agreed",
    "same here",
    "i will take a look this afternoon",
    "thanks for the heads up",
    "looking now",
]

CH_PHRASES: dict[str, list[str]] = {
    "general": [
        "all-hands today at {hr}, agenda in the doc",
        "welcome {n} to the team, say hi",
        "reminder: expense reports due {day}",
        "office is closed {day} for the holiday",
        "great work shipping this sprint everyone",
        "posting the weekly metrics update shortly",
        "kudos to {n} for the customer save",
        "lunch is catered today, come grab some",
        "quick reminder to fill out the {topic} survey",
        "town hall notes are up, please skim them",
        "we hit our uptime target this month, {pct} percent",
        "new hire starting {day} on the {team} side",
    ],
    "random": [
        "anyone up for lunch around {hr}",
        "this coffee machine is fighting me again",
        "{n} did you watch the game last night",
        "{day}, finally. any weekend plans",
        "found a great {food} place near the office",
        "who left their mug in the sink again",
        "recommend me a {cast} podcast for the commute",
        "it is way too cold in here today",
        "happy birthday {n}, cake in the kitchen",
        "the elevator is broken again, stairs it is",
        "new {food} spot opened downtown, who is in",
        "anyone have a charger i can borrow",
    ],
    "engineering": [
        "PR #{pr} is up for the {comp} refactor, can someone review",
        "CI is red on {branch}, digging in now",
        "{n} can you take a look at the flaky {comp} test",
        "deploying the {comp} hotfix to {env}",
        "p{pct} latency on {svc} dropped after the {comp} change",
        "merging the {comp} migration once tests pass",
        "found a race in the {comp} worker, patching it",
        "bumping the {svc} pool, memory was tight",
        "rolling back deploy {dep} on {env}, error spike",
        "added retries to the {comp} path",
        "{n} the {comp} schema change looks good to me",
        "profiling shows the hot path is {comp} serialization",
        "cut the release branch for sprint {k}",
        "the {comp} timeout needs a longer budget",
    ],
    "design": [
        "new mockups for the {feat} flow are up",
        "{n} can you review the empty states for {feat}",
        "updated the color tokens in figma",
        "the {feat} page needs a spacing pass",
        "shipping the new nav to design review",
        "iconography set is ready for handoff",
        "accessibility audit found {k} contrast issues",
        "prototype for the {feat} view is clickable now",
        "{n} thoughts on the new logo direction",
        "tightened the type scale, reads cleaner",
    ],
    "leadership": [
        "board update draft is in the shared drive",
        "we need to talk runway before the offsite",
        "{n} let us sync on the hiring plan",
        "the growth numbers flattened again this month",
        "customers keep asking why not just use the model",
        "we should revisit our defensibility story",
        "prepping talking points for the investor call",
        "net revenue retention slipped to {pct} percent",
        "aligning on the q1 plan by end of week",
        "the commoditization risk is real, let us discuss",
    ],
    "product-reply": [
        "reply draft quality dipped on long threads",
        "customer churn ticked up in the smb segment",
        "{n} the auto-reply confidence needs tuning",
        "shipping the tone control feature this week",
        "the support inbox integration is flaky again",
        "usage is soft, activation is the bottleneck",
        "a competitor just shipped this for free",
        "the model does most of this natively now",
        "triage accuracy is holding at {pct} percent",
        "renewal risk on {k} mid-market accounts",
    ],
    "product-runtime": [
        "runtime connector api draft is ready to review",
        "{n} the tool-permission layer needs a spec",
        "eval harness caught a regression in routing",
        "first design partner wants a {comp} connector",
        "the sandbox isolation model is coming together",
        "runtime docs outline is up for feedback",
        "agent trace viewer prototype looks promising",
        "we need a story for long-running tool calls",
        "quokka milestone {k} is basically done",
        "prepping the private beta build for {n}",
        "permissioned data access is the hard part",
    ],
    "eng-agents": [
        "connector sdk scaffolding is merged",
        "{n} can you own the tool-registry piece",
        "eval suite now runs on every PR",
        "added tracing spans around {comp} tool calls",
        "the sandbox needs a syscall allowlist",
        "routing model eval improved {k} points",
        "wired up the permission checks in the gateway",
        "flaky {comp} connector test, adding a retry budget",
        "benchmark harness is deterministic now",
        "cut the first internal runtime build",
    ],
    "sales": [
        "demo with the {vertical} prospect went well",
        "{n} can you send the follow-up deck",
        "pipeline review moved to {day}",
        "the enterprise deal slipped a quarter",
        "{k} new logos in the smb tier this week",
        "customer wants a security questionnaire",
        "renewal call scheduled for next {day}",
        "quota looks reachable if the mid-market closes",
        "prospect asked about the model roadmap",
        "sending over pricing for the annual plan",
    ],
    "design-partners": [
        "onboarding the first runtime design partner",
        "{n} can you set up the shared channel",
        "design partner wants weekly office hours",
        "feedback: they need a {lang} sdk first",
        "second partner signed the pilot agreement",
        "collecting the connector wishlist from partners",
        "partner demo is scheduled for next week",
        "the beta feedback form is ready to send",
        "{k} partners active in the pilot now",
        "partner asked for audit logs on tool calls",
    ],
}

DM_WORK = [
    "can you review my {comp} PR when you get a sec",
    "did you see the {metric} numbers from yesterday",
    "let us sync for {k} minutes after standup",
    "i pushed the {comp} fix, take a look",
    "what is our story for the {biztopic} question",
    "can you cover the {vertical} demo tomorrow",
    "the {comp} eval is green, ready to merge",
    "need your take on the {comp} design",
    "sending the {doctype} over now",
    "are we still on for the 1:1 {when}",
]
DM_BANTER = [
    "coffee run? i am dying over here",
    "did you catch the game last night",
    "that meeting could have been an email",
    "weekend plans or just recovering",
    "the new {food} place is legit, we should go",
    "i cannot believe it is only {day}",
    "nice work today, genuinely",
    "remind me to never skip lunch again",
    "you seeing this rain right now",
    "one more coffee and i am unstoppable",
]


def day_epoch(d: dt.date) -> int:
    return int(
        dt.datetime(d.year, d.month, d.day,
                    tzinfo=dt.timezone.utc).timestamp())


def daterange(start: dt.date, end: dt.date) -> list[dt.date]:
    days = []
    d = start
    while d <= end:
        days.append(d)
        d += dt.timedelta(days=1)
    return days


def in_window(dep: dt.date | None, d: dt.date) -> bool:
    return dep is None or d <= dep


@dataclass
class Msg:
    user: str
    text: str
    reactions: list[dict[str, Any]] = field(default_factory=list)
    thread_ts: str | None = None
    file: dict[str, Any] | None = None
    replies: list["Msg"] = field(default_factory=list)


@dataclass
class Generator:
    rng: random.Random
    frac: int = 0
    messages: list[dict[str, Any]] = field(default_factory=list)
    files: list[dict[str, Any]] = field(default_factory=list)
    forced: dict[tuple[str, str], list[Msg]] = field(default_factory=dict)

    def next_frac(self) -> str:
        self.frac += 1
        return f"{self.frac:06d}"

    def phase_mult(self, name: str, d: dt.date) -> float:
        m = 1.0
        if name == "leadership":
            if dt.date(2025, 11, 20) <= d <= dt.date(2025, 12, 22):
                m *= 2.3
            if dt.date(2026, 1, 5) <= d <= dt.date(2026, 1, 12):
                m *= 2.0
        if name == "product-reply":
            if dt.date(2025, 11, 20) <= d <= dt.date(2025, 12, 6):
                m *= 1.8
            if d >= dt.date(2026, 1, 1):
                m *= 0.5
        if name == "product-runtime":
            if d <= dt.date(2026, 1, 20):
                m *= 1.5
            if dt.date(2026, 3, 5) <= d <= dt.date(2026, 3, 14):
                m *= 1.6
        if name == "design-partners" and dt.date(2026, 3, 5) <= d <= dt.date(
                2026, 3, 14):
            m *= 1.5
        if name == "sales" and d <= dt.date(2025, 11, 20):
            m *= 1.3
        if name in ("general", "engineering") and d in (dt.date(
                2025, 12, 19), dt.date(2026, 1, 8), dt.date(2026, 2, 20)):
            m *= 1.5
        return m

    def draw_count(self, mean: float) -> int:
        base = int(mean)
        n = base + (1 if self.rng.random() < (mean - base) else 0)
        if self.rng.random() < 0.15:
            n += 1
        if self.rng.random() < 0.05:
            n += 2
        return min(n, 15)

    def pick_reactions(self, participants: list[str],
                       d: dt.date) -> list[dict[str, Any]]:
        if self.rng.random() >= P_REACT:
            return []
        pool = [
            h for h in participants if in_window(DEPARTURE[HANDLE2ID[h]], d)
        ]
        if not pool:
            return []
        out = []
        for _ in range(1 if self.rng.random() < 0.7 else 2):
            name = self.rng.choice(EMOJI)
            k = self.rng.randint(1, min(3, len(pool)))
            users = sorted(self.rng.sample(pool, k),
                           key=lambda h: HANDLE2ID[h])
            out.append({
                "name": name,
                "users": [HANDLE2ID[h] for h in users],
                "count": k,
            })
        return out

    def fill(self, text: str, others: list[str]) -> str:
        if "{n}" in text:
            mention = FIRST[HANDLE2ID[self.rng.choice(others)]] if others \
                else "team"
            text = text.replace("{n}", mention)
        for tok, pool in VOCAB.items():
            marker = "{" + tok + "}"
            while marker in text:
                text = text.replace(marker, self.rng.choice(pool), 1)
        for tok, lo, hi in NUMS:
            marker = "{" + tok + "}"
            while marker in text:
                text = text.replace(marker, str(self.rng.randint(lo, hi)), 1)
        return text

    def channel_line(self, name: str, author: str, participants: list[str],
                     d: dt.date) -> str:
        others = [
            h for h in participants
            if h != author and in_window(DEPARTURE[HANDLE2ID[h]], d)
        ]
        return self.fill(self.rng.choice(CH_PHRASES[name]), others)

    def emit_day(self, channel_id: str, name: str, participants: list[str],
                 d: dt.date, mean: float, allow_bot: bool) -> None:
        active = [
            h for h in participants if in_window(DEPARTURE[HANDLE2ID[h]], d)
        ]
        if not active:
            return
        plan: list[Msg] = list(self.forced.get((channel_id, d.isoformat()),
                                               []))
        weekday = 1.0 if d.weekday() < 5 else 0.3
        adj = mean * self.phase_mult(name, d) * weekday * SCALE
        for _ in range(self.draw_count(adj)):
            if allow_bot and self.rng.random() < 0.08:
                m = Msg(user=BOT[0],
                        text=f"deploy #{self.rng.randint(2000, 2999)} "
                        f"succeeded on {self.rng.choice(VOCAB['env'])}")
            else:
                author = self.rng.choice(active)
                m = Msg(user=HANDLE2ID[author],
                        text=self.channel_line(name, author, participants, d))
            m.reactions = self.pick_reactions(active, d)
            if self.rng.random() < P_THREAD and len(active) > 1:
                for _ in range(self.rng.randint(1, 3)):
                    r_author = self.rng.choice(active)
                    m.replies.append(
                        Msg(user=HANDLE2ID[r_author],
                            text=self.fill(self.rng.choice(REPLIES), [])))
            plan.append(m)
        self.flush_day(channel_id, d, plan)

    def emit_dm_day(self, dm_id: str, parts: list[str], d: dt.date,
                    banter: bool) -> None:
        active = [h for h in parts if in_window(DEPARTURE[HANDLE2ID[h]], d)]
        if len(active) < 2:
            return
        plan: list[Msg] = list(self.forced.get((dm_id, d.isoformat()), []))
        weekday = 1.0 if d.weekday() < 5 else 0.4
        for _ in range(self.draw_count(DM_MEAN * weekday * SCALE)):
            author = self.rng.choice(parts)
            bank = DM_BANTER if (banter and self.rng.random() < 0.6) \
                else DM_WORK
            plan.append(
                Msg(user=HANDLE2ID[author],
                    text=self.fill(self.rng.choice(bank), [])))
        self.flush_day(dm_id, d, plan)

    def append_row(self, channel_id: str, ts: str, m: Msg,
                   thread_ts: str | None) -> None:
        row: dict[str, Any] = {
            "channel": channel_id,
            "ts": ts,
            "user": m.user,
            "text": m.text,
        }
        if thread_ts is not None:
            row["thread_ts"] = thread_ts
        if m.reactions:
            row["reactions"] = m.reactions
        self.messages.append(row)
        if m.file is not None:
            rec = dict(m.file)
            rec["channel"] = channel_id
            rec["message_ts"] = ts
            self.files.append(rec)

    def flush_day(self, channel_id: str, d: dt.date, plan: list[Msg]) -> None:
        if not plan:
            return
        day0 = day_epoch(d) + DAY_BASE_HOUR * 3600
        # Each top-level message gets an independent time across the workday,
        # then the day is sorted chronologically; replies follow their parent
        # within a few minutes. A quiet day's lone message thus lands anywhere
        # in business hours, not pinned to 09:00.
        prims = sorted(((day0 + self.rng.randint(0, WORKDAY_SECONDS), i, m)
                        for i, m in enumerate(plan)),
                       key=lambda x: (x[0], x[1]))
        for start, _i, m in prims:
            parent_ts = f"{start}.{self.next_frac()}"
            self.append_row(channel_id, parent_ts, m, m.thread_ts)
            clock = start
            for r in m.replies:
                clock += self.rng.randint(REPLY_GAP_MIN, REPLY_GAP_MAX)
                self.append_row(channel_id, f"{clock}.{self.next_frac()}", r,
                                parent_ts)

    def _force(self, cid: str, date: dt.date, m: Msg) -> None:
        self.forced.setdefault((cid, date.isoformat()), []).append(m)

    def plant(self) -> None:
        add = self._force
        add(
            "C5", dt.date(2025, 11, 24),
            Msg(user=HANDLE2ID["priya"],
                text="the reply moat is basically gone after this "
                "week's model launches",
                reactions=[{
                    "name": "sob",
                    "users": ["U8"],
                    "count": 1
                }]))
        add(
            "C6", dt.date(2025, 11, 25),
            Msg(user=HANDLE2ID["iris"],
                text="are we sure the reply moat still holds, "
                "customers can do this in the box now"))
        add(
            "C5", dt.date(2025, 12, 15),
            Msg(user=HANDLE2ID["priya"],
                text="sharing the Q4 board deck ahead of the meeting",
                file=blob_file("F10", "board_deck_q4.pdf", "Q4 Board Deck",
                               "application/pdf", "pdf")))
        add(
            "C5", dt.date(2025, 12, 3),
            Msg(user=HANDLE2ID["mia"],
                text="november reply metrics attached, growth is soft",
                file=text_file("F1", "reply_metrics_nov.csv",
                               "November Reply Metrics", "text/csv", "csv",
                               CSV_REPLY_METRICS)))
        add(
            "C6", dt.date(2025, 12, 5),
            Msg(user=HANDLE2ID["iris"],
                text="churn analysis for the smb segment attached",
                file=text_file("F2", "churn_analysis.csv", "Churn Analysis",
                               "text/csv", "csv", CSV_CHURN)))
        add(
            "C5", dt.date(2025, 12, 12),
            Msg(user=HANDLE2ID["mia"],
                text="updated runway model, we have two options",
                file=text_file("F3", "runway_model.csv", "Runway Model",
                               "text/csv", "csv", CSV_RUNWAY)))
        add(
            "C3", dt.date(2025, 12, 9),
            Msg(user=HANDLE2ID["bob"],
                text="reply incident, capturing the log here",
                file=text_file("F9", "incident_2025-12-09.log",
                               "Reply Incident Log", "text/plain", "text",
                               LOG_INCIDENT)))
        add(
            "C3", dt.date(2025, 12, 9),
            Msg(user=BOT[0],
                text="deploy #2312 rolled back after error spike"))
        add(
            "C1", dt.date(2025, 12, 19),
            Msg(user=HANDLE2ID["priya"],
                text="today we made the hard decision to reduce our team, "
                "thank you erin and frank for everything",
                reactions=[{
                    "name": "pray",
                    "users": ["U8", "U1", "U2"],
                    "count": 3
                }, {
                    "name": "heart",
                    "users": ["U3"],
                    "count": 1
                }]))
        add(
            "C1", dt.date(2026, 1, 8),
            Msg(user=HANDLE2ID["priya"],
                text="we are pivoting to Kestrel Runtime, an agent "
                "infrastructure play, codename Quokka",
                file=None,
                reactions=[{
                    "name": "rocket",
                    "users": ["U8", "U11", "U13"],
                    "count": 3
                }]))
        add(
            "C7", dt.date(2026, 1, 8),
            Msg(user=HANDLE2ID["marcus"],
                text="kicking off project Quokka, the runtime for building "
                "agents over company tools"))
        add(
            "C5", dt.date(2026, 1, 7),
            Msg(user=HANDLE2ID["priya"],
                text="pivot rationale for the board attached",
                file=blob_file("F11", "pivot_rationale.pdf", "Pivot Rationale",
                               "application/pdf", "pdf")))
        add(
            "C5", dt.date(2026, 1, 6),
            Msg(user=HANDLE2ID["marcus"],
                text="pivot memo draft attached, please read before we decide",
                file=text_file("F4", "pivot_memo.md", "Pivot Memo",
                               "text/markdown", "markdown", MD_PIVOT_MEMO)))
        add(
            "C6", dt.date(2026, 1, 10),
            Msg(user=HANDLE2ID["alice"],
                text="reply growth postmortem attached",
                file=text_file("F5", "reply_growth_postmortem.md",
                               "Reply Growth Postmortem", "text/markdown",
                               "markdown", MD_POSTMORTEM)))
        add(
            "C1", dt.date(2026, 1, 9),
            Msg(user=HANDLE2ID["priya"],
                text="january all hands deck attached",
                file=blob_file(
                    "F12", "all_hands_2026-01.pptx", "January All Hands",
                    "application/vnd.openxmlformats-officedocument"
                    ".presentationml.presentation", "pptx")))
        add(
            "C7", dt.date(2026, 1, 15),
            Msg(user=HANDLE2ID["henry"],
                text="runtime spec draft attached, feedback welcome",
                file=text_file("F6", "runtime_spec.md", "Runtime Spec",
                               "text/markdown", "markdown", MD_RUNTIME_SPEC)))
        add(
            "C8", dt.date(2026, 2, 6),
            Msg(user=HANDLE2ID["henry"],
                text="model eval results for the routing change attached",
                file=text_file("F7", "model_eval_results.csv",
                               "Model Eval Results", "text/csv", "csv",
                               CSV_EVAL)))
        add(
            "C4", dt.date(2026, 2, 5),
            Msg(user=HANDLE2ID["carol"],
                text="new logo v2 attached for the runtime brand",
                file=blob_file("F15", "logo_v2.png", "Logo v2", "image/png",
                               "png")))
        add(
            "C5", dt.date(2026, 2, 18),
            Msg(user=HANDLE2ID["mia"],
                text="runway model spreadsheet after the bridge attached",
                file=blob_file(
                    "F14", "runway_model.xlsx", "Runway Model",
                    "application/vnd.openxmlformats-officedocument"
                    ".spreadsheetml.sheet", "xlsx")))
        add(
            "C10", dt.date(2026, 2, 12),
            Msg(user=HANDLE2ID["noah"],
                text="design partner pipeline attached, three active",
                file=text_file("F8", "design_partner_pipeline.csv",
                               "Design Partner Pipeline", "text/csv", "csv",
                               CSV_PARTNERS)))
        add(
            "C1", dt.date(2026, 2, 20),
            Msg(user=HANDLE2ID["priya"],
                text="we closed a bridge round to fund the runtime pivot",
                reactions=[{
                    "name": "tada",
                    "users": ["U8", "U1", "U11", "U13"],
                    "count": 4
                }]))
        add(
            "C7", dt.date(2026, 3, 11),
            Msg(user=HANDLE2ID["marcus"],
                text="Kestrel Runtime private beta is live for "
                "design partners",
                file=blob_file(
                    "F13", "runtime_launch.pptx", "Runtime Launch",
                    "application/vnd.openxmlformats-officedocument"
                    ".presentationml.presentation", "pptx"),
                reactions=[{
                    "name": "rocket",
                    "users": ["U11", "U17", "U13"],
                    "count": 3
                }]))
        add(
            "C10", dt.date(2026, 3, 11),
            Msg(user=HANDLE2ID["noah"],
                text="every design partner has runtime beta access now"))
        add(
            "D4", dt.date(2026, 1, 30),
            Msg(user=HANDLE2ID["iris"],
                text="i cannot get behind the pivot, i am going to resign"))
        add(
            "D4", dt.date(2026, 1, 30),
            Msg(user=HANDLE2ID["alice"],
                text="i understand, thank you for building reply with us"))
        add(
            "D6", dt.date(2026, 2, 13),
            Msg(user=HANDLE2ID["liam"],
                text="i am burned out, i need to step away from the team"))
        add(
            "D6", dt.date(2026, 2, 13),
            Msg(user=HANDLE2ID["bob"],
                text="take care of yourself, we will figure out the coverage"))
        add(
            "D1", dt.date(2026, 1, 6),
            Msg(user=HANDLE2ID["priya"],
                text="Quokka is the right bet, let us commit to the runtime"))


def text_file(fid: str, name: str, title: str, mimetype: str, filetype: str,
              content: str) -> dict[str, Any]:
    return {
        "id": fid,
        "name": name,
        "title": title,
        "mimetype": mimetype,
        "filetype": filetype,
        "content": content,
    }


def blob_file(fid: str, name: str, title: str, mimetype: str,
              filetype: str) -> dict[str, Any]:
    return {
        "id": fid,
        "name": name,
        "title": title,
        "mimetype": mimetype,
        "filetype": filetype,
        "content_path": f"blobs/{name}",
    }


CSV_REPLY_METRICS = ("month,active_accounts,replies_sent,activation_rate\n"
                     "2025-09,412,18240,0.31\n"
                     "2025-10,428,18990,0.30\n"
                     "2025-11,431,18110,0.28\n")
CSV_CHURN = ("segment,accounts,churned,churn_rate\n"
             "smb,240,29,0.121\n"
             "mid_market,84,6,0.071\n"
             "enterprise,19,1,0.053\n")
CSV_RUNWAY = ("scenario,monthly_burn,cash_on_hand,runway_months\n"
              "status_quo,410000,3900000,9.5\n"
              "pivot_lean,320000,3900000,12.2\n")
CSV_EVAL = ("suite,cases,passed,accuracy\n"
            "routing,500,472,0.944\n"
            "tool_selection,500,461,0.922\n"
            "permission,300,300,1.000\n")
CSV_PARTNERS = ("partner,stage,connector_request,active\n"
                "northwind,pilot,slack,true\n"
                "acme_data,pilot,postgres,true\n"
                "helio,evaluating,github,false\n")
MD_PIVOT_MEMO = (
    "# Pivot Memo: Reply to Runtime\n\n"
    "## Why\n\n"
    "The reply moat is gone. Foundation models draft email natively and for\n"
    "near zero marginal cost. Our vertical wrapper is being commoditized.\n\n"
    "## Proposal\n\n"
    "Pivot to Kestrel Runtime (codename Quokka): a horizontal runtime for\n"
    "building AI agents over a company's own tools and data.\n")
MD_POSTMORTEM = (
    "# Kestrel Reply Growth Postmortem\n\n"
    "Activation stalled at 28 percent. Churn concentrated in SMB. The core\n"
    "job to be done became a native model feature during 2025.\n")
MD_RUNTIME_SPEC = (
    "# Kestrel Runtime Spec (Quokka)\n\n"
    "## Components\n\n"
    "- Connectors: mount external tools and data\n"
    "- Tool layer: permissioned, audited tool calls\n"
    "- Evals: deterministic regression suite for agent behavior\n")
LOG_INCIDENT = (
    "2025-12-09T14:02:11Z ERROR reply-worker queue backlog growing\n"
    "2025-12-09T14:03:40Z ERROR model timeout rate 0.34\n"
    "2025-12-09T14:07:05Z WARN rolling back deploy 2312\n"
    "2025-12-09T14:12:22Z INFO error rate recovered, backlog draining\n")


def make_pdf(title_lines: list[str]) -> bytes:
    ops = []
    y = 720
    for ln in title_lines:
        safe = ln.replace("\\", "").replace("(", "").replace(")", "")
        ops.append(f"BT /F1 14 Tf 72 {y} Td ({safe}) Tj ET")
        y -= 22
    stream = "\n".join(ops).encode("latin-1")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref_pos = len(out)
    n = len(objs) + 1
    out += f"xref\n0 {n}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {n} /Root 1 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF\n").encode()
    return bytes(out)


def make_ooxml(parts: list[tuple[str, str]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
        for arcname, content in parts:
            zi = zipfile.ZipInfo(arcname, date_time=(1980, 1, 1, 0, 0, 0))
            zi.create_system = 3
            zi.compress_type = zipfile.ZIP_STORED
            zf.writestr(zi, content)
    return buf.getvalue()


def make_xlsx(sheet_rows: list[list[str]]) -> bytes:
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/'
          'content-types">'
          '<Default Extension="rels" ContentType="application/vnd.'
          'openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/xl/workbook.xml" ContentType="application/'
          'vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
          '<Override PartName="/xl/worksheets/sheet1.xml" '
          'ContentType="application/vnd.openxmlformats-officedocument.'
          'spreadsheetml.worksheet+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/'
            'package/2006/relationships"><Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
            'relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>')
    wb = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<workbook xmlns="http://schemas.openxmlformats.org/'
          'spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.'
          'org/officeDocument/2006/relationships"><sheets>'
          '<sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>')
    wbrels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<Relationships xmlns="http://schemas.openxmlformats.org/'
              'package/2006/relationships"><Relationship Id="rId1" '
              'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
              'relationships/worksheet" Target="worksheets/sheet1.xml"/>'
              '</Relationships>')
    rows_xml = []
    for ri, row in enumerate(sheet_rows, start=1):
        cells = "".join(f'<c r="A{ri}" t="inlineStr"><is><t>{v}</t></is></c>'
                        for v in row)
        rows_xml.append(f'<row r="{ri}">{cells}</row>')
    sheet = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<worksheet xmlns="http://schemas.openxmlformats.org/'
             'spreadsheetml/2006/main"><sheetData>'
             f'{"".join(rows_xml)}</sheetData></worksheet>')
    return make_ooxml([
        ("[Content_Types].xml", ct),
        ("_rels/.rels", rels),
        ("xl/workbook.xml", wb),
        ("xl/_rels/workbook.xml.rels", wbrels),
        ("xl/worksheets/sheet1.xml", sheet),
    ])


def make_pptx(title: str, bullets: list[str]) -> bytes:
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/'
          'content-types">'
          '<Default Extension="rels" ContentType="application/vnd.'
          'openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/ppt/presentation.xml" ContentType='
          '"application/vnd.openxmlformats-officedocument.presentationml.'
          'presentation.main+xml"/>'
          '<Override PartName="/ppt/slides/slide1.xml" ContentType='
          '"application/vnd.openxmlformats-officedocument.presentationml.'
          'slide+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/'
            'package/2006/relationships"><Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
            'relationships/officeDocument" Target="ppt/presentation.xml"/>'
            '</Relationships>')
    pres = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:presentation xmlns:p="http://schemas.openxmlformats.org/'
            'presentationml/2006/main" xmlns:r="http://schemas.'
            'openxmlformats.org/officeDocument/2006/relationships">'
            '<p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst>'
            '</p:presentation>')
    presrels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/'
                'package/2006/relationships"><Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/'
                '2006/relationships/slide" Target="slides/slide1.xml"/>'
                '</Relationships>')
    body = "".join(f"<p>{title}</p>" for title in [title] + bullets)
    slide = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<p:sld xmlns:p="http://schemas.openxmlformats.org/'
             'presentationml/2006/main"><p:cSld><p:spTree>'
             f'<notes>{body}</notes>'
             '</p:spTree></p:cSld></p:sld>')
    sliderels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Relationships xmlns="http://schemas.openxmlformats.org/'
                 'package/2006/relationships"></Relationships>')
    return make_ooxml([
        ("[Content_Types].xml", ct),
        ("_rels/.rels", rels),
        ("ppt/presentation.xml", pres),
        ("ppt/_rels/presentation.xml.rels", presrels),
        ("ppt/slides/slide1.xml", slide),
        ("ppt/slides/_rels/slide1.xml.rels", sliderels),
    ])


PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNkYPhf"
    "DwAChwGA60e6kgAAAABJRU5ErkJggg==")


def write_blobs() -> None:
    BLOBS.mkdir(exist_ok=True)
    (BLOBS / "board_deck_q4.pdf").write_bytes(
        make_pdf([
            "Kestrel Q4 Board Deck", "Reply metrics and growth",
            "Risk: reply moat commoditization", "Runway and options"
        ]))
    (BLOBS / "pivot_rationale.pdf").write_bytes(
        make_pdf([
            "Kestrel Pivot Rationale", "From Reply to Runtime",
            "Codename Quokka", "Agent infrastructure thesis"
        ]))
    (BLOBS / "all_hands_2026-01.pptx").write_bytes(
        make_pptx("January All Hands",
                  ["The pivot to Runtime", "What changes", "Q1 goals"]))
    (BLOBS / "runtime_launch.pptx").write_bytes(
        make_pptx("Kestrel Runtime Launch",
                  ["Private beta", "Design partners", "Roadmap"]))
    (BLOBS / "runway_model.xlsx").write_bytes(
        make_xlsx([["scenario", "burn", "runway_months"],
                   ["post_bridge", "300000", "16.0"],
                   ["aggressive", "380000", "12.6"]]))
    (BLOBS / "logo_v2.png").write_bytes(PNG_1PX)


def assert_anchors(gen: Generator) -> None:
    # A planted anchor is silently lost if its date falls outside the
    # channel/DM's active range (emit_day only reads self.forced for days it
    # iterates). Fail loudly instead so a channel/departure-date edit can never
    # quietly drop a story beat and its battery case.
    present = {(m["channel"], m["text"]) for m in gen.messages}
    for (cid, _date), plan in gen.forced.items():
        for m in plan:
            if (cid, m.text) not in present:
                raise SystemExit(
                    f"planted anchor dropped from {cid}: {m.text[:60]!r}")
    planted_files = {
        m.file["id"]
        for plan in gen.forced.values()
        for m in plan if m.file is not None
    }
    missing = planted_files - {f["id"] for f in gen.files}
    if missing:
        raise SystemExit(f"planted files dropped: {sorted(missing)}")


def build_fixture() -> dict[str, Any]:
    gen = Generator(rng=random.Random(SEED))
    gen.plant()
    ch_by_id = {c[0]: c for c in CHANNELS}
    for d in daterange(WINDOW_START, WINDOW_END):
        for cid, name, _priv, _created, _arch, astart, aend in CHANNELS:
            if not (astart <= d <= aend):
                continue
            gen.emit_day(cid,
                         name,
                         CH_PARTICIPANTS[name],
                         d,
                         CH_MEAN[name],
                         allow_bot=name in ("engineering", "product-reply"))
        for did, _u, parts, cstart, cend, banter in DMS:
            end = cend or WINDOW_END
            if cstart <= d <= end:
                gen.emit_dm_day(did, parts, d, banter)
    assert_anchors(gen)
    users = [{
        "id": uid,
        "name": h,
        "real_name": rn,
        "email": f"{h}@kestrel.example.com",
    } for uid, h, rn, _role, _dep in CAST]
    for u in users:
        if DEPARTURE[u["id"]] is not None:
            u["deleted"] = True
    users.append({
        "id": BOT[0],
        "name": BOT[1],
        "real_name": BOT[2],
        "email": "buildbot@kestrel.example.com",
        "is_bot": True,
    })
    channels = []
    for cid, name, priv, created, arch, _astart, _aend in CHANNELS:
        entry: dict[str, Any] = {
            "id": cid,
            "name": name,
            "kind": "channel",
            "created": day_epoch(created),
        }
        if priv:
            entry["is_private"] = True
        if arch is not None:
            entry["is_archived"] = True
        channels.append(entry)
    dms = [{
        "id": did,
        "user": HANDLE2ID[u],
        "kind": "im",
        "created": day_epoch(cstart),
    } for did, u, _parts, cstart, _cend, _banter in DMS]
    _ = ch_by_id
    return {
        "users": users,
        "channels": channels,
        "dms": dms,
        "messages": gen.messages,
        "files": gen.files,
    }


def main() -> None:
    write_blobs()
    data = build_fixture()
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    distinct = len({m["text"] for m in data["messages"]})
    print(f"messages={len(data['messages'])} distinct_text={distinct} "
          f"files={len(data['files'])} users={len(data['users'])} "
          f"channels={len(data['channels'])} dms={len(data['dms'])}")


if __name__ == "__main__":
    main()
