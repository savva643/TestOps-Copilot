"""Проверка тест-кейсов на соответствие стандартам Allure TestOps as Code."""

import re
from typing import Dict, List, Any
import structlog

logger = structlog.get_logger()


class StandardValidator:
    """Валидатор соответствия тест-кейсов стандартам."""

    def validate_test_case(self, code: str, test_type: str) -> Dict[str, Any]:
        """
        Проверяет тест-кейс на соответствие принятым стандартам.

        Args:
            code: Код тест-кейса
            test_type: Тип теста (manual/api/ui)

        Returns:
            dict с результатами валидации:
            {
                "is_valid": bool,
                "errors": [str],      # Критические ошибки
                "warnings": [str],    # Предупреждения
                "score": int,          # Оценка 0-100
                "recommendations": [str]  # Рекомендации по улучшению
            }
        """
        errors: List[str] = []
        warnings: List[str] = []
        recommendations: List[str] = []

        if test_type == "manual":
            return self._validate_manual_test(code)
        elif test_type in ["api", "ui"]:
            return self._validate_code_test(code, test_type)
        else:
            return {
                "is_valid": False,
                "errors": [f"Unknown test_type: {test_type}"],
                "warnings": [],
                "score": 0,
                "recommendations": [],
            }

    def _validate_manual_test(self, code: str) -> Dict[str, Any]:
        """Валидация ручного тест-кейса."""
        errors: List[str] = []
        warnings: List[str] = []
        recommendations: List[str] = []
        score = 100

        # Проверка наличия структуры
        if not code or not code.strip():
            errors.append("Тест-кейс пустой")
            score = 0
            return self._build_result(errors, warnings, score, recommendations)

        # Проверка наличия шагов
        if "шаг" not in code.lower() and "step" not in code.lower():
            warnings.append("Не найдены явные шаги теста (рекомендуется нумерация)")
            score -= 10

        # Проверка наличия ожидаемых результатов
        if "ожидаемый" not in code.lower() and "expected" not in code.lower():
            warnings.append("Не найдены ожидаемые результаты")
            score -= 10

        # Проверка наличия тестовых данных
        if "данные" not in code.lower() and "data" not in code.lower():
            warnings.append("Не указаны тестовые данные")
            score -= 5

        score = max(0, score)

        return self._build_result(errors, warnings, score, recommendations)

    def _validate_code_test(self, code: str, test_type: str) -> Dict[str, Any]:
        """Валидация автоматизированного теста (API/UI)."""
        errors: List[str] = []
        warnings: List[str] = []
        recommendations: List[str] = []
        score = 100

        if not code or not code.strip():
            errors.append("Код теста пустой")
            score = 0
            return self._build_result(errors, warnings, score, recommendations)

        # Проверка обязательных импортов
        required_imports = {
            "api": ["pytest", "httpx", "allure"],
            "ui": ["pytest", "playwright", "allure"],
        }
        for imp in required_imports.get(test_type, []):
            if imp not in code.lower():
                errors.append(f"Отсутствует обязательный импорт: {imp}")
                score -= 20

        # Проверка обязательных Allure декораторов
        required_decorators = [
            r'@allure\.label\s*\(\s*["\']owner["\']',
            r'@allure\.suite\s*\(',
            r'@allure\.tag\s*\(',
            r'@allure\.label\s*\(\s*["\']priority["\']',
            r'@allure\.title\s*\(',
        ]

        for decorator_pattern in required_decorators:
            if not re.search(decorator_pattern, code, re.IGNORECASE):
                errors.append(f"Отсутствует обязательный декоратор: {decorator_pattern}")
                score -= 15

        # Проверка опциональных декораторов
        optional_decorators = [
            (r'@allure\.feature\s*\(', "Рекомендуется добавить @allure.feature()"),
            (r'@allure\.story\s*\(', "Рекомендуется добавить @allure.story()"),
            (r'@allure\.link\s*\(', "Рекомендуется добавить @allure.link() для JIRA"),
        ]

        for decorator_pattern, message in optional_decorators:
            if not re.search(decorator_pattern, code, re.IGNORECASE):
                recommendations.append(message)
                score -= 5

        # Проверка паттерна AAA
        aaa_pattern = r"#\s*(Arrange|Act|Assert)"
        if not re.search(aaa_pattern, code, re.IGNORECASE):
            warnings.append("Не найдена структура AAA (комментарии # Arrange, # Act, # Assert)")
            score -= 10

        # Проверка наличия тестовых функций
        test_functions = re.findall(r'def\s+test_\w+', code, re.IGNORECASE)
        if not test_functions:
            errors.append("Не найдено ни одной тестовой функции (test_*)")
            score -= 30

        # Проверка приоритетов (должны быть CRITICAL, NORMAL, LOW)
        priority_pattern = r'@allure\.tag\s*\(\s*["\']([^"\']+)["\']'
        priorities = re.findall(priority_pattern, code, re.IGNORECASE)
        valid_priorities = ["CRITICAL", "NORMAL", "LOW"]
        for priority in priorities:
            if priority.upper() not in valid_priorities:
                errors.append(
                    f"Недопустимый приоритет: {priority}. Допустимые: {valid_priorities}"
                )
                score -= 10

        # Проверка использования severity вместо tag
        if re.search(r'@allure\.severity\s*\(', code, re.IGNORECASE):
            errors.append(
                "Использован @allure.severity() вместо @allure.tag(). "
                "По ТЗ нужно использовать @allure.tag() с приоритетами CRITICAL/NORMAL/LOW"
            )
            score -= 15

        # Проверка для API тестов
        if test_type == "api":
            if "AsyncClient" not in code and "httpx" in code.lower():
                warnings.append("Рекомендуется использовать httpx.AsyncClient для асинхронных запросов")
                score -= 5

            if "Bearer" not in code and "Authorization" not in code:
                warnings.append("Не найдена авторизация через Bearer token")
                score -= 5

        # Проверка для UI тестов
        if test_type == "ui":
            if "page" not in code.lower() and "browser" not in code.lower():
                warnings.append("Не найдено использование page или browser объектов Playwright")
                score -= 5

        score = max(0, score)

        return self._build_result(errors, warnings, score, recommendations)

    def _build_result(
        self,
        errors: List[str],
        warnings: List[str],
        score: int,
        recommendations: List[str],
    ) -> Dict[str, Any]:
        """Формирует итоговый результат валидации."""
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "score": score,
            "recommendations": recommendations,
        }

