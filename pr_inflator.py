# pr inflator
# makes a PR for every line you changed lol
# run it in a git repo with uncommitted changes
#   python pr_inflator.py --dry-run   (just shows what it would do)
#   python pr_inflator.py             (makes the branches locally)
#   python pr_inflator.py --for-real  (actually pushes + opens the PRs, needs gh)

import subprocess
import sys
import os
import time
import random
import shutil
import argparse
import difflib
from pathlib import Path

titles = [
    "feat: strategically introduce a line",
    "refactor: realign synergies at the character level",
    "perf: shave 0 ms off nothing",
    "chore: incremental value delivery",
    "fix: proactively address a line before it becomes a bug",
    "feat: unlock shareholder value (line edition)",
    "refactor: right-size this line for scale",
    "docs: let the code speak for itself",
    "feat: move the needle, one character at a time",
    "chore: iterate with agility",
    "refactor: leverage best-in-class whitespace",
    "feat: ship it",
]


def git(*args):
    result = subprocess.run(["git"] + list(args), capture_output=True, text=True)
    if result.returncode != 0:
        err = result.stderr or result.stdout
        raise Exception("git " + " ".join(args) + " failed: " + err.strip())
    return result.stdout


def get_changed_files():
    changed = git("diff", "HEAD", "--name-only", "-z").split("\0")
    new_files = git("ls-files", "--others", "--exclude-standard", "-z").split("\0")
    files = []
    for f in changed + new_files:
        if f != "" and f not in files:
            files.append(f)
    files.sort()
    return files


def get_old_version(path):
    # --filters is important on windows otherwise the line endings dont match
    result = subprocess.run(["git", "cat-file", "--filters", "HEAD:" + path], capture_output=True)
    if result.returncode != 0:
        return None  # file is new
    return result.stdout


def fix_endings(lines):
    out = []
    for l in lines:
        out.append(l.replace("\r\n", "\n"))
    return out


