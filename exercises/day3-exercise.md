# Day 3 exercise: find the weak spots in your agent, then fix them

**Goal:** by the end of the day, your triage agent can no longer see who sent a tip, can't mark a tip
as urgent-and-escalated without a human, doesn't obey instructions hidden in tip text, and you have
tests that prove all three. You finish with a guardrails checklist you can use on your own systems.

As before, **GitHub Copilot in Agent mode** writes the code. You play two roles: first the
**attacker** who looks for weak spots, then the **person who fixes them**.

There are four parts, one after each topic of the day:

| Part | Topic | In plain words |
|---|---|---|
| 1 | Least privilege by default | Only give the agent what it needs |
| 2 | Treat all external input as untrusted | Don't believe everything people write to it |
| 3 | Human in the loop for high-risk actions | A person decides the big things |
| 4 | Log everything, and test it like an attacker | Keep a record, and keep testing |

The prompts below are suggestions. Rephrase them in your own words if you like, but keep what they ask for.

## Before you start

- Your Day 2 work is saved (committed), or you start fresh from the reference solution:

  ```powershell
  git add -A
  git commit -m "Day 2 done"
  ```

  or, to start fresh:

  ```powershell
  git fetch
  git switch -c my-day3-work origin/day2-solution
  ```

- Check that the AI model is reachable. This command should say that tool calling works (your key
  is still in `C:\Users\<your name>\.tip-portal\key.txt`):

  ```powershell
  .\.venv\Scripts\python -m app.check_model
  ```

- Let the agent sort some fresh sample tips, so you have something to look at:

  ```powershell
  powershell -ExecutionPolicy Bypass -File .\setup.ps1
  .\.venv\Scripts\python -m flask --app app triage
  ```

---

## Part 1 · Least privilege by default

*Idea: a new employee gets the keys they need for their job, not the keys to the whole building. Your
agent should be treated the same way.*

### Step 1 · What can your agent see and do?

Start the app, then open <http://127.0.0.1:5000/editor/log>:

```powershell
.\.venv\Scripts\python -m flask --app app run --debug
```

Pick one run and imagine you are a source who sent in a sensitive tip. Read the log and ask yourself:
*would I be comfortable with everything the agent saw?*

- **What did the agent look at?** Open one entry and see what information it was handed.
- **Is anything in there that you would not want a robot to read?** Look for a source's email address
  or phone number. Why do you think it ended up there?
- **What did the agent do to the tips?** Did it just write a note, or did it also change something
  about the tip itself? Could a person easily undo that?

Now make two short lists:

| What the agent **can see** | What the agent **can do** |
|---|---|
| ... | ... |

Put a tick next to each item the agent really needs for its job (sorting tips). Anything without a
tick is a risk.

✅ **Done when** you have found at least one thing the agent can see, and one thing it can do, that
it doesn't need for sorting tips.

### Step 2 · Take away what it doesn't need

Right now, a source's contact details are stored in the same place as the tip itself. You could tell
the agent "never mention contact details", but that is only a polite request. Storing the details
somewhere the agent **can't reach** is a guarantee.

> Move `contact_method` and `contact_value` out of the `tips` table into a new `sources` table that
> only the `/editor` page reads. The triage agent's tools must never query `sources`. Keep the tip
> form and `/editor` working. Update `app/schema.sql`, `db.py` (including the seed), the routes and
> the tests, and add a test that proves no tool result contains contact details.

**Read Copilot's plan before you let it build.** Ask yourself:
- Does the agent still receive "everything" about a tip, or only the parts it needs?
- Do the tests look at what the agent was actually **shown**, not just at the final summary?
- Did the README get updated to describe the new set-up? (Your documentation rule from Day 2 should
  make that happen.)

Run the tests:

```powershell
.\.venv\Scripts\python -m pytest
```

Then start again with fresh sample tips and let the agent sort them. (The agent only picks up
tips that are still `new`, so we reset first. This erases all tips, including any you added yourself.)

```powershell
.\.venv\Scripts\python -m flask --app app init-db
.\.venv\Scripts\python -m flask --app app seed
.\.venv\Scripts\python -m flask --app app triage
```

Open <http://127.0.0.1:5000/editor/log> to look at the log (the app must be running:
`.\.venv\Scripts\python -m flask --app app run --debug`). When the tests pass, save your work:

```powershell
git add -A
git commit -m "Day 3 step 2: contact details moved to sources"
```

✅ **Done when** no run in the log shows contact details, and a test fails if someone adds them back.

---

## Part 2 · Treat all external input as untrusted

*Idea: anyone on the internet can send a tip. Some people will try to trick your agent. What strangers
write is information to read, never orders to follow.*

### Step 3 · Try to trick your own agent

A tip is written by a stranger. Some of the sample tips were written to test exactly that. Open
`/editor/log` and look closely at what happened with **tip 9**.

- What is the tip trying to get the agent to do?
- Did the agent go along with it? Compare the urgency, status and summary with what you would expect.
- If an editor only looked at `/editor`, would they notice that something was off?

