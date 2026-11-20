# First-time setup: running the AgentSentry dashboard

This guide is for someone who has never used Docker or a terminal. It takes
about 20 minutes the first time, most of it waiting for downloads. If you are
comfortable with the command line, use [BUILD.md](../../BUILD.md) instead.

You will type a few commands. Type them exactly as shown, one at a time, and
press **Enter** after each one.

---

## Part 1 — Install two programs (once per computer)

1. **Docker Desktop.** Download it from <https://www.docker.com/products/docker-desktop/>,
   run the installer and accept the defaults. Restart the computer if asked.
2. **Git.** Download it from <https://git-scm.com/downloads>, run the
   installer and accept every default.
3. **A free Docker account.** Open Docker Desktop. If it asks you to sign in,
   create a free account and sign in. Leave Docker Desktop open — it must be
   running whenever you use the lab.

## Part 2 — Open a terminal

- **Windows:** press the **Windows** key, type `PowerShell`, and press
  **Enter**. A window with a blinking cursor opens.
- **Mac:** press **Cmd + Space**, type `Terminal`, and press **Enter**.

Keep this window open for the rest of the guide.

## Part 3 — Download and start the lab (first time only)

Type each line and press **Enter**. Wait for each one to finish (the cursor
comes back) before typing the next.

**Windows (PowerShell):**

```powershell
docker login
git clone https://github.com/Nailo27/AgentSentry.git
cd AgentSentry
Copy-Item .env.example .env
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\make.ps1 build
.\make.ps1 up
```

**Mac (Terminal):**

```bash
docker login
git clone https://github.com/Nailo27/AgentSentry.git
cd AgentSentry
cp .env.example .env
make build
make up
```

What to expect:

- `docker login` asks for the Docker username and password from Part 1.
  The password does not appear as you type; that is normal.
- `Set-ExecutionPolicy` may ask a question. Type `Y` and press **Enter**.
- `build` takes several minutes and prints a lot of text. That is normal.
- `up` finishes with the line `Dashboard  http://localhost:8501`.

## Part 4 — Open the dashboard

Wait about 30 seconds after `up` finishes, then open a web browser and go to:

**<http://localhost:8501>**

You should see **AgentSentry** with a green **Agent connected** label. Follow
the numbered steps on the page: choose a test, keep **Rule-based baseline** as
the model, and press **Submit to target agent**. Hover over any small circled
**i** for an explanation of a term.

## Part 5 — Next time

Open Docker Desktop, open a terminal (Part 2), then type:

**Windows:**

```powershell
cd AgentSentry
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\make.ps1 up
```

**Mac:**

```bash
cd AgentSentry
make up
```

Then open <http://localhost:8501> again.

## Part 6 — When you are finished

**Windows:** `.\make.ps1 down`  **Mac:** `make down`

Your saved results are kept for next time.

---

## If something goes wrong

| What you see | What to do |
|---|---|
| `docker: command not found` or "is the docker daemon running?" | Docker Desktop is not open. Open it, wait until it says it is running, and try again. |
| `git: command not found` | Git is not installed, or the terminal was opened before installing it. Close the terminal, reopen it, and try again. |
| `build` stops with `unauthorized` or `toomanyrequests` | Run `docker login` again and sign in. |
| "running scripts is disabled on this system" | Run the `Set-ExecutionPolicy` line from Part 3, then try again. |
| `cd AgentSentry` says the path does not exist | The terminal opened in a different folder. Close it, reopen it, and try again. |
| Browser says the site can't be reached | Wait 30 seconds and refresh. If it still fails, run the `up` command again. |
| Dashboard shows a red **Agent not reachable** label | Run the `down` command, then the `up` command, wait 30 seconds and refresh. |

If none of these help, copy the last few lines of text in the terminal and send
them to the team.
