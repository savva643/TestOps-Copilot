"""Celery tasks for test generation."""

from typing import Optional, Dict, Any
import structlog
from celery import Task
from app.services.llm_client import LLMClient
from app.services.prompt_engineer import PromptEngineer, PromptValidationError
from app.services.standard_validator import StandardValidator
from app.core.exceptions import LLMError, TaskError

logger = structlog.get_logger()


class ProgressTrackingTask(Task):
    """Custom task class with progress tracking."""

    def update_progress(self, current: int, total: int, message: str = ""):
        """Update task progress."""
        progress = int((current / total) * 100) if total > 0 else 0
        self.update_state(
            state="PROGRESS",
            meta={
                "current": current,
                "total": total,
                "progress": progress,
                "message": message,
            },
        )
        logger.info(
            "Task progress updated",
            task_id=self.request.id,
            progress=progress,
            message=message,
        )


def generate_test_case_task(
    self: ProgressTrackingTask,
    description: str,
    test_type: str = "manual",
    feature: Optional[str] = None,
    story: Optional[str] = None,
    priority: str = "NORMAL",
    owner: Optional[str] = None,
    jira_link: Optional[str] = None,
    llm_api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a test case using LLM.

    This is a Celery task that runs asynchronously.
    """
    logger.info(
        "Starting test case generation",
        task_id=self.request.id,
        test_type=test_type,
        priority=priority,
    )

    try:
        # Update progress: 0% - Starting
        self.update_progress(0, 100, "Initializing...")

        # Initialize LLM client with API key if provided
        llm_client = LLMClient(api_key=llm_api_key)

        # Update progress: 20% - Validating and preparing prompts
        self.update_progress(20, 100, "Validating inputs and preparing prompts...")

        # Get prompts (with validation)
        prompt_engineer = PromptEngineer()
        try:
            system_prompt, user_prompt = prompt_engineer.get_test_case_generation_prompt(
                description=description,
                test_type=test_type,
                feature=feature,
                story=story,
                priority=priority,
                owner=owner,
                jira_link=jira_link,
            )
        except PromptValidationError as e:
            logger.error("Prompt validation failed", error=str(e))
            raise

        # Update progress: 40% - Calling LLM
        self.update_progress(40, 100, "Generating test case with LLM...")

        # Generate test case
        # Note: This is a sync function, but LLM client is async
        # Create new event loop for async operations
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        def extract_code_blocks_from_markdown(txt: str) -> list[dict]:
            """Извлекает все блоки кода из markdown с описаниями перед ними.
            
            Обрабатывает формат, где ИИ возвращает markdown с объяснениями и кодом:
            - Объяснение в начале
            - Блоки кода ```python ... ```
            - Объяснения между блоками кода
            
            Returns:
                List of dicts: [{"description": "...", "code": "..."}, ...]
            """
            import re
            # Более гибкий паттерн: ищем ```python или ``` с любым содержимым
            # Поддерживает варианты:
            # - ```python\nкод\n```
            # - ```python код```
            # - ```\nкод\n```
            # - ``` код```
            patterns = [
                r'```(?:python)?\s*\n(.*?)\n```',  # Стандартный формат с переносами строк
                r'```(?:python)?\s+(.*?)```',      # Без переноса строк после ```
                r'```(?:python)?(.*?)```',          # Без пробелов
            ]
            
            files = []
            last_end = 0
            all_matches = []
            
            # Пробуем все паттерны и собираем все совпадения
            for pattern in patterns:
                matches = list(re.finditer(pattern, txt, re.DOTALL))
                for match in matches:
                    # Проверяем, не перекрывается ли с уже найденными
                    overlap = False
                    for existing in all_matches:
                        if not (match.end() <= existing.start() or match.start() >= existing.end()):
                            overlap = True
                            break
                    if not overlap:
                        all_matches.append(match)
            
            # Сортируем по позиции начала
            all_matches.sort(key=lambda m: m.start())
            
            # Если есть общее объяснение в начале (до первого блока кода)
            general_description = None
            if all_matches:
                first_match = all_matches[0]
                text_before_first = txt[:first_match.start()].strip()
                if text_before_first:
                    # Проверяем, что это не код (не начинается с import/from/def/class)
                    if not any(text_before_first.lstrip().startswith(kw) for kw in 
                              ['import ', 'from ', 'def ', 'class ', '@pytest', '@allure']):
                        general_description = text_before_first
            
            for i, match in enumerate(all_matches):
                # Текст перед этим блоком кода - описание для этого конкретного блока
                description_start = last_end
                description_end = match.start()
                block_description = txt[description_start:description_end].strip()
                
                code = match.group(1).strip()
                
                # Пропускаем пустые блоки
                if not code:
                    continue
                
                # Объединяем общее описание (если есть и это первый блок) с описанием блока
                if i == 0 and general_description:
                    if block_description:
                        final_description = f"{general_description}\n\n{block_description}"
                    else:
                        final_description = general_description
                else:
                    final_description = block_description if block_description else None
                
                files.append({
                    "description": final_description if final_description else None,
                    "code": code,
                    "filename": f"test_{i+1}.py" if len(all_matches) > 1 else "test.py"
                })
                
                last_end = match.end()
            
            # Если есть текст после последнего блока кода
            if last_end < len(txt):
                remaining = txt[last_end:].strip()
                if remaining:
                    # Проверяем, что это не код
                    if not any(remaining.lstrip().startswith(kw) for kw in 
                              ['import ', 'from ', 'def ', 'class ', '@pytest', '@allure']):
                        # Если это не код, добавляем как описание к последнему файлу
                        if files:
                            if files[-1]["description"]:
                                files[-1]["description"] += "\n\n" + remaining
                            else:
                                files[-1]["description"] = remaining
            
            return files

        def extract_code_from_text(txt: str) -> dict:
            """Извлекает код из текста: структурированный ответ с файлами и описаниями."""
            # Пробуем извлечь из markdown блоков
            files = extract_code_blocks_from_markdown(txt)
            if files:
                return {
                    "files": files,
                    "raw_response": txt  # Сохраняем оригинальный ответ
                }
            
            # Если нет markdown блоков, ищем код, начинающийся с import/from или других ключевых слов
            lines = txt.splitlines()
            code_start_idx = None
            
            # Ищем начало кода по ключевым словам Python
            python_starters = ['import ', 'from ', 'def ', 'class ', '@pytest', '@allure', 'async def']
            for i, line in enumerate(lines):
                stripped_line = line.lstrip()
                for starter in python_starters:
                    if stripped_line.startswith(starter):
                        code_start_idx = i
                        break
                if code_start_idx is not None:
                    break
            
            if code_start_idx is not None:
                description = "\n".join(lines[:code_start_idx]).strip() if code_start_idx > 0 else None
                code = "\n".join(lines[code_start_idx:]).strip()
                
                # Проверяем, что код не пустой и содержит достаточно содержимого
                if code and len(code) > 50:  # Минимум 50 символов кода
                    return {
                        "files": [{
                            "description": description,
                            "code": code,
                            "filename": "test.py"
                        }],
                        "raw_response": txt
                    }
            
            # Если код не найден, но текст содержит Python-подобные конструкции, 
            # пытаемся извлечь код более агрессивно
            # Ищем блоки, которые выглядят как код (содержат отступы, ключевые слова)
            if 'def ' in txt or 'class ' in txt or '@pytest' in txt or '@allure' in txt:
                # Пытаемся найти начало реального кода, пропуская текст
                lines = txt.splitlines()
                code_lines = []
                in_code = False
                
                for line in lines:
                    stripped = line.lstrip()
                    # Если строка начинается с Python-ключевого слова или имеет отступ
                    if (stripped.startswith(('import ', 'from ', 'def ', 'class ', '@', 'async ')) or
                        (in_code and (line.startswith((' ', '\t')) or stripped == '' or stripped.startswith('#')))):
                        in_code = True
                        code_lines.append(line)
                    elif in_code and not stripped.startswith((' ', '\t', '#')) and stripped:
                        # Если мы в коде и встретили строку без отступа (не пустую и не комментарий),
                        # это может быть конец блока кода или начало нового
                        if any(stripped.startswith(kw) for kw in python_starters):
                            code_lines.append(line)
                        else:
                            break
                
                if code_lines:
                    code = "\n".join(code_lines).strip()
                    if len(code) > 50:
                        return {
                            "files": [{
                                "description": None,
                                "code": code,
                                "filename": "test.py"
                            }],
                            "raw_response": txt
                        }
            
            # Если код не найден, возвращаем весь текст как один файл
            return {
                "files": [{
                    "description": None,
                    "code": txt.strip(),
                    "filename": "test.py"
                }],
                "raw_response": txt
            }

        def has_code(txt: str) -> bool:
            """Проверяет, есть ли в тексте код (markdown блоки или import/from).
            
            Учитывает, что ответ может содержать markdown объяснения перед кодом.
            """
            # Сначала проверяем наличие блоков кода в markdown
            code_blocks = extract_code_blocks_from_markdown(txt)
            if code_blocks and any(block.get("code") and len(block["code"].strip()) > 10 for block in code_blocks):
                return True
            
            # Ищем import/from в любой строке, не только в начале
            lines = txt.splitlines()
            for line in lines:
                stripped = line.lstrip()
                if stripped.startswith("import ") or stripped.startswith("from "):
                    return True
            
            # Также проверяем наличие ключевых слов Python (но не в markdown заголовках)
            python_keywords = ['def ', 'class ', '@pytest', '@allure', 'async def', 'assert ']
            txt_lower = txt.lower()
            for keyword in python_keywords:
                # Проверяем, что ключевое слово не в markdown заголовке (не начинается с #)
                keyword_pos = txt_lower.find(keyword)
                if keyword_pos != -1:
                    # Проверяем, что перед ключевым словом нет # на той же строке
                    line_start = txt.rfind('\n', 0, keyword_pos)
                    if line_start == -1:
                        line_start = 0
                    else:
                        line_start += 1
                    line_before_keyword = txt[line_start:keyword_pos].strip()
                    if not line_before_keyword.startswith('#'):
                        return True
            return False

        # Первичная генерация
        generated_text = loop.run_until_complete(
            llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        )

        # Для API/UI извлекаем код из ответа (может быть в markdown блоках или как чистый код)
        if test_type in ["api", "ui"]:
            # Логируем первые 500 символов для отладки
            preview = generated_text[:500].replace("\n", "\\n")
            logger.debug(
                "LLM response preview",
                task_id=self.request.id,
                preview=preview,
                length=len(generated_text),
            )
            
            # Извлекаем код из ответа (может быть несколько файлов)
            # Это нормальный формат ответа ИИ - markdown с объяснениями и кодом
            extracted = extract_code_from_text(generated_text)
            
            # Проверяем, что извлеченный код валидный
            has_valid_code = False
            if extracted and extracted.get("files") and len(extracted["files"]) > 0:
                # Проверяем, что извлеченный код не пустой
                valid_files = [f for f in extracted["files"] if f.get("code") and len(f["code"].strip()) > 50]
                if valid_files:
                    has_valid_code = True
                    logger.info(
                        "Extracted code files from LLM response",
                        task_id=self.request.id,
                        files_count=len(valid_files),
                        has_descriptions=any(f.get("description") for f in valid_files),
                    )
                    # Сохраняем только валидные файлы
                    extracted["files"] = valid_files
                    generated_text = extracted
                else:
                    logger.warning(
                        "Extracted files are empty or too short",
                        task_id=self.request.id,
                        extracted_files_count=len(extracted.get("files", [])),
                    )
            
            # Если код не найден, проверяем более строго и пробуем повторный запрос
            if not has_valid_code:
                # Проверяем через has_code (может найти код, который не извлекся)
                if not has_code(generated_text if isinstance(generated_text, str) else str(generated_text)):
                    logger.warning(
                        "LLM response doesn't contain code blocks or import statements",
                        task_id=self.request.id,
                        preview=preview,
                    )
                    # Пробуем ещё раз с более строгим промптом
                    strict_user_prompt = (
                        "СТРОГОЕ ТРЕБОВАНИЕ: Твой ответ ДОЛЖЕН начинаться СРАЗУ с ```python (без единого символа перед ним). "
                        "ЗАПРЕЩЕНО писать: 'We need to...', 'Let's create...', 'I'll generate...', 'Here is...'. "
                        "ЗАПРЕЩЕНО писать планы действий или описания. "
                        "Пиши ТОЛЬКО готовый код на Python внутри блока ```python ... ```.\n\n"
                        + user_prompt
                    )
                    generated_text = loop.run_until_complete(
                        llm_client.generate(
                            system_prompt=system_prompt,
                            user_prompt=strict_user_prompt,
                        )
                    )
                    
                    # Извлекаем код из повторного ответа
                    extracted = extract_code_from_text(generated_text)
                    if extracted and extracted.get("files") and len(extracted["files"]) > 0:
                        valid_files = [f for f in extracted["files"] if f.get("code") and len(f["code"].strip()) > 50]
                        if valid_files:
                            extracted["files"] = valid_files
                            generated_text = extracted
                            has_valid_code = True
                    
                    # Проверяем снова
                    if not has_valid_code and not has_code(generated_text if isinstance(generated_text, str) else str(generated_text)):
                        # Логируем полный ответ для отладки
                        logger.error(
                            "LLM still doesn't return code after retry",
                            task_id=self.request.id,
                            response_preview=str(generated_text)[:1000] if isinstance(generated_text, str) else str(generated_text)[:1000],
                        )
                        raise LLMError(
                            "Invalid response from LLM API",
                            details={
                                "reason": "expected code in markdown blocks or starting with import/from",
                                "response_preview": str(generated_text)[:500] if isinstance(generated_text, str) else str(generated_text)[:500]
                            },
                        )
            
            # Если после всех проверок код не извлечен, используем fallback
            if not has_valid_code or not isinstance(generated_text, dict):
                logger.warning(
                    "Failed to extract code files, using fallback",
                    task_id=self.request.id,
                )
                # Fallback: сохраняем как один файл
                original_text = generated_text if isinstance(generated_text, str) else str(generated_text)
                generated_text = {
                    "files": [{
                        "description": None,
                        "code": original_text,
                        "filename": "test.py"
                    }],
                    "raw_response": original_text
                }

        # Update progress: 80% - Processing result
        self.update_progress(80, 100, "Processing generated test case...")

        # Валидация сгенерированного кода
        validation_result = None
        if test_type in ["api", "ui"]:
            validator = StandardValidator()
            # Валидируем первый файл (или все файлы)
            if isinstance(generated_text, dict) and generated_text.get("files"):
                first_file_code = generated_text["files"][0].get("code", "")
                if first_file_code:
                    validation_result = validator.validate_test_case(first_file_code, test_type)
                    logger.info(
                        "Validation completed",
                        task_id=self.request.id,
                        is_valid=validation_result.get("is_valid"),
                        score=validation_result.get("score"),
                        errors_count=len(validation_result.get("errors", [])),
                    )

        # Close client
        loop.run_until_complete(llm_client.close())

        # Формируем полный промпт для сохранения в артефактах
        full_prompt = f"System Prompt:\n{system_prompt}\n\nUser Prompt:\n{user_prompt}"
        
        def generate_explanation_md(
            test_type: str,
            feature: Optional[str],
            story: Optional[str],
            files: list,
            validation_result: Optional[dict] = None
        ) -> str:
            """Генерирует markdown файл с объяснениями фич и типов проверок."""
            lines = []
            lines.append("# Объяснение тестов и проверок\n")
            lines.append(f"**Тип теста:** {test_type.upper()}\n")
            
            if feature:
                lines.append(f"**Фича:** {feature}\n")
            if story:
                lines.append(f"**История:** {story}\n")
            
            lines.append("\n## Описание функциональности\n")
            if feature:
                lines.append(f"Тесты проверяют функциональность **{feature}**.")
            if story:
                lines.append(f"Основной фокус: **{story}**.")
            lines.append("\nТесты автоматизируют проверку корректной работы функциональности и обработку различных сценариев.\n")
            
            lines.append("\n## Типы проверок\n")
            if test_type == "api":
                lines.append("### API Тесты\n")
                lines.append("Тесты проверяют:\n")
                lines.append("- **Корректность HTTP запросов** - правильность формирования запросов, заголовков, тела")
                lines.append("- **Валидацию ответов** - статус коды, структура данных, типы полей")
                lines.append("- **Обработку ошибок** - корректная обработка 4xx/5xx ошибок")
                lines.append("- **Граничные случаи** - пустые значения, максимальные длины, специальные символы")
                lines.append("- **Бизнес-логику** - корректность расчетов, валидаций, состояний")
                lines.append("\n### Структура тестов\n")
                lines.append("- **Arrange (Подготовка)** - настройка тестовых данных, заголовков, параметров")
                lines.append("- **Act (Действие)** - выполнение HTTP запроса (GET, POST, PUT, DELETE и т.д.)")
                lines.append("- **Assert (Проверка)** - валидация статус кода, структуры ответа, значений полей")
            elif test_type == "ui":
                lines.append("### UI Тесты\n")
                lines.append("Тесты проверяют:\n")
                lines.append("- **Отображение элементов** - видимость, доступность, корректное позиционирование")
                lines.append("- **Интерактивность** - клики, ввод данных, навигация")
                lines.append("- **Валидацию форм** - проверка полей ввода, сообщений об ошибках")
                lines.append("- **Состояния интерфейса** - загрузка, ошибки, успешные операции")
                lines.append("- **Адаптивность** - корректное отображение на разных разрешениях")
                lines.append("\n### Структура тестов\n")
                lines.append("- **Arrange (Подготовка)** - открытие страницы, настройка начального состояния")
                lines.append("- **Act (Действие)** - взаимодействие с элементами (клики, ввод, навигация)")
                lines.append("- **Assert (Проверка)** - проверка видимости элементов, текста, состояний")
            
            lines.append("\n## Структура кода\n")
            lines.append("### Файлы тестов\n")
            for i, file in enumerate(files, 1):
                filename = file.get("filename", f"test_{i}.py")
                lines.append(f"\n#### {filename}\n")
                if file.get("description"):
                    lines.append(f"{file['description']}\n")
                else:
                    lines.append(f"Содержит тесты для проверки функциональности.\n")
            
            lines.append("\n### Используемые библиотеки\n")
            if test_type == "api":
                lines.append("- **pytest** - фреймворк для тестирования")
                lines.append("- **httpx** или **aiohttp** - для выполнения HTTP запросов")
                lines.append("- **allure-pytest** - для интеграции с Allure TestOps")
                lines.append("- **pydantic** - для валидации данных (если используется)")
            elif test_type == "ui":
                lines.append("- **pytest** - фреймворк для тестирования")
                lines.append("- **playwright** - для автоматизации браузера")
                lines.append("- **allure-pytest** - для интеграции с Allure TestOps")
            
            lines.append("\n### Allure декораторы\n")
            lines.append("Каждый тест использует следующие декораторы Allure:\n")
            lines.append("- `@allure.label(\"owner\", ...)` - владелец теста")
            if feature:
                lines.append(f"- `@allure.feature(\"{feature}\")` - функциональность")
            if story:
                lines.append(f"- `@allure.story(\"{story}\")` - история")
            lines.append(f"- `@allure.suite(\"{test_type}\")` - тип теста")
            lines.append("- `@allure.tag(...)` - приоритет теста")
            lines.append("- `@allure.title(...)` - название теста")
            lines.append("- `@allure.step(...)` - шаги внутри теста")
            
            if validation_result:
                lines.append("\n## Результаты валидации\n")
                is_valid = validation_result.get("is_valid", False)
                score = validation_result.get("score", 0)
                lines.append(f"- **Валидность:** {'✓ Валидный' if is_valid else '✗ Требует доработки'}\n")
                lines.append(f"- **Оценка:** {score}/100\n")
                errors = validation_result.get("errors", [])
                if errors:
                    lines.append(f"- **Найдено проблем:** {len(errors)}\n")
                    lines.append("\n### Рекомендации по улучшению:\n")
                    for error in errors[:5]:  # Показываем первые 5 ошибок
                        lines.append(f"- {error}\n")
            
            lines.append("\n## Как использовать\n")
            lines.append("1. Установите зависимости: `pip install -r requirements.txt`")
            lines.append("2. Настройте конфигурацию (URL, токены и т.д.)")
            lines.append("3. Запустите тесты: `pytest tests/ -v --alluredir=allure-results`")
            lines.append("4. Просмотрите результаты в Allure TestOps")
            
            return "\n".join(lines)
        
        # Если generated_text - это dict с файлами, сохраняем как есть
        # Если это строка (для manual тестов), преобразуем в структуру
        if isinstance(generated_text, str):
            # Для manual тестов генерируем имя файла с ID из текста или используем дефолтное
            import re
            tc_id_match = re.search(r'\*\*ID:\*\*\s*(TC-\d+)', generated_text)
            tc_id = tc_id_match.group(1) if tc_id_match else "TC-001"
            filename = f"manual_test_case_{tc_id}.txt"
            
            test_case_data = {
                "files": [{
                    "description": None,
                    "code": generated_text,
                    "filename": filename
                }],
                "raw_response": generated_text
            }
        else:
            test_case_data = generated_text
            # Для API/UI тестов добавляем файл с объяснениями
            if test_type in ["api", "ui"] and isinstance(test_case_data, dict) and test_case_data.get("files"):
                explanation_md = generate_explanation_md(
                    test_type=test_type,
                    feature=feature,
                    story=story,
                    files=test_case_data["files"],
                    validation_result=validation_result
                )
                # Добавляем файл с объяснениями в начало списка файлов
                test_case_data["files"].insert(0, {
                    "description": "Документация с объяснениями фич и типов проверок",
                    "code": explanation_md,
                    "filename": "EXPLANATION.md"
                })
        
        result = {
            "test_case": test_case_data,
            "test_type": test_type,
            "feature": feature,
            "story": story,
            "priority": priority,
            "owner": owner,
            "jira_link": jira_link,
            "prompt": full_prompt,  # Сохраняем промпт для отладки
        }
        
        # Добавляем результаты валидации, если есть
        if validation_result:
            result["validation"] = validation_result

        # Update progress: 100% - Complete
        self.update_progress(100, 100, "Test case generated successfully")

        logger.info(
            "Test case generated successfully",
            task_id=self.request.id,
            test_type=test_type,
        )

        return result

    except PromptValidationError as e:
        logger.error("Prompt validation error", task_id=self.request.id, error=str(e))
        raise TaskError(
            "Prompt validation failed",
            details={"task_id": self.request.id, "error": str(e)},
        )
    except LLMError as e:
        logger.error("LLM error", task_id=self.request.id, error=str(e))
        # Retry on LLM errors
        if self.request.retries < self.max_retries:
            logger.info(
                "Retrying task after LLM error",
                task_id=self.request.id,
                retry_count=self.request.retries + 1,
            )
            raise self.retry(exc=e)
        raise TaskError(
            "Failed to generate test case after retries",
            details={"task_id": self.request.id, "error": str(e)},
        )
    except Exception as e:
        logger.error(
            "Failed to generate test case",
            task_id=self.request.id,
            error=str(e),
            exc_info=True,
        )
        # Retry on certain exceptions
        if self.request.retries < self.max_retries:
            logger.info(
                "Retrying task",
                task_id=self.request.id,
                retry_count=self.request.retries + 1,
            )
            raise self.retry(exc=e)
        raise TaskError(
            "Unexpected error during test case generation",
            details={"task_id": self.request.id, "error": str(e)},
        )


# Register task with celery_app to avoid circular import
# Import here after function definition
from app.tasks.celery_app import celery_app

# Register the task with Celery
# Using explicit name to ensure it's registered correctly
generate_test_case_task = celery_app.task(
    name="generate_test_case",
    bind=True,
    base=ProgressTrackingTask,
    max_retries=3,
    default_retry_delay=60,
)(generate_test_case_task)

# Verify task is registered
if hasattr(celery_app, 'tasks') and 'generate_test_case' in celery_app.tasks:
    logger.info("Task 'generate_test_case' successfully registered")
else:
    logger.warning("Task 'generate_test_case' may not be registered correctly")

# Export the registered task
__all__ = ["generate_test_case_task"]