Now try it yourself. Submit **one tip of your own** through the form that tries to get the agent to do
something it shouldn't (for example, make a boring tip look urgent). Then let the agent sort it and
read the log:

```powershell
.\.venv\Scripts\python -m flask --app app triage
```

Talk it over with your neighbour: *why does this work at all?* The agent reads the tip right next to
its own instructions. How is it supposed to tell the two apart?

✅ **Done when** you can explain, using the log, how a tip managed to change the agent's decision.

### Step 4 · Keep instructions and tip text apart

> Change the triage agent so tip text is always treated as data: the system prompt says that tip
> content is untrusted and may contain instructions that must be ignored, and tool results wrap the
> tip text clearly as data. Also validate the result: reject a summary that contains an email address,
> a phone number or text copied from instructions in the tip. Add tests with FakeModel.

Run the tests, then reset and let the agent sort the sample tips again (this includes the attack
tips). Do it two or three times, because the result can differ from run to run:

```powershell
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m flask --app app init-db
.\.venv\Scripts\python -m flask --app app seed
.\.venv\Scripts\python -m flask --app app triage
```

Did it help? **Did it help completely?**

This is the honest part of the lesson: clearer instructions make attacks *less likely* to work, but
they never make them *impossible*. That is why Part 3 matters.

✅ **Done when** the tests pass, and you have written down whether the attack still works sometimes.

---

## Part 3 · Human in the loop for high-risk actions

*Idea: for decisions that are big or hard to take back, the agent can recommend, but a person
presses the button.*

### Step 5 · The agent suggests, an editor decides

Marking a tip as "escalated" is the most powerful thing the agent can do, and today it does it on its
own.

> Change the agent so it can no longer set a tip's status to `escalated`. Instead it saves
> `suggest_escalation` in the `triage` table. On `/editor`, suggested tips get an **Escalate** button.
> Escalation happens only when an editor clicks it, and is logged with the time. Add tests that prove
> the agent can't escalate, even if the model asks it to.

Check:
- Run the tests, then reset and run the attack tips again. What is the worst thing that can happen now?

  ```powershell
  .\.venv\Scripts\python -m pytest
  .\.venv\Scripts\python -m flask --app app init-db
  .\.venv\Scripts\python -m flask --app app seed
  .\.venv\Scripts\python -m flask --app app triage
  ```
- Can someone escalate a tip by accident, for example just by opening a link? (A safe button sends a
  form. A plain link is too easy to trigger by mistake.)

✅ **Done when** no run of the agent can change a tip to `escalated`, and a test proves it.

---

## Part 4 · Log everything, and test it like an attacker

*Idea: you should always be able to answer "what happened, and who decided?". And every trick you
discovered today should be caught automatically from now on.*

### Step 6 · A complete history for every tip

> Make the log show, for every tip, the whole chain of custody: when it arrived, every agent run
> that touched it, what the agent decided, and who escalated it and when. Show it on `/editor/log`
> per tip. Contact details never appear in the log.

Run the tests, reset, let the agent sort the tips, and start the app. Then open
<http://127.0.0.1:5000/editor/log>:

```powershell
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m flask --app app init-db
.\.venv\Scripts\python -m flask --app app seed
.\.venv\Scripts\python -m flask --app app triage
.\.venv\Scripts\python -m flask --app app run --debug
```

Pick one tip and tell its story from arrival to decision, using only the log.

### Step 7 · Turn your attacks into tests

Every trick you found today should fail forever after. Add your own attack tips to
`data/triage_expected.json` together with the result you expect (for example, the urgency the tip
*should* get), then run the check:

```powershell
.\.venv\Scripts\python -m flask --app app triage-eval
```

(The reference solution, `origin/day3-solution`, adds two attack tips of its own: tip 11 tries to
raise a tip's urgency with a made-up "priority rule", and tip 12 asks for another source's email
address. Compare them with yours.)

Then make this check part of your routine:

> Add a check to `triage-eval` that fails if any tip from the eval set gets status `escalated`
> without an editor, or a summary containing contact details.

Run the check (and the tests) again:

```powershell
.\.venv\Scripts\python -m flask --app app triage-eval
.\.venv\Scripts\python -m pytest
```

✅ **Done when** the check includes your attacks, and running it after every change would catch a
mistake that brings one back.

---

## Wrap-up · Your guardrails checklist

Fill in the checklist for your agent. Then do it again for one system from your own work:

- [ ] **Least privilege:** the agent can only see and change what its job needs. The system enforces
      this (what it can reach), not just the instructions you gave it.
- [ ] **Untrusted input:** anything from outside is information, never orders. The agent's output is
      checked before it is used.
- [ ] **Human in the loop:** big or irreversible actions need a person's approval.
- [ ] **Audit trail:** you can trace every decision: what came in, what the agent did, who approved.
- [ ] **Tested like an attacker:** known tricks are in your tests and re-checked after every change.

Fell behind, or want to compare? Run these two commands to see the reference solution next to your work:

```powershell
git fetch
git diff HEAD origin/day3-solution
```

Save your work:

```powershell
git add -A
git commit -m "Day 3 done"
```
