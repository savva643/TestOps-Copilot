"""Lightweight validator for generated test code."""

import re
from typing import List


def validate_allure_contract(code: str) -> List[str]:
    """
    Validate that generated code satisfies minimal Allure/TestOps requirements.

    Checks:
    - Presence of allure imports and annotations (@allure.*)
    - AAA pattern markers (Arrange/Act/Assert or step sections)
    - Required labels: owner, priority, feature, story, suite
    """
    issues: List[str] = []

    if "import allure" not in code:
        issues.append("Отсутствует import allure")

    required_labels = ["owner", "priority", "feature", "story", "suite"]
    for label in required_labels:
        if f'@allure.label("{label}"' not in code and f"@allure.{label}" not in code:
            issues.append(f'Отсутствует метка allure "{label}"')

    if "@allure.manual" not in code and "@pytest.mark.manual" not in code:
        # optional for non-manual, but we flag if neither manual marker found
        issues.append("Не указан тип теста (@allure.manual / @pytest.mark.manual)")

    aaa_markers = ["Arrange", "Act", "Assert"]
    if not all(marker.lower() in code.lower() for marker in aaa_markers):
        issues.append("Не найден AAA паттерн (Arrange/Act/Assert)")

    if not re.search(r"@allure\.tag\([\"'](CRITICAL|NORMAL|LOW)", code):
        issues.append("Не указана метка приоритета @allure.tag")

    return issues

