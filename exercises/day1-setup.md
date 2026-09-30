# Day 1 setup: get the course project running (10 min)

Your course laptop already has VS Code, git, Python and GitHub Copilot installed. In this setup
you check that Copilot works, download the course project from GitHub, and start it once.

If you get stuck, note the step number and the exact error message, and ask a facilitator.

**What you need**
- The course laptop, connected to the internet
- The link to the course repository: **https://github.com/pjhj-ttc/agentic-coding-intro**
- Your GitHub login, *only if* the laptop isn't already signed in (Setup 1 tells you)

---

## Setup 1 · Check Copilot (2 min)

The laptop may already be signed in to GitHub Copilot. Test that first:

1. Open **VS Code**.
2. Open the chat: press `Ctrl+Alt+I`, or click the chat icon at the top of the window.
3. Type `Hello, are you working?` and press Enter.
4. At the bottom of the chat panel, open the **mode dropdown** and check that **Agent** is one of the options.

**Got an answer, and Agent is there?** You're signed in with a Copilot licence. Go straight to Setup 2.

**No answer, or asked to sign in?** Sign in yourself:

- Click the **person icon** (Accounts) in the bottom-left corner → **Sign in to use GitHub Copilot**
  (or *Sign in with GitHub*). Sign in in the browser and approve, then repeat steps 3 and 4.
- If it's signed in to an account **without** Copilot (you see a message about not having access
  or a subscription): click the person icon → the account name → **Sign Out**, then sign in with
  the account that has your Copilot licence.

⚠️ Still no answer, or **Agent** is missing from the dropdown? Ask a facilitator.

---

## Setup 2 · Download the course project (3 min)

1. In VS Code, open a terminal: menu **Terminal → New Terminal**. A panel opens at the bottom
   where you can type commands. Press Enter after each command.
2. Check that git knows your name (git puts it on every save point you make):

   ```powershell
   git config --global user.name
   ```

   If this prints nothing, set it (keep the quotes):

   ```powershell
   git config --global user.name "Your Name"
   git config --global user.email "you@example.com"
   ```

3. Create a course folder and download the project into it:

   ```powershell
   New-Item -ItemType Directory -Force $HOME\course | Out-Null
   cd $HOME\course
   git clone https://github.com/pjhj-ttc/agentic-coding-intro.git
   ```

   When it's done you have the folder `C:\Users\<your name>\course\agentic-coding-intro`.

4. Open the project folder in VS Code:

   ```powershell
   code -r .\agentic-coding-intro
   ```

   (Or use **File → Open Folder...** → `course\agentic-coding-intro` → **Select Folder**.)

---

## Setup 3 · Trust the project and run the setup script (3–5 min)

1. VS Code asks *"Do you trust the authors of the files in this folder?"* → click
   **Yes, I trust the authors**. This turns on the project's settings.
2. If VS Code suggests installing **recommended extensions**, click **Install**.
3. Open a new terminal: **Terminal → New Terminal**. The path should end in `agentic-coding-intro>`.
4. Run:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\setup.ps1
   ```

The script checks your tools, installs what the project needs, creates a database with sample tips
and runs the tests. You should see a list of green `[OK]` lines, ending with **All good!**

```
  [OK]   git version 2.47.0.windows.1
  [OK]   git knows who you are (Your Name)
  [OK]   Python 3.12 found: C:\Program Files\Python312\python.exe
  [OK]   Virtual environment ready: C:\Users\anna\course\agentic-coding-intro\.venv\Scripts\python.exe (Python 3.12.7)
  [OK]   Dependencies installed
  ...
All good! Start the app with:
```

If you see a red `[FAIL]` line, it tells you what is wrong. Fix it (see *Troubleshooting* below)
and run the script again. Running it more than once is safe.

If VS Code asks you to **select a Python interpreter**, choose the one that mentions `.venv`.

---

## Setup 4 · Check the app runs (2 min)

In the same terminal:

```powershell
.\.venv\Scripts\python -m flask --app app run --debug
```

Wait for the line `Running on http://127.0.0.1:5000`. Then hold `Ctrl` and click that link.
You should see a page titled **"Send us a confidential tip"**.

Stop the app: click in the terminal and press `Ctrl+C`.

---

## ✅ You're ready when

- [ ] Copilot Chat answered you, and **Agent** mode is available
- [ ] `setup.ps1` ended with **All good!**
- [ ] The app showed "Send us a confidential tip" in your browser

Continue with the [Day 1 exercise](day1-exercise.md).

---

## Troubleshooting

| Problem | What to do |
|---|---|
| `git clone` says *"Repository not found"* or asks you to sign in | The link is probably mistyped: copy it exactly from *What you need* above. Ask a facilitator if it still fails |
| *"running scripts is disabled on this system"* | Make sure you typed the whole command, including `powershell -ExecutionPolicy Bypass -File` |
| `[FAIL] git doesn't know your name yet` | Run the two `git config` commands from Setup 2, then run the script again |
| `[FAIL] pip install failed`, or errors mentioning *SSL*, *certificate* or *proxy* | The network may block Python downloads. Ask a facilitator |
| `[FAIL] Could not create the database` | Check the project is in `C:\Users\<your name>\course` (Setup 2), not on a network drive. Otherwise ask a facilitator |
| `[FAIL] Tests failed` | Ask a facilitator |
| The app says *"Address already in use"* | Something else uses port 5000. Add `--port 5001` to the command and open `http://127.0.0.1:5001` |
| The browser shows *"This site can't be reached"* | Check the app is still running in the terminal, and that the address is `127.0.0.1:5000` |
| Guides open as plain text | Press `Ctrl+Shift+V` for the formatted view, and check you clicked *Trust* in Setup 3 |
