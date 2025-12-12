# Демо-сценарий (UI + GitLab)

## Часть 1. Генерация ручных/UI кейсов
1. Открыть Dashboard → «Сгенерировать тесты».
2. Загрузить `demo_materials/manual/ui-calculator-openapi.yaml`, выбрать тип UI/manual, язык ru, паттерн AAA.
3. Запустить задачу, перейти в Tasks и показать live-статус.
4. После SUCCESS: скачать ZIP, открыть пример кейса с allure метками и шагами.
5. Показать валидатор (owner/priority/AAA).

## Часть 2. Генерация API автотестов
1. Загрузить `demo_materials/api/evolution-compute-sample.yaml`, выбрать тип API/auto (pytest).
2. Дождаться завершения, скачать артефакт, показать декораторы allure и негативные кейсы.

## Часть 3. GitLab интеграция
1. Использовать папку `gitlab-test` → `git init`, подключить новый проект в GitLab, `git push`.
2. Запустить pipeline (lint + test + coverage). Показать coverage виджет и логи job.
3. В UI TestOps Copilot подключить GitLab token, выбрать проект, запустить анализ (coverage/дубликаты).
4. Показать рекомендации и ссылки на MR/branch (если заданы).

## Метрики для показа
- Время генерации 5–10 кейсов (<30 сек).
- Доля корректных тестов без правок (>80%).
- Coverage отчёт из GitLab pipeline.

