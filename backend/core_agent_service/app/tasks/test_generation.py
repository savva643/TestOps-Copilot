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
            
            Returns:
                List of dicts: [{"description": "...", "code": "..."}, ...]
            """
            import re
            # Ищем все блоки кода: ```python ... ``` или ``` ... ```
            pattern = r'```(?:python)?\s*\n(.*?)\n```'
            code_matches = list(re.finditer(pattern, txt, re.DOTALL))
            
            files = []
            last_end = 0
            
            for i, match in enumerate(code_matches):
                # Текст перед этим блоком кода - описание
                description_start = last_end
                description_end = match.start()
                description = txt[description_start:description_end].strip()
                
                code = match.group(1).strip()
                
                files.append({
                    "description": description if description else None,
                    "code": code,
                    "filename": f"test_{i+1}.py" if len(code_matches) > 1 else "test.py"
                })
                
                last_end = match.end()
            
            # Если есть текст после последнего блока кода
            if last_end < len(txt):
                remaining = txt[last_end:].strip()
                if remaining:
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
            
            # Если нет markdown блоков, ищем код, начинающийся с import/from
            lines = txt.splitlines()
            code_start_idx = None
            for i, line in enumerate(lines):
                stripped_line = line.lstrip()
                if stripped_line.startswith("import ") or stripped_line.startswith("from "):
                    code_start_idx = i
                    break
            
            if code_start_idx is not None:
                description = "\n".join(lines[:code_start_idx]).strip() if code_start_idx > 0 else None
                code = "\n".join(lines[code_start_idx:]).strip()
                return {
                    "files": [{
                        "description": description,
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
            """Проверяет, есть ли в тексте код (markdown блоки или import/from)."""
            code_blocks = extract_code_blocks_from_markdown(txt)
            if code_blocks:
                return True
            stripped = txt.lstrip()
            return stripped.startswith("import ") or stripped.startswith("from ")

        # Первичная генерация
        generated_text = loop.run_until_complete(
            llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        )

        # Для API/UI извлекаем код из ответа (может быть в markdown блоках или как чистый код)
        if test_type in ["api", "ui"]:
            if not has_code(generated_text):
                # Логируем первые 200 символов для отладки
                preview = generated_text[:200].replace("\n", "\\n")
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
                
                if not has_code(generated_text):
                    raise LLMError(
                        "Invalid response from LLM API",
                        details={"reason": "expected code in markdown blocks or starting with import/from"},
                    )
            
            # Извлекаем код из ответа (может быть несколько файлов)
            extracted = extract_code_from_text(generated_text)
            if extracted and extracted.get("files"):
                logger.info(
                    "Extracted code files from LLM response",
                    task_id=self.request.id,
                    files_count=len(extracted["files"]),
                )
                # Сохраняем структурированный ответ
                generated_text = extracted
            else:
                # Fallback: сохраняем как один файл
                generated_text = {
                    "files": [{
                        "description": None,
                        "code": generated_text,
                        "filename": "test.py"
                    }],
                    "raw_response": generated_text
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

