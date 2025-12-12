# GitLab Test Project

> 📖 Вернуться к [главной документации](../README.md)

Минимальный проект для проверки CI/CD, coverage и интеграции с TestOps Copilot.

Содержимое:
- `.gitlab-ci.yml` — пайплайн lint + test, выгрузка coverage.xml.
- `src/main.py` — простая функция.
- `tests/test_main.py` — pytest, проверяет функцию и демонстрирует покрытие.

Как запустить:
1. `git init && git add . && git commit -m "chore: init"`
2. Создать проект в GitLab и привязать remote:  
   `git remote add origin <gitlab-url>`  
   `git push -u origin main`
3. Проверить pipeline в GitLab → CI/CD → Pipelines, открыть coverage отчет.

Бэйджи (замените group/project):
- Pipeline: `https://gitlab.com/<group>/<project>/badges/main/pipeline.svg`
- Coverage: `https://gitlab.com/<group>/<project>/badges/main/coverage.svg`

## Связанная документация

- [README.md](../README.md) — Главная документация проекта
- [demo_materials/gitlab/README.md](../demo_materials/gitlab/README.md) — Демо GitLab интеграции
- [docs/DEMO_SCENARIO.md](../docs/DEMO_SCENARIO.md) — Сценарий демонстрации

