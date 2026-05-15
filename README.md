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
## General notes

- Для работы skill'a нужен Playwright MCP (если не установлен – агент предложит это сделать)
- Также для скрэйпинга FB Ads Library необходим логин в FB аккаунт – это несёт риск для аккаунта, т.к. Meta запрещает "automated access to their services"
- Для более стабильной работы skill'а есть несколько шагов, которые нужно ревьюит вручную. Общий влой выглядит так:
  - Закинуть ссылку на app или вэб-воронку с вызовом skill'а
  - Skill начёт собирать инфу (домены, legal names, keywords) 
  - Когда он закончит, то предложит проверить список keywords и доменов (пауза во флоу до ответа юзера)
  - После подтверждения списка skill начинает поиск всех подходящих FB Ad страниц (Phgase 1)
  - Далее юзер должен перепроверить список найденных страниц перед более глубоким скрэйпингом (пауза во флоу до ответа юзера)
  - После подтверждения skill начинает более глубокий скрэйпинг всех найденных страниц и поиск воронок в них (Phase 2 – занимает около 30 мин)
- Если среди кампаний на страницах найдена новая воронка, то skill перезапустить Phase 1, чтобы потенциально найти больше FB Ad страниц
- После завершения всех фаз skill собирает отчёт и таблицы с найденными ссылками
- Рекомендую проверить информацию о кол-ве активных РК для некоторых страниц, т.к. бывают кейсы, когда skill неправильно парсит их кол-во и помечает FB Ad страницу как неактивную. Если случится такой кейс, то нужно попросить перепроверить страницу и он перезапустит Phase 2

Т.к. использование Playwright делает процесс относительно долгим и рискованным для аккаунта, то можно доработать skill и использовать сторонние API для скрейпинга, если skill будет полезен.

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
