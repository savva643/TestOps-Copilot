# Руководство пользователя TestOps Copilot

> 📖 Вернуться к [главной документации](../../README.md)

## Содержание

## 1. Быстрый старт (UI)
- Перейдите на Dashboard → кнопка «Сгенерировать тесты».
- Загрузите спецификацию: `demo_materials/manual/ui-calculator-openapi.yaml` (UI) или `demo_materials/api/evolution-compute-sample.yaml` (API).
- Укажите тип тестов (UI/API/manual/auto), язык (ru/en), паттерн AAA, owner/priority.
- Запустите задачу и перейдите в «Все задачи» для мониторинга.
- После завершения скачайте ZIP-артефакт и просмотрите тесты.

## 2. Интеграция с GitLab (аналитика/оптимизация)
- В настройках UI добавьте GitLab token (Bearer).
- В разделе Optimize выберите проект (например, `gitlab-test`, см. папку `gitlab-test/`).
- Запустите анализ: покрытие, дубликаты, рекомендации.
- В MR отображается статус пайплайна и coverage badge (добавьте URL в README проекта).

## 3. Рекомендации по качеству тестов
- Используйте метки allure: owner, priority, feature/story/suite.
- Следуйте паттерну AAA (Arrange-Act-Assert).
- Для автотестов: отдавайте предпочтение pytest + allure; для UI — добавляйте шаги и скриншоты.

## 4. Частые операции
- Повторный запуск задачи: через экран Tasks.
- Фильтр по владельцу: хранится в credentials (owner_id).
- Обновление статусов: кнопка «Обновить» на Dashboard и Tasks.

## 5. Экспорт/отчёты
- Артефакты доступны после SUCCESS/COMPLETED статуса.
- Для GitLab задач подтягиваются gitlab_url/MR (если заданы при создании).

## 6. Где смотреть примеры
- [demo_materials/manual/](../../demo_materials/manual/) — UI калькулятор (ручные кейсы).
- [demo_materials/api/](../../demo_materials/api/) — Evolution Compute (API автотесты/ручные).
- [demo_materials/gitlab/](../../demo_materials/gitlab/) — сценарий GitLab CI/CD + интеграция.

## Связанная документация

- [QUICK_START.md](../../QUICK_START.md) — Быстрый старт
- [QUICK_TEST.md](../../QUICK_TEST.md) — Быстрая проверка работоспособности
- [docs/DEMO_SCENARIO.md](DEMO_SCENARIO.md) — Сценарий демонстрации
- [docs/TESTING_INSTRUCTIONS.md](TESTING_INSTRUCTIONS.md) — Инструкции по тестированию

