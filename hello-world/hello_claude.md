# Hello, Claude Code

A 5-minute tour of the tool you'll be living in all weekend. By the
end you'll have:

- Asked Claude a question and seen it edit a file
- Tried a **slash command** (`/hackathon-aws`)
- Switched into **auto-accept-edits mode** and **plan mode**
- Used **memory** so Claude remembers you next session

No prior Claude Code experience needed. If you've never opened a
terminal, that's fine too — you'll mostly type into the Claude prompt.

---

## 0. Open this repo in Claude Code

Make sure you've installed Claude Code: <https://www.claude.com/product/claude-code>

Then, in this folder:

```bash
claude
```

(Or, in VS Code / a JetBrains IDE: open this folder, then open the
Claude Code panel.)

You should see a prompt at the bottom of the window. That's where you
type. Everything above is Claude's output and tool activity.

---

## 1. Just ask

Type this and hit enter:

```text
Read hello-world/profile.md and tell me what's in it.
```

Claude will tell you the file doesn't exist yet. **Good** — that's
exercise 2.

---

## 2. Let Claude write a file for you

```text
Create hello-world/profile.md. Fill it in with these placeholders for
me to edit later: my name, my background (wet-lab / dry-lab / mixed),
what I want to learn this weekend, and one project I'm excited about.
```

Claude will propose a `Write` and ask for permission. Hit **`y`** (or
click **Allow**) to approve.

Now open `hello-world/profile.md` in your editor and fill it in. This
is the first piece of *personal* context in your repo.

---

## 3. Tell Claude about yourself (and let it remember)

Back in the Claude prompt:

```text
Read hello-world/profile.md and save what's relevant about me to
memory so you remember it next time.
```

Claude will write a small memory file under `memory/` describing you.
Next session, it'll use that context to tailor explanations to your
background. (Try opening a fresh Claude session later and asking
"what do you remember about me?" — you should see it recall the
profile.)

---

## 4. Try a slash command

Slash commands inject heavy context all at once. This repo ships with
`/hackathon-aws`. Try:

```text
/hackathon-aws What AWS resources are already set up for the hackathon?
Don't launch anything — just summarize.
```

Claude reads the full account inventory (VPCs, subnets, security
groups, AMIs, Bedrock model IDs) before responding. You'll see it cite
exact resource IDs rather than guessing.

You don't need a slash command for HPC — the `scripps-garibaldi-hpc`
skill auto-loads when you ask about Garibaldi. Try:

```text
Write me an interactive Slurm session with 32 GB of RAM for 2 hours
on Garibaldi.
```

Notice Claude uses the correct partition names and login conventions
from the skill, not generic Slurm.

---

## 5. Switch modes

Claude Code has **permission modes** that control how often it stops
to ask you. Cycle through them by pressing **`Shift+Tab`** at the
prompt:

| Mode                  | Behavior                                                                 |
|-----------------------|--------------------------------------------------------------------------|
| Default               | Asks before writing files, running shell commands, etc.                  |
| **Auto-accept edits** | Approves file edits automatically — still asks for shell commands.       |
| **Plan mode**         | Read-only research mode. Claude makes a plan but won't change anything.  |

> **Try it now:** press `Shift+Tab` until the bottom of the screen
> shows "auto-accept edits", then ask:
>
> > "Add a 'Hackathon goals' section to my `hello-world/profile.md`
> > with three placeholder bullets."
>
> Notice Claude makes the edit without prompting. Press `Shift+Tab`
> a couple more times to land on **Plan mode**, and ask:
>
> > "How would you organize a multi-stage Slurm pipeline for an
> > `scRNA-seq` analysis?"
>
> Claude will respond with a plan instead of touching files.

**When to use each:**

- **Default:** the safe default. Use this when you're new or doing
  anything that touches AWS / shared resources.
- **Auto-accept edits:** great for tight feedback loops in your own
  workspace — e.g. when Claude is iterating on a script you're testing.
- **Plan mode:** use when you want to *think* with Claude before
  committing to changes. Especially good for "should we do X or Y?"
  questions.

---

## 6. Auto mode (no clarifying questions)

There's one more mode worth knowing. **Auto mode** tells Claude to
make reasonable judgment calls instead of pausing to ask. It's great
when you have a clear goal and want Claude to just go.

Start it by adding the `--auto` flag (or by saying it inline):

```text
In auto mode: set up a fresh personal S3 bucket using my profile,
upload hello-world/profile.md to it, and then download it back into
/tmp to verify the round-trip. Pick reasonable names where I haven't
specified.
```

You can always interrupt with **`Esc`** if Claude starts heading
somewhere you don't want.

> **Rule of thumb:** combine auto mode with auto-accept-edits when
> you're doing fast local iteration. Keep both *off* when you're
> issuing AWS commands you can't undo (terminating prod resources,
> deleting buckets with data).

---

## 7. Useful commands while you work

- `Esc` — interrupt whatever Claude is doing
- `Shift+Tab` — cycle permission modes
- `/help` — see all built-in commands
- `/clear` — start a fresh conversation (keeps memory, drops context)
- `/cost` — see token usage for the current session
- `Ctrl+R` (or two Esc presses) — switch to a previous message
- `#` at the start of a message — save it as a memory note

---

## You're ready

Move on to the other hello-world exercises — but now from inside
Claude Code:

> "Run [hello-world/hello_local.py](hello_local.py) and tell me if my
> environment is healthy."

> "Walk me through `test_skill.sh` step-by-step — I want to understand
> what it's about to do before I run it."

> "I just got a fresh HPC account. Help me submit
> [hello-world/hello_hpc.slurm](hello_hpc.slurm) end-to-end."

Welcome to the hackathon.
