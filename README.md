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
- Для более стабильной работы skill'а есть несколько шагов, которые нужно ревьюить вручную. Общий флоу выглядит так:
  - Закинуть агенту ссылку на app или вэб-воронку с вызовом skill'а
  - Skill начёт собирать инфу (домены, legal names, keywords) 
  - Когда он закончит, то предложит проверить список keywords и доменов (пауза во флоу до ответа юзера)
  - После подтверждения списка skill начинает поиск всех подходящих FB Ad страниц (Phgase 1)
  - Далее юзер должен перепроверить список найденных страниц перед более глубоким скрэйпингом (пауза во флоу до ответа юзера)
  - После подтверждения skill начинает более глубокий скрэйпинг всех найденных страниц и поиск воронок в них (Phase 2 – занимает около 30 мин)
- Если среди кампаний на страницах найдена новая воронка, то skill перезапустить Phase 1, чтобы потенциально найти больше FB Ad страниц (автоматический запуск)
- После завершения всех фаз skill собирает отчёт и таблицы с найденными ссылками
- Рекомендую выборочно проверить информацию о кол-ве активных РК для страниц, т.к. бывают кейсы, когда skill неправильно парсит их кол-во и может пометить FB Ad страницу как неактивную. Если случится такой кейс, то нужно попросить перепроверить страницу и он перезапустит Phase 2

Т.к. использование Playwright делает процесс относительно долгим и рискованным для аккаунта, то можно доработать skill и использовать сторонние API для скрейпинга, если skill будет полезен.

---