def split_into_steps(old, new):
    # goes from old to new changing one line at a time
    # returns a list of (lines, what changed)
    steps = []
    current = list(old)
    offset = 0  # how much the line numbers moved from stuff we already did

    matcher = difflib.SequenceMatcher(None, fix_endings(old), fix_endings(new), autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue

        pos = i1 + offset
        num_old = i2 - i1
        num_new = j2 - j1

        # replace = change the lines that line up, then delete/add whatever is left over
        same = 0
        if tag == "replace":
            same = min(num_old, num_new)

        for k in range(same):
            current[pos + k] = new[j1 + k]
            steps.append((list(current), "change line " + str(pos + k + 1)))

        for k in range(num_old - same):
            del current[pos + same]
            steps.append((list(current), "delete line " + str(pos + same + 1)))

        for k in range(same, num_new):
            current.insert(pos + k, new[j1 + k])
            steps.append((list(current), "add line " + str(pos + k + 1)))

        offset += num_new - num_old

    return steps


def make_plan(path, old, new):
    try:
        old_lines = []
        new_lines = []
        if old is not None:
            old_lines = old.decode("utf-8").splitlines(keepends=True)
        if new is not None:
            new_lines = new.decode("utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        # images and stuff, just do it in one go
        return [(path, new, "binary file, a single heroic PR")]

    plan = []
    if old is None and len(new_lines) == 0:
        plan.append((path, b"", "create empty file"))

    for lines, what in split_into_steps(old_lines, new_lines):
        plan.append((path, "".join(lines).encode("utf-8"), what))

    # make sure the last step is EXACTLY what the user had
    if new is not None and len(plan) > 0 and plan[-1][1] != new:
        plan[-1] = (path, new, plan[-1][2])

    if new is None:
        plan.append((path, None, "delete the now-empty file"))

    return plan


def write_file(path, content):
    if content is None:
        if os.path.exists(path):
            os.remove(path)
        return
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)


parser = argparse.ArgumentParser(description="one line of code = one pull request")
parser.add_argument("--dry-run", action="store_true", help="just print the plan")
parser.add_argument("--for-real", action="store_true", help="push and open the PRs (needs gh)")
parser.add_argument("--prefix", default="inflate", help="branch name prefix")
parser.add_argument("--yes", action="store_true", help="dont ask to confirm")
args = parser.parse_args()

os.chdir(git("rev-parse", "--show-toplevel").strip())
start_branch = git("rev-parse", "--abbrev-ref", "HEAD").strip()

files = get_changed_files()
if len(files) == 0:
    print("nothing to inflate. write some code first (one line is plenty)")
    sys.exit()

old_versions = {}
new_versions = {}
plan = []
for f in files:
    old_versions[f] = get_old_version(f)
    if os.path.exists(f):
        with open(f, "rb") as fh:
            new_versions[f] = fh.read()
    else:
        new_versions[f] = None
    plan += make_plan(f, old_versions[f], new_versions[f])

total = len(plan)
print(f"found {len(files)} changed file(s) -> {total} pull requests")
print(f"productivity increase: {(total - 1) * 100:,}%")
print()

if args.dry_run:
    for i in range(total):
        print(f"  PR {i + 1}: {plan[i][2]} in {plan[i][0]}")
    sys.exit()

if args.for_real:
    if shutil.which("gh") is None:
        print("you need the github cli (gh) for --for-real. install it and do gh auth login")
        sys.exit(1)
    if not args.yes:
        answer = input(f"about to open {total} PRs for real. type {total} to confirm: ")
        if answer.strip() != str(total):
            print("cancelled. your manager will never know what could have been")
            sys.exit()

# backup first just in case
backup = Path(git("rev-parse", "--git-dir").strip()) / "pr-inflator-backup" / time.strftime("%Y%m%d-%H%M%S")
for f in files:
    if new_versions[f] is not None:
        os.makedirs(os.path.dirname(backup / f), exist_ok=True)
        with open(backup / f, "wb") as fh:
            fh.write(new_versions[f])

stamp = time.strftime("%Y%m%d%H%M%S")
prev_branch = start_branch
links = []

try:
    # go back to how the files were, then redo the changes one line at a time
    for f in files:
        write_file(f, old_versions[f])

    n = 0
    for path, content, what in plan:
        n += 1
        branch = f"{args.prefix}/{stamp}/line-{n:04d}"
        git("checkout", "-q", "-b", branch)
        write_file(path, content)
        git("add", "-A", "--", path)

        # sometimes nothing actually changed (line ending stuff) so skip it
        if git("diff", "--cached", "--name-only").strip() == "":
            git("checkout", "-q", prev_branch)
            git("branch", "-q", "-D", branch)
            continue

        title = random.choice(titles) + f" ({n}/{total})"
        git("commit", "-q", "-m", title, "-m", f"{what} in {path}\n\nmade with pr-inflator")

        if args.for_real:
            git("push", "-q", "-u", "origin", branch)
            body = f"{what} in `{path}`.\n\npart {n} of {total} of one change, stacked on `{prev_branch}`. merge in order.\n\n_made with pr-inflator_"
            result = subprocess.run(["gh", "pr", "create", "--base", prev_branch, "--head", branch,
                                     "--title", title, "--body", body], capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception("gh pr create failed: " + result.stderr.strip())
            links.append(result.stdout.strip())

        print(f"  [{n}/{total}] {branch}: {what} in {path}")
        prev_branch = branch

except Exception as e:
    # put their stuff back so nothing gets lost
    for f in files:
        write_file(f, new_versions[f])
    print()
    print("something broke: " + str(e))
    print("your changes are back in your files (not committed) on " + git("rev-parse", "--abbrev-ref", "HEAD").strip())
    print("theres also a backup in " + str(backup))
    sys.exit(1)

print()
print(f"done! you're on {prev_branch} which has your whole change")
print(f"PRs created: {total}. lines of actual work: {total}. ratio: perfect")
if len(links) > 0:
    print("first PR: " + links[0])
    print("last PR: " + links[-1])
