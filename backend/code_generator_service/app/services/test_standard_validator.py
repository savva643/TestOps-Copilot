"""Validator for test-case code against AAA and labeling standards."""

import re
from typing import List


def validate_test_standard(code: str) -> List[str]:
    issues: List[str] = []

    # AAA keywords
    for marker in ("Arrange", "Act", "Assert"):
        if marker.lower() not in code.lower():
            issues.append(f"Отсутствует секция {marker}")

    # Required labels in code
    required_labels = ["owner", "priority", "feature", "story"]
    for label in required_labels:
        if f'@allure.label("{label}"' not in code:
            issues.append(f'Отсутствует allure.label("{label}")')

    # Priority tag
    if not re.search(r"@allure\.tag\([\"'](CRITICAL|NORMAL|LOW)", code):
        issues.append("Не указана приоритетная метка @allure.tag")

    return issues

