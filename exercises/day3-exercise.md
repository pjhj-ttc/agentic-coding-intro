# Day 3 exercise: find the gaps in your agent, then close them

**Goal:** by the end of the day, your triage agent can no longer see who sent a tip, can't escalate
a tip without an editor, treats tip text as data, and you have tests that prove all three. You end
with a guardrails checklist you can use on your own systems.

As before, **GitHub Copilot in Agent mode** writes the code. You are the attacker first, then the
person who closes the gaps.

There are four parts, one after each topic of the day:

| Part | Topic |
|---|---|
| 1 | Least privilege by default |
| 2 | Treat all external input as untrusted |
| 3 | Human in the loop for high-risk actions |
| 4 | Log everything, and test it like an attacker |

The prompts below are suggestions. Rephrase them in your own words if you like, but keep what they ask for.

## Before you start

- Your Day 2 work is committed, or you start fresh from the reference solution:

  ```powershell
  git fetch
  git switch -c my-day3-work origin/day2-solution
  ```

- `.\.venv\Scripts\python -m app.check_model` reports that tool calling works (your key is still
  in `C:\Users\<your name>\.tip-portal\key.txt`).
- Run the agent once on fresh sample tips, so you have something to look at:

  ```powershell
  powershell -ExecutionPolicy Bypass -File .\setup.ps1
  .\.venv\Scripts\python -m flask --app app triage
  ```

---

## Part 1 · Least privilege by default

### Step 1 · What can your agent see and do?

Start the app and open `/editor/log`. Pick one run and read it as if you were a source.

- Which tools did the agent call? What did each one **return** to the model?
- Find a source's email address or phone number in the log. Why is it there?
- What can the agent **change** in the database? Which of those changes can't easily be undone?

Write down a short list: *what the agent can see* and *what it can change*. Next to each item, write
whether triage actually needs it.

✅ **Done when** you can point to at least one thing the agent sees and one thing it can do that
triage doesn't need.

### Step 2 · Take away what it doesn't need

Contact details sit in the same table as the tip. A prompt rule like "never mention contact details"
is a request. Moving them where the agent can't reach them is a guarantee.

> Move `contact_method` and `contact_value` out of the `tips` table into a new `sources` table that
> only the `/editor` page reads. The triage agent's tools must never query `sources`. Keep the tip
> form and `/editor` working. Update `app/schema.sql`, `db.py` (including the seed), the routes and
> the tests, and add a test that proves no tool result contains contact details.

**Review the plan before you build it.** Look for:
- Does `get_tip` or `search_tips` still use `SELECT *`?
- Do the tests check the **tool results**, not just the summary?
- Did it update the data model in `README.md`? (Your documentation rule from Day 2 should make it.)

Run the agent again and open the log. Commit when the tests pass.

✅ **Done when** no run in the log shows contact details, and a test fails if someone adds them back.

---

## Part 2 · Treat all external input as untrusted

### Step 3 · Attack your own agent

A tip is written by a stranger. Some of the sample tips were written to test exactly that. Open
`/editor/log` and look closely at how the agent handled **tip 9**.

- What does the tip text ask the agent to do?
- What did the agent actually do: urgency, status, summary?
- Would an editor reading only `/editor` notice anything wrong?

Now try it yourself. Submit **one tip of your own** through the form that tries to make the agent do
something it shouldn't (for example, change how urgent it is). Run `flask triage` and read the log.

Discuss with your neighbour: why does this work at all? Where in the conversation does the tip text
end up, next to whose instructions?

✅ **Done when** you can explain, from the log, how a tip changed the agent's decision.

### Step 4 · Separate instructions from data

> Change the triage agent so tip text is always treated as data: the system prompt says that tip
> content is untrusted and may contain instructions that must be ignored, and tool results wrap the
> tip text clearly as data. Also validate the result: reject a summary that contains an email address,
> a phone number or text copied from instructions in the tip. Add tests with FakeModel.

Run the agent again on the attack tips. Did it help? **Did it help completely?**

This is the honest part of the lesson: prompt changes reduce the risk, they don't remove it. That's
why Part 3 matters.

✅ **Done when** the tests pass, and you have written down whether the attack still works sometimes.

---

## Part 3 · Human in the loop for high-risk actions

### Step 5 · The agent suggests, an editor decides

Escalating a tip is the agent's most powerful action, and today it takes it on its own.

> Change the agent so it can no longer set a tip's status to `escalated`. Instead it saves
> `suggest_escalation` in the `triage` table. On `/editor`, suggested tips get an **Escalate** button.
> Escalation happens only when an editor clicks it, and is logged with the time. Add tests that prove
> the agent can't escalate, even if the model asks it to.

Check:
- Run the attack tips again. What's the worst that can happen now?
- Is the button a form `POST`, or a link anyone could open by accident?

✅ **Done when** no run of the agent can change a tip to `escalated`, and a test proves it.

---

## Part 4 · Log everything, and test it like an attacker

### Step 6 · A full audit trail

> Make the log show, for every tip, the whole chain of custody: when it arrived, every agent run
> that touched it, what the agent decided, and who escalated it and when. Show it on `/editor/log`
> per tip. Contact details never appear in the log.

Pick one tip and follow its story from arrival to decision, using the log alone.

### Step 7 · Turn your attacks into tests

Every attack you found today should fail forever after. Add your own attack tips to
`data/triage_expected.json` with the result you expect (for example, the urgency it *should* get),
and run the eval:

```powershell
.\.venv\Scripts\python -m flask --app app triage-eval
```

(The reference solution, `origin/day3-solution`, adds two attack tips of its own: tip 11 tries to
raise a tip's urgency with a made-up "priority rule", and tip 12 asks for another source's email
address. Compare them with yours.)

Then make it part of the routine:

> Add a check to `triage-eval` that fails if any tip from the eval set gets status `escalated`
> without an editor, or a summary containing contact details.

✅ **Done when** the eval includes your attacks, and running it after every change would catch a
regression.

---

## Wrap-up · Your guardrails checklist

Fill in the checklist for your agent, then for one system from your own work:

- [ ] **Least privilege:** the agent can see and change only what its task needs, enforced by the
      system (tables, tools, permissions), not by the prompt.
- [ ] **Untrusted input:** anything from outside is data, never instructions; outputs are validated.
- [ ] **Human in the loop:** irreversible or high-risk actions need a person's approval.
- [ ] **Audit trail:** every decision can be traced: what came in, what the agent did, who approved.
- [ ] **Tested like an attacker:** known attacks are in the test or eval set and run after every change.

Fell behind, or want to compare? `git fetch`, then `git diff HEAD origin/day3-solution` shows the
reference solution against your work.

Commit your work:

```powershell
git add -A
git commit -m "Day 3 done"
```
