# Git hooks

The repository is configured locally to use this directory as its Git hooks path.
The `post-commit` hook pushes the current branch after every successful commit.

To enable it in a fresh clone:

```bash
git config core.hooksPath .githooks
chmod +x .githooks/post-commit
```
