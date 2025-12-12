# Демо GitLab интеграции

Цель: показать генерацию/публикацию тестов и аналитику через GitLab CI/CD.

Сценарий:
1) Используйте папку `gitlab-test` (см. корень репо) как пример проекта.
2) В GitLab создайте новый проект и запушьте содержимое:
   - `.gitlab-ci.yml` — пайплайн lint+test, артефакт coverage.
   - `src/main.py`, `tests/test_main.py` — простой код для демонстрации.
3) Запустите pipeline и покажите:
   - статус job'ов,
   - отчет покрытия (coverage.xml → виджет в MR/проекте),
   - артефакты (если включите upload),
   - логи пайплайна.
4) Интеграция с TestOps Copilot:
   - Подключить GitLab token в UI,
   - выбрать проект `gitlab-test`,
   - запросить анализ покрытия/дубликатов,
   - получить рекомендации и список тестов на доработку.

Примечания:
- Для Code Quality/Dependency Scanning можно добавить шаблоны GitLab:  
  `include: template: Code-Quality.gitlab-ci.yml` и др.
- Для бэйджей используйте URL вида  
  `https://gitlab.com/<group>/<project>/badges/main/pipeline.svg`.

