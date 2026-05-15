# competitors-w2w-research

A Claude Code skill that maps a competitor app's web-to-web (W2W) paid-acquisition funnels — Facebook ad pages, funnel URLs, status classification, and tech-stack detection. See [SKILL.md](SKILL.md) for the full workflow.

## Install

```bash
git clone https://github.com/relllxr/competitors-w2w-research.git ~/.claude/skills/competitors-w2w-research
```

Restart Claude Code (or run `/skills`) and the skill will be auto-detected.

## Update

```bash
cd ~/.claude/skills/competitors-w2w-research && git pull
```

---

## Maintainer notes

### Dev sandbox

A sandbox copy lives at `~/.claude/skills/competitors-w2w-research-dev` with `name: competitors-w2w-research-dev` in its frontmatter, so both skills load side-by-side without colliding. The sandbox is **not** under git control — edit it freely, break it, throw it away.

To trigger the sandbox version explicitly during testing, ask Claude to use `/skill competitors-w2w-research-dev` (the description has a "do not auto-trigger" guard so it won't run by accident).

### Publishing dev → main

When changes in the sandbox are ready to ship:

```bash
rsync -av --delete --exclude='.git' \
  ~/.claude/skills/competitors-w2w-research-dev/ \
  ~/.claude/skills/competitors-w2w-research/

cd ~/.claude/skills/competitors-w2w-research
git add -A
git commit -m "describe what changed"
git push
```

Then ping colleagues to `git pull`.

### Resetting the sandbox to match published

If the sandbox drifts and you want to start from the published version again:

```bash
rm -rf ~/.claude/skills/competitors-w2w-research-dev
cp -R ~/.claude/skills/competitors-w2w-research ~/.claude/skills/competitors-w2w-research-dev
rm -rf ~/.claude/skills/competitors-w2w-research-dev/.git
# then re-apply the dev frontmatter rename in SKILL.md
```
