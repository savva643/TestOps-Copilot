# TestOps Copilot Frontend Dashboard

React + TypeScript frontend для TestOps Copilot.

## Технологии

- React 19
- TypeScript
- Vite
- React Router
- TanStack Query
- Axios
- Recharts (для графиков)

## Установка

```bash
npm install
```

## Разработка

```bash
npm run dev
```

Приложение будет доступно на http://localhost:3000

## Сборка

```bash
npm run build
```

## Линтинг

```bash
npm run lint
npm run format
```

## Переменные окружения

Создайте файл `.env`:

```
VITE_API_URL=http://localhost:8000
VITE_API_KEY=your-api-key-here
```

## Структура

```
src/
├── api/          # API клиенты
├── components/   # React компоненты
├── pages/        # Страницы приложения
├── stores/       # Zustand сторы (если нужны)
└── types/        # TypeScript типы
```

## Основные страницы

- **Home** - Главная страница с описанием возможностей
- **Generate** - Генерация тест-кейсов
- **Tasks** - Просмотр статуса задач
- **Optimize** - Оптимизация тестов (v1.1)

