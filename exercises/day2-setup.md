# Day 2 setup: get the new files and connect to the model

Today your project gets new files: the two Day 2 exercises, the database tables for the triage
agent, and `app/llm.py`, which connects the agent to a language model. In this setup you download
them, rebuild the database, and check that the model answers.

If you get stuck, note the step number and the exact error message, and ask a facilitator.

**What you need**
- The **same laptop** as on Day 1, with the project in `C:\Users\<your name>\course\agentic-coding-intro`
- The model **key** from the facilitator

---

## Setup 1 · Save your Day 1 work

1. Open **VS Code** with the project folder (**File → Open Recent → agentic-coding-intro**).
2. Open a terminal: **Terminal → New Terminal**. The path should end in `agentic-coding-intro>`.
3. Save everything you did on Day 1 as a commit:

   ```powershell
   git add -A; git commit -m "Day 1 done"
   ```

   It's fine if this says *"nothing to commit"*: then your work is already saved.

4. Check which branch you are on:

   ```powershell
   git branch --show-current
   ```

   You should see your own branch, e.g. `my-work`. If it says `main`, ask a facilitator before
   you continue.

---

## Setup 2 · Download the Day 2 files

Download what's new on GitHub. This doesn't change any of your files yet:

```powershell
git fetch
```

Then choose **one** of these two:

**A. Continue with your own Day 1 work.** Choose this if your tip form and `/editor` page work.

```powershell
git merge origin/main --no-edit
```

**B. Start fresh from the reference solution.** Choose this if your Day 1 app doesn't work, or if
option A shows a *conflict*. Your Day 1 work stays safe on your own branch.

```powershell
git merge --abort                                    # only if option A showed a conflict
git switch -c my-day2-work origin/day1-solution
```

Check that the new files arrived. In the Explorer on the left, you should now see
`exercises/day2-exercise1.md`, `exercises/day2-exercise2.md` and `app/llm.py`.

---

## Setup 3 · Rebuild the database

The triage agent needs two new tables. Run the setup script again:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

It ends with **All good!**, as on Day 1. It also resets the database to the sample tips, so tips you
submitted yourself on Day 1 are gone. That's expected.

---

## Setup 4 · Connect to the model

On Day 2 you build a **triage agent**: a small program that reads tips and asks a language model
what they are about. GitHub Copilot is your *coding* agent; the triage agent is a separate program
with its own access to a model, in **Microsoft Foundry**.

The agent needs a **key**: a password for the model. You save it once, in a file in your own user
folder, **outside the project**. Run these two lines. The second one asks for the key: paste the key
from the facilitator and press Enter.

```powershell
New-Item -ItemType Directory -Force $HOME\.tip-portal | Out-Null
Read-Host "Paste the key" | Set-Content -NoNewline $HOME\.tip-portal\key.txt
```

The key is now in `C:\Users\<your name>\.tip-portal\key.txt`.

Then check that the model answers:

```powershell
.\.venv\Scripts\python -m app.check_model
```

You should see something like:

```
Model:      gpt-5-nano
Answered in 2.4 s, tokens used: 281
Tool call:  get_desk_list  (tool calling works)
```

> **Why not in the project's `.env`?** Remember Day 1 step 4a: Copilot read `.env` and put its
> contents in the chat. Copilot's file tools only look inside the project folder; to read a file
> outside it, Copilot has to ask you first. And this project tells VS Code to always ask before
> Copilot runs a command that reads a file, such as `Get-Content` or `cat`.
>
> So: **if Copilot ever asks to open or read `.tip-portal\key.txt`, say no.** It never needs the
> key itself. The key is only for your triage agent.

---

## ✅ You're ready when

- [ ] Your Day 1 work is committed, and you are on your own branch (`my-work` or `my-day2-work`)
- [ ] You can see `exercises/day2-exercise1.md` and `exercises/day2-exercise2.md`
- [ ] `setup.ps1` ended with **All good!**
- [ ] `python -m app.check_model` says **tool calling works**

Continue with [exercise 1: your AGENTS.md](day2-exercise1.md).

---

## Troubleshooting

| Problem | What to do |
|---|---|
| `git commit` says *"Please tell me who you are"* | Run the two `git config` commands from the Day 1 setup, then commit again |
| `git merge` says **CONFLICT** | Run `git merge --abort`, then use option B (start fresh). Your Day 1 work stays on your own branch |
| `git switch` says *"a branch named 'my-day2-work' already exists"* | You already did option B. Run `git switch my-day2-work` instead |
| `fatal: invalid reference: origin/day1-solution` | Run `git fetch` first, then try again |
| `[FAIL] No model key found` | The key file is missing. Run the two key lines from Setup 4 again |
| `The model service answered 401` | The key is wrong or has a typo. Run the `Read-Host` line again and paste it once more |
| `The model service answered 404` | Ask a facilitator |
| `Could not reach the model service` | The network may block the model service. Ask a facilitator |
| `did not answer in JSON` | Ask a facilitator |
| `Warning: the model did not call the tool` | Ask a facilitator |
