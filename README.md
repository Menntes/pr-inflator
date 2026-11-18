# pr-inflator 📈

**Turn a dumb metric on it's head.**

`pr-inflator` takes the change you just wrote and opens one pull request for every single line of it.
A 40-line bug fix becomes 40 PRs.

```
$ python pr_inflator.py --dry-run
found 3 changed file(s) -> 212 pull requests
productivity increase: 21,100%
```

## Why

> "When a measure becomes a target, it ceases to be a good measure." (Goodhart's law)

I personally know some great engineers who are being measured not on their work, but on how many PRs they open. That number says nothing about value, and it pushes people to cut their work into smaller and smaller pieces.

This tool takes that to its logical end. If everyone ran it, the number of PRs would measure nothing at all,
and that's the point! If everone has PR's maxed, no one does.

## "But one-line PRs won't compile!"

Correct, and that was the first objection from the first person I showed this to (dad)

So `pr-inflator` makes **stacked** PRs. PR #2's base branch is PR #1's branch, PR #3 sits on PR #2, and so on.
Every PR's diff is exactly one line, but the code at every step contains all the lines before it.
Merge them in order and your change lands exactly as you wrote it.

In other words, the code works fine. The metric is the thing that breaks.

## Usage

Make your changes in a git repo, don't commit them, then:

```bash
python pr_inflator.py --dry-run     # preview the PR count, touch nothing
python pr_inflator.py               # create the stacked branches and commits locally
python pr_inflator.py --for-real    # also push them and open the PRs (needs the gh CLI)
```

`--for-real` asks you to type the exact number of PRs before it starts, as a last moment of reflection.

Your finished files are backed up to `.git/pr-inflator-backup/` before anything happens.

## FAQ

**Should I run this at work?**
No. The people reviewing your code will get angry. Goodluck on trying to convince the rest of your team to join you before you get sacked.

**Then what's it for?**
It's just a showcase on how dumb the metric of "# of PRs" is. A simple addition can be hundreds of PRs, while something meaningful can just be a few. 

**Does it support commits-per-day, lines of code, or story points?**
Not yet. But feel free to do PRs to this repo, hopefully hundreds.

## License

MIT. One line at a time.
