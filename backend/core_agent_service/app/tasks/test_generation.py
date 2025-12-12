"""Celery tasks for test generation."""

from typing import Optional, Dict, Any
import structlog
from celery import Task
from app.services.llm_client import LLMClient
from app.services.prompt_engineer import PromptEngineer, PromptValidationError
from app.services.standard_validator import StandardValidator
from app.core.exceptions import LLMError, TaskError

logger = structlog.get_logger()


def filter_english_thinking_text(text: str) -> str:
    """
    Удаляет английский текст-раздумывание в начале объяснения.
    Фильтрует фразы типа "We need to produce...", "Let's create...", "I'll generate..." и т.д.
    Для manual тестов также ищет начало тест-кейса (# ТЕСТ-КЕЙС:).
    """
    if not text:
        return text
    
    # Для manual тестов: ищем начало тест-кейса
    import re
    tc_match = re.search(r'#\s*ТЕСТ-КЕЙС:', text, re.IGNORECASE)
    if tc_match:
        # Если нашли тест-кейс, берем текст начиная с него
        text = text[tc_match.start():]
    
    # Паттерны английского раздумывания
    english_starters = [
        "we need to",
        "let's",
        "i'll",
        "i will",
        "we should",
        "we can",
        "we will",
        "let me",
        "i need to",
        "we must",
        "i should",
        "i can",
        "i'm going to",
        "we're going to",
        "here is",
        "this is",
        "will output",
        "should output",
        "must include",
    ]
    
    lines = text.split('\n')
    filtered_lines = []
    skip_until_markdown = False
    
    for i, line in enumerate(lines):
        line_lower = line.strip().lower()
        
        # Пропускаем пустые строки в начале
        if not line_lower and not filtered_lines:
            continue
        
        # Проверяем, начинается ли строка с английского раздумывания
        starts_with_thinking = any(line_lower.startswith(starter) for starter in english_starters)
        
        # Если это английское раздумывание, пропускаем до первого markdown заголовка или русского текста
        if starts_with_thinking:
            skip_until_markdown = True
            continue
        
        # Если мы пропускаем, ищем первый markdown заголовок (#) или русский текст
        if skip_until_markdown:
            # Проверяем, является ли строка markdown заголовком
            if line.strip().startswith('#'):
                skip_until_markdown = False
                filtered_lines.append(line)
            # Проверяем, есть ли в строке кириллица (русский текст)
            elif any('\u0400' <= char <= '\u04FF' for char in line):
                skip_until_markdown = False
                filtered_lines.append(line)
            # Пропускаем строку, если она не содержит кириллицу и не является заголовком
            continue
        
        # Добавляем строку, если мы не в режиме пропуска
        filtered_lines.append(line)
    
    result = '\n'.join(filtered_lines).strip()
    
    # Если после фильтрации остался только английский текст, возвращаем исходный
    # (на случай, если весь текст был на английском, но не был раздумыванием)
    if not result:
        return text
    
    return result


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

        def is_valid_python_code(code: str) -> bool:
            """Проверяет, является ли текст валидным Python кодом, а не объяснениями."""
            if not code or len(code.strip()) < 20:
                return False
            
            code_lower = code.lower()
            
            # Проверяем наличие обязательных Python конструкций
            has_import = 'import ' in code or 'from ' in code
            has_def_or_class = 'def ' in code or 'class ' in code or '@' in code
            has_pytest_markers = '@pytest' in code or '@allure' in code
            
            # Проверяем, что это не просто объяснения на английском
            # Если текст начинается с "we need", "let's", "i'll" и т.д. - это не код
            explanation_starters = [
                'we need', 'we must', 'we should', 'let\'s', 'let us',
                'i\'ll', 'i will', 'i need', 'i must', 'here is',
                'this is', 'the code', 'the test', 'will produce',
                'should output', 'must include', 'need to'
            ]
            first_lines = '\n'.join(code.splitlines()[:3]).lower()
            if any(first_lines.startswith(starter) for starter in explanation_starters):
                return False
            
            # Если есть import/from И (def/class/@pytest/@allure), то это код
            if has_import and (has_def_or_class or has_pytest_markers):
                return True
            
            # Если есть def или class с правильным синтаксисом
            if has_def_or_class:
                # Проверяем, что после def/class идет имя функции/класса
                import re
                if re.search(r'\bdef\s+\w+', code) or re.search(r'\bclass\s+\w+', code):
                    return True
            
            # Если есть декораторы pytest/allure
            if has_pytest_markers:
                return True
            
            return False

        def has_code(txt: str) -> bool:
            """Проверяет, есть ли в тексте код (markdown блоки или import/from).
            
            Учитывает, что ответ может содержать markdown объяснения перед кодом.
            """
            # Сначала проверяем наличие блоков кода в markdown
            code_blocks = extract_code_blocks_from_markdown(txt)
            if code_blocks:
                # Проверяем, что извлеченный код действительно валидный Python код
                for block in code_blocks:
                    code = block.get("code", "")
                    if code and is_valid_python_code(code):
                        return True
            
            # Ищем import/from в любой строке, не только в начале
            lines = txt.splitlines()
            for line in lines:
                stripped = line.lstrip()
                if stripped.startswith("import ") or stripped.startswith("from "):
                    # Проверяем, что дальше есть реальный код
                    code_start = txt.find(line)
                    code_snippet = txt[code_start:code_start+500]  # Берем следующий фрагмент
                    if is_valid_python_code(code_snippet):
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
                        # Проверяем валидность кода вокруг ключевого слова
                        code_snippet = txt[max(0, keyword_pos-100):keyword_pos+500]
                        if is_valid_python_code(code_snippet):
                            return True
            return False

        # Для API/UI используем двухэтапный подход: сначала код, потом объяснение
        if test_type in ["api", "ui"]:
            logger.info(
                "Using two-step approach for API/UI tests: generate code first, then explanation",
                task_id=self.request.id,
            )
            
            # Этап 1: Генерируем только код (максимально строгий промпт)
            self.update_progress(40, 100, "Generating Python code...")
            
            code_system_prompt = """Ты — генератор Python-кода тестов в формате Allure TestOps as Code. Твоя ЕДИНСТВЕННАЯ задача — вернуть готовый код.

КРИТИЧЕСКИ ВАЖНО:
- Твой ответ ДОЛЖЕН начинаться СРАЗУ с ```python (без единого символа перед ним)
- ЗАПРЕЩЕНО писать: 'We need to...', 'We must...', 'Let's create...', 'I'll generate...', 'Here is...'
- ЗАПРЕЩЕНО писать планы действий или описания
- Пиши ТОЛЬКО готовый код на Python внутри блока ```python ... ```

Формат ответа (СТРОГО):
```python
import pytest
# ... готовый код ...
```

НИКАКИХ объяснений перед блоком кода. НИКАКИХ планов. ТОЛЬКО КОД."""
            
            code_user_prompt = (
                "КРИТИЧЕСКИ ВАЖНО: Твой ответ ДОЛЖЕН начинаться СРАЗУ с ```python (без единого символа перед ним).\n"
                "ЗАПРЕЩЕНО писать:\n"
                "- 'We need to...', 'We must...', 'We should...'\n"
                "- 'Let's create...', 'Let us...'\n"
                "- 'I'll generate...', 'I will...', 'I need...'\n"
                "- 'Here is...', 'This is...', 'The code...'\n"
                "- 'Will produce...', 'Should output...', 'Must include...'\n"
                "- Любые планы действий или описания того, что ты собираешься сделать\n\n"
                "ТВОЙ ОТВЕТ ДОЛЖЕН БЫТЬ ТОЛЬКО:\n"
                "```python\n"
                "import pytest\n"
                "# ... готовый код ...\n"
                "```\n\n"
                "НИКАКИХ объяснений перед блоком кода. НИКАКИХ планов. ТОЛЬКО КОД.\n\n"
                + user_prompt
            )
            
            code_response = loop.run_until_complete(
                llm_client.generate(
                    system_prompt=code_system_prompt,
                    user_prompt=code_user_prompt,
                )
            )
            
            # Извлекаем код
            code_extracted = extract_code_from_text(code_response)
            if not code_extracted or not code_extracted.get("files"):
                # Если не удалось извлечь, пробуем еще раз
                logger.warning(
                    "Failed to extract code, retrying with even stricter prompt",
                    task_id=self.request.id,
                )
                code_response = loop.run_until_complete(
                    llm_client.generate(
                        system_prompt="Ты генератор Python кода. Верни ТОЛЬКО код, начиная с ```python. Без объяснений.",
                        user_prompt=f"```python\n{user_prompt}\n\nВерни ТОЛЬКО код Python внутри блока ```python ... ```. БЕЗ объяснений.",
                    )
                )
                code_extracted = extract_code_from_text(code_response)
            
            if not code_extracted or not code_extracted.get("files"):
                raise LLMError(
                    "Failed to generate Python code",
                    details={"reason": "Could not extract code from LLM response"},
                )
            
            # Проверяем валидность кода
            valid_code_files = []
            for f in code_extracted["files"]:
                code = f.get("code", "")
                if code and len(code.strip()) > 50 and is_valid_python_code(code):
                    valid_code_files.append(f)
            
            if not valid_code_files:
                raise LLMError(
                    "Generated code is not valid Python code",
                    details={"reason": "LLM returned text that is not valid Python code"},
                )
            
            logger.info(
                "Code generated successfully, now generating explanation",
                task_id=self.request.id,
                files_count=len(valid_code_files),
            )
            
            # Этап 2: Генерируем объяснение для кода
            self.update_progress(60, 100, "Generating explanation...")
            
            # Берем первый файл с кодом для объяснения
            main_code = valid_code_files[0]['code']
            
            explanation_prompt = f"""Объясни на русском языке следующий тестовый код:

```python
{main_code[:3000]}
```

Объясни подробно в формате Markdown:
1. **Описание функциональности** - что тестирует этот код
2. **Типы проверок** - какие проверки выполняются (статус коды, валидация данных, обработка ошибок и т.д.)
3. **Структура тестов** - какие тесты содержатся, их назначение
4. **Используемые библиотеки и инструменты** - pytest, httpx/allure и т.д.
5. **Как использовать** - как запустить эти тесты

Используй заголовки, списки, таблицы для структурирования информации.

ВАЖНО: Начни ответ СРАЗУ с заголовка или русского текста. НЕ пиши английские фразы типа "We need to...", "Let's create...", "I'll generate..." в начале ответа."""
            
            explanation_response = loop.run_until_complete(
                llm_client.generate(
                    system_prompt="Ты помощник, объясняющий тестовый код. Объясни код на русском языке в формате Markdown с заголовками, списками и структурированной информацией. НЕ пиши английские фразы-раздумывания в начале ответа. Начинай сразу с русского текста или заголовка Markdown.",
                    user_prompt=explanation_prompt,
                )
            )
            
            # Добавляем объяснение как description к файлам с кодом
            if explanation_response:
                explanation_text = explanation_response.strip()
                # Фильтруем английский текст-раздумывание в начале
                explanation_text = filter_english_thinking_text(explanation_text)
                for f in valid_code_files:
                    # Добавляем объяснение к каждому файлу (или только к первому)
                    if not f.get("description"):
                        f["description"] = explanation_text
            
            # Сохраняем результат
            generated_text = {
                "files": valid_code_files,
                "raw_response": code_response
            }
            
            logger.info(
                "Successfully generated code and explanation using two-step approach",
                task_id=self.request.id,
                files_count=len(valid_code_files),
            )
        
        else:
            # Для manual тестов используем обычный подход
            generated_text = loop.run_until_complete(
                llm_client.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                )
            )

        # Для API/UI тестов код уже сгенерирован в двухэтапном подходе выше
        # Для manual тестов обрабатываем ответ
        
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
            # Для manual тестов фильтруем английский текст-раздумывание и проверяем формат
            import re
            
            # Фильтруем английский текст-раздумывание в начале
            filtered_text = filter_english_thinking_text(generated_text)
            
            # Проверяем, что ответ начинается с тест-кейса
            # Если нет, пытаемся найти начало тест-кейса в тексте
            if not filtered_text.strip().startswith("# ТЕСТ-КЕЙС:"):
                # Ищем начало тест-кейса в тексте
                tc_match = re.search(r'#\s*ТЕСТ-КЕЙС:', filtered_text, re.IGNORECASE)
                if tc_match:
                    # Берем текст начиная с найденного тест-кейса
                    filtered_text = filtered_text[tc_match.start():]
                else:
                    # Если не нашли, проверяем, может быть это описание на английском
                    # И ищем паттерны типа "We need to output..."
                    english_thinking_patterns = [
                        r'^[^#]*?(?=#\s*ТЕСТ-КЕЙС:)',  # Текст до тест-кейса
                        r'^We\s+need\s+to[^#]*',  # "We need to..."
                        r'^Let\'?s\s+[^#]*',  # "Let's..."
                        r'^I\'?ll\s+[^#]*',  # "I'll..."
                        r'^Here\s+is[^#]*',  # "Here is..."
                    ]
                    for pattern in english_thinking_patterns:
                        filtered_text = re.sub(pattern, '', filtered_text, flags=re.IGNORECASE | re.DOTALL)
                    filtered_text = filtered_text.strip()
            
            # Если после фильтрации текст пустой или слишком короткий, используем оригинал
            if not filtered_text or len(filtered_text.strip()) < 50:
                logger.warning(
                    "Filtered text is too short, using original",
                    task_id=self.request.id,
                    filtered_length=len(filtered_text) if filtered_text else 0,
                )
                filtered_text = generated_text
            
            # Генерируем имя файла с ID из текста или используем дефолтное
            tc_id_match = re.search(r'\*\*ID:\*\*\s*(TC-\d+)', filtered_text)
            tc_id = tc_id_match.group(1) if tc_id_match else "TC-001"
            filename = f"manual_test_case_{tc_id}.txt"
            
            test_case_data = {
                "files": [{
                    "description": None,
                    "code": filtered_text,
                    "filename": filename
                }],
                "raw_response": generated_text  # Сохраняем оригинальный ответ для отладки
            }
        else:
            test_case_data = generated_text
            # Для API/UI тестов добавляем файл с объяснениями
            if test_type in ["api", "ui"] and isinstance(test_case_data, dict) and test_case_data.get("files"):
                # Берем объяснение из description первого файла (если есть - сгенерировано в двухэтапном подходе)
                llm_explanation = None
                if test_case_data["files"] and test_case_data["files"][0].get("description"):
                    llm_explanation = test_case_data["files"][0]["description"]
                    # Фильтруем английский текст-раздумывание
                    llm_explanation = filter_english_thinking_text(llm_explanation)
                
                # Генерируем техническое объяснение
                technical_explanation = generate_explanation_md(
                    test_type=test_type,
                    feature=feature,
                    story=story,
                    files=test_case_data["files"],
                    validation_result=validation_result
                )
                
                # Объединяем объяснение от LLM с техническим объяснением
                if llm_explanation:
                    # Если есть объяснение от LLM, используем его как основу и добавляем техническую информацию
                    combined_explanation = f"{llm_explanation}\n\n---\n\n## Техническая информация\n\n{technical_explanation}"
                else:
                    # Если нет объяснения от LLM, используем только техническое
                    combined_explanation = technical_explanation
                
                # Добавляем файл с объяснениями в начало списка файлов
                test_case_data["files"].insert(0, {
                    "description": "Документация с объяснениями фич и типов проверок",
                    "code": combined_explanation,
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

