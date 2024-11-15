from io import StringIO

import math
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Optional, Literal
from enum import Enum

from benchmark.models import Testcase, Response


class PermissionComparison(Enum):
    OR_HIGHER = "or_higher"
    OR_LOWER = "or_lower"
    EXACT = "exact"
    NONE = "none"
    MISSING_OK = "missing_ok"


ACCESS_LEVELS = {
    "Guest": 10,
    "Reporter": 20,
    "Developer": 30,
    "Maintainer": 40,
    "Owner": 50,
}


@dataclass
class PermissionRule:
    username: str
    group: str
    permission: Optional[str]
    comparison: PermissionComparison

    def __str__(self) -> str:
        if self.comparison == PermissionComparison.NONE:
            return f"{self.username} should have no entry for {self.group}"
        elif self.comparison == PermissionComparison.MISSING_OK:
            return f"{self.username} can either be missing or have {self.permission} or lower in {self.group}"  # Updated description

        permission_str = self.permission or "None"
        if self.comparison == PermissionComparison.OR_HIGHER:
            return f"{self.username} needs {permission_str} or higher in {self.group}"
        elif self.comparison == PermissionComparison.OR_LOWER:
            return f"{self.username} needs {permission_str} or lower in {self.group}"
        else:
            return f"{self.username} needs exactly {permission_str} in {self.group}"


def check_permission_level(actual: Optional[str], required: Optional[str],
                           comparison: PermissionComparison) -> bool:
    """
    Check if permission meets the required level based on comparison type

    Args:
        actual: Actual permission level (or None if entry doesn't exist)
        required: Required permission level
        comparison: Type of comparison to perform
    """
    # Handle cases where entry doesn't exist
    if actual is None:
        return comparison in [PermissionComparison.NONE, PermissionComparison.MISSING_OK]

    # Entry exists when it shouldn't
    if comparison == PermissionComparison.NONE:
        return False

    actual_level = ACCESS_LEVELS.get(actual, 0)
    required_level = ACCESS_LEVELS.get(required, 0)

    if comparison == PermissionComparison.OR_HIGHER:
        return actual_level >= required_level
    elif comparison == PermissionComparison.OR_LOWER:
        return actual_level <= required_level
    elif comparison == PermissionComparison.MISSING_OK:
        return actual_level <= required_level  # Changed to allow equal or lower permissions
    else:  # EXACT
        return actual_level == required_level


def verify(testcase: Testcase, response: Response) -> int:
    try:
        response_file = StringIO(response.response_file)
        df = pd.read_csv(response_file, sep=";", names=['Username', 'Group', 'Permission'])
    except Exception as e:
        response.set_check_result(f"# Permissions\n- CSV parsing failed: {str(e)}")
        return 0
    response.set_valid(True)

    score = 0
    issues = []

    permission_rules = create_permission_rules()

    for rule in permission_rules:
        matches = df[
            (df['Username'] == rule.username) &
            (df['Group'] == rule.group)
            ]

        # Handle non-existent entries
        if matches.empty:
            if rule.comparison in [PermissionComparison.NONE, PermissionComparison.MISSING_OK]:
                score += 1
            else:
                issues.append(f"- Missing required permission: {str(rule)}")
            continue

        # Handle existing entries
        if rule.comparison == PermissionComparison.NONE:
            issues.append(f"- {rule.username} should not have any entry for {rule.group}")
            continue

        for _, row in matches.iterrows():
            if check_permission_level(row['Permission'], rule.permission, rule.comparison):
                score += 1
            else:
                issues.append(f"- Invalid permission: {row['Username']} has {row['Permission']} "
                              f"in {row['Group']}, but {str(rule)}")

    issue_text = "\n".join(issues) if issues else "- All permissions are correct"
    response.set_check_result(f"# Permissions\n{issue_text}")

    score = (score / len(permission_rules)) * 100
    return math.floor(score)


def check_permissions(df: pd.DataFrame, rules: List[PermissionRule]) -> List[str]:
    """
    Verify all permission rules against the data
    """
    issues = []

    for rule in rules:
        matches = df[
            (df['Username'] == rule.username) &
            (df['Group'] == rule.group)
            ]

        # Handle missing entries
        if matches.empty:
            if rule.comparison not in [PermissionComparison.NONE, PermissionComparison.MISSING_OK]:
                issues.append(f"Missing required permission: {str(rule)}")
            continue

        # Handle existing entries
        if rule.comparison == PermissionComparison.NONE:
            issues.append(f"{rule.username} should not have any entry for {rule.group}")
            continue

        for _, row in matches.iterrows():
            if not check_permission_level(row['Permission'], rule.permission, rule.comparison):
                issues.append(
                    f"Invalid permission: {rule.username} has {row['Permission']} "
                    f"in {rule.group}, but {str(rule)}"
                )

    return issues


def create_permission_rules():
    return [
        # RZ001/RZ005 - System Administrators
        PermissionRule("rz001", "Webentwicklung", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("rz001", "Appentwicklung", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("rz001", "Integration", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("rz001", "Infrastruktur", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("rz001", "Netzwerk", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("rz001", "Server", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("rz001", "Reporting", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("rz001", "Finanzen", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("rz001", "Metriken", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("rz005", "Webentwicklung", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("rz005", "Appentwicklung", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("rz005", "Integration", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("rz005", "Infrastruktur", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("rz005", "Netzwerk", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("rz005", "Server", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("rz005", "Reporting", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("rz005", "Finanzen", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("rz005", "Metriken", "Maintainer", PermissionComparison.OR_HIGHER),

        # RZ002/RZ004 - Server Managers
        PermissionRule("rz002", "Infrastruktur", "Reporter", PermissionComparison.OR_LOWER),
        PermissionRule("rz002", "Server", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("rz002", "Netzwerk", "Reporter", PermissionComparison.MISSING_OK),
        PermissionRule("rz002", "Webentwicklung", None, PermissionComparison.NONE),
        PermissionRule("rz002", "Appentwicklung", None, PermissionComparison.NONE),
        PermissionRule("rz002", "Integration", None, PermissionComparison.NONE),
        PermissionRule("rz002", "Reporting", None, PermissionComparison.NONE),
        PermissionRule("rz002", "Finanzen", None, PermissionComparison.NONE),
        PermissionRule("rz002", "Metriken", None, PermissionComparison.NONE),
        PermissionRule("rz004", "Infrastruktur", "Reporter", PermissionComparison.OR_LOWER),
        PermissionRule("rz004", "Server", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("rz004", "Netzwerk", "Reporter", PermissionComparison.MISSING_OK),
        PermissionRule("rz004", "Webentwicklung", None, PermissionComparison.NONE),
        PermissionRule("rz004", "Appentwicklung", None, PermissionComparison.NONE),
        PermissionRule("rz004", "Integration", None, PermissionComparison.NONE),
        PermissionRule("rz004", "Reporting", None, PermissionComparison.NONE),
        PermissionRule("rz004", "Finanzen", None, PermissionComparison.NONE),
        PermissionRule("rz004", "Metriken", None, PermissionComparison.NONE),

        # RZ003 - Network Manager
        PermissionRule("rz003", "Infrastruktur", "Reporter", PermissionComparison.OR_LOWER),
        PermissionRule("rz003", "Network", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("rz004", "Server", "Reporter", PermissionComparison.MISSING_OK),
        PermissionRule("rz004", "Webentwicklung", None, PermissionComparison.NONE),
        PermissionRule("rz004", "Appentwicklung", None, PermissionComparison.NONE),
        PermissionRule("rz004", "Integration", None, PermissionComparison.NONE),
        PermissionRule("rz004", "Reporting", None, PermissionComparison.NONE),
        PermissionRule("rz004", "Finanzen", None, PermissionComparison.NONE),
        PermissionRule("rz004", "Metriken", None, PermissionComparison.NONE),

        # DEV001 - Lead Developer, DevOps Lead
        PermissionRule("dev001", "Webentwicklung", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("dev001", "Appentwicklung", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("dev001", "Integration", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("dev001", "Finanzen", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("dev001", "Metriken", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("dev001", "Infrastruktur", None, PermissionComparison.NONE),
        PermissionRule("dev001", "Server", None, PermissionComparison.NONE),
        PermissionRule("dev001", "Network", None, PermissionComparison.NONE),

        # DEV002 - Lead Developer Appentwicklung
        PermissionRule("dev002", "Appentwicklung", "Owner", PermissionComparison.EXACT),
        PermissionRule("dev001", "Integration", "Reporter", PermissionComparison.EXACT),
        PermissionRule("dev002", "Webentwicklung", None, PermissionComparison.NONE),
        PermissionRule("dev002", "Reporting", None, PermissionComparison.NONE),
        PermissionRule("dev002", "Finanzen", None, PermissionComparison.NONE),
        PermissionRule("dev002", "Metriken", None, PermissionComparison.NONE),
        PermissionRule("dev002", "Infrastruktur", None, PermissionComparison.NONE),
        PermissionRule("dev002", "Server", None, PermissionComparison.NONE),
        PermissionRule("dev002", "Network", None, PermissionComparison.NONE),

        # DEV003/DEV004 - Lead Developers
        PermissionRule("dev003", "Webentwicklung", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("dev003", "Appentwicklung", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("dev003", "Integration", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("dev003", "Reporting", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("dev003", "Finanzen", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("dev003", "Metriken", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("dev003", "Infrastruktur", None, PermissionComparison.NONE),
        PermissionRule("dev003", "Server", None, PermissionComparison.NONE),
        PermissionRule("dev003", "Network", None, PermissionComparison.NONE),
        PermissionRule("dev004", "Webentwicklung", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("dev004", "Appentwicklung", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("dev004", "Integration", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("dev004", "Reporting", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("dev004", "Finanzen", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("dev004", "Metriken", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("dev004", "Infrastruktur", None, PermissionComparison.NONE),
        PermissionRule("dev004", "Server", None, PermissionComparison.NONE),
        PermissionRule("dev004", "Network", None, PermissionComparison.NONE),

        # DEV005 - Lead Developer with different permissions
        PermissionRule("dev005", "Integration", "Reporter", PermissionComparison.EXACT),
        PermissionRule("dev005", "Reporting", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("dev005", "Finanzen", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("dev005", "Metriken", "Maintainer", PermissionComparison.OR_HIGHER),
        PermissionRule("dev005", "Webentwicklung", None, PermissionComparison.NONE),
        PermissionRule("dev005", "Appentwicklung", None, PermissionComparison.NONE),
        PermissionRule("dev005", "Infrastruktur", None, PermissionComparison.NONE),
        PermissionRule("dev005", "Server", None, PermissionComparison.NONE),
        PermissionRule("dev005", "Network", None, PermissionComparison.NONE),

        # DEV006-DEV010 - Developers in Webentwicklung
        PermissionRule("dev006", "Webentwicklung", "Developer", PermissionComparison.EXACT),
        PermissionRule("dev006", "Integration", "Reporter", PermissionComparison.EXACT),
        PermissionRule("dev006", "Appentwicklung", "Developer", PermissionComparison.EXACT),
        PermissionRule("dev006", "Reporting", None, PermissionComparison.NONE),
        PermissionRule("dev006", "Finanzen", None, PermissionComparison.NONE),
        PermissionRule("dev006", "Metriken", None, PermissionComparison.NONE),
        PermissionRule("dev006", "Infrastruktur", None, PermissionComparison.NONE),
        PermissionRule("dev006", "Server", None, PermissionComparison.NONE),
        PermissionRule("dev006", "Network", None, PermissionComparison.NONE),
        PermissionRule("dev007", "Webentwicklung", "Developer", PermissionComparison.EXACT),
        PermissionRule("dev007", "Integration", "Reporter", PermissionComparison.EXACT),
        PermissionRule("dev007", "Appentwicklung", "Developer", PermissionComparison.NONE),
        PermissionRule("dev007", "Reporting", None, PermissionComparison.NONE),
        PermissionRule("dev007", "Finanzen", None, PermissionComparison.NONE),
        PermissionRule("dev007", "Metriken", None, PermissionComparison.NONE),
        PermissionRule("dev007", "Infrastruktur", None, PermissionComparison.NONE),
        PermissionRule("dev007", "Server", None, PermissionComparison.NONE),
        PermissionRule("dev007", "Network", None, PermissionComparison.NONE),
        PermissionRule("dev008", "Webentwicklung", "Developer", PermissionComparison.EXACT),
        PermissionRule("dev008", "Integration", "Reporter", PermissionComparison.EXACT),
        PermissionRule("dev008", "Appentwicklung", "Developer", PermissionComparison.NONE),
        PermissionRule("dev008", "Reporting", None, PermissionComparison.NONE),
        PermissionRule("dev008", "Finanzen", None, PermissionComparison.NONE),
        PermissionRule("dev008", "Metriken", None, PermissionComparison.NONE),
        PermissionRule("dev008", "Infrastruktur", None, PermissionComparison.NONE),
        PermissionRule("dev008", "Server", None, PermissionComparison.NONE),
        PermissionRule("dev008", "Network", None, PermissionComparison.NONE),
        PermissionRule("dev009", "Webentwicklung", "Developer", PermissionComparison.EXACT),
        PermissionRule("dev009", "Integration", "Reporter", PermissionComparison.EXACT),
        PermissionRule("dev009", "Appentwicklung", "Developer", PermissionComparison.NONE),
        PermissionRule("dev009", "Reporting", None, PermissionComparison.NONE),
        PermissionRule("dev009", "Finanzen", None, PermissionComparison.NONE),
        PermissionRule("dev009", "Metriken", None, PermissionComparison.NONE),
        PermissionRule("dev009", "Infrastruktur", None, PermissionComparison.NONE),
        PermissionRule("dev009", "Server", None, PermissionComparison.NONE),
        PermissionRule("dev009", "Network", None, PermissionComparison.NONE),
        PermissionRule("dev010", "Webentwicklung", "Developer", PermissionComparison.EXACT),
        PermissionRule("dev010", "Integration", "Reporter", PermissionComparison.EXACT),
        PermissionRule("dev010", "Appentwicklung", "Developer", PermissionComparison.NONE),
        PermissionRule("dev010", "Reporting", None, PermissionComparison.NONE),
        PermissionRule("dev010", "Finanzen", None, PermissionComparison.NONE),
        PermissionRule("dev010", "Metriken", None, PermissionComparison.NONE),
        PermissionRule("dev010", "Infrastruktur", None, PermissionComparison.NONE),
        PermissionRule("dev010", "Server", None, PermissionComparison.NONE),
        PermissionRule("dev010", "Network", None, PermissionComparison.NONE),

        # DEV011-DEV013 - Developers in Finanzen
        PermissionRule("dev011", "Reporting", "Reporter", PermissionComparison.OR_LOWER),
        PermissionRule("dev011", "Finanzen", "Developer", PermissionComparison.EXACT),
        PermissionRule("dev011", "Integration", "Reporter", PermissionComparison.EXACT),
        PermissionRule("dev011", "Appentwicklung", None, PermissionComparison.NONE),
        PermissionRule("dev011", "Webentwicklung", None, PermissionComparison.EXACT),
        PermissionRule("dev011", "Metriken", "Reporter", PermissionComparison.MISSING_OK),
        PermissionRule("dev011", "Infrastruktur", None, PermissionComparison.NONE),
        PermissionRule("dev011", "Server", None, PermissionComparison.NONE),
        PermissionRule("dev011", "Network", None, PermissionComparison.NONE),
        PermissionRule("dev012", "Reporting", "Reporter", PermissionComparison.OR_LOWER),
        PermissionRule("dev012", "Finanzen", "Developer", PermissionComparison.EXACT),
        PermissionRule("dev012", "Integration", "Reporter", PermissionComparison.EXACT),
        PermissionRule("dev012", "Appentwicklung", None, PermissionComparison.NONE),
        PermissionRule("dev012", "Webentwicklung", None, PermissionComparison.EXACT),
        PermissionRule("dev012", "Metriken", "Reporter", PermissionComparison.MISSING_OK),
        PermissionRule("dev012", "Infrastruktur", None, PermissionComparison.NONE),
        PermissionRule("dev012", "Server", None, PermissionComparison.NONE),
        PermissionRule("dev012", "Network", None, PermissionComparison.NONE),
        PermissionRule("dev013", "Reporting", "Reporter", PermissionComparison.OR_LOWER),
        PermissionRule("dev013", "Finanzen", "Developer", PermissionComparison.EXACT),
        PermissionRule("dev013", "Integration", "Reporter", PermissionComparison.EXACT),
        PermissionRule("dev013", "Appentwicklung", None, PermissionComparison.NONE),
        PermissionRule("dev013", "Webentwicklung", None, PermissionComparison.EXACT),
        PermissionRule("dev013", "Metriken", "Reporter", PermissionComparison.MISSING_OK),
        PermissionRule("dev013", "Infrastruktur", None, PermissionComparison.NONE),
        PermissionRule("dev013", "Server", None, PermissionComparison.NONE),
        PermissionRule("dev013", "Network", None, PermissionComparison.NONE),

        # DEV014-DEV017 - Developers in Metriken
        PermissionRule("dev014", "Reporting", "Reporter", PermissionComparison.OR_LOWER),
        PermissionRule("dev014", "Metriken", "Developer", PermissionComparison.EXACT),
        PermissionRule("dev014", "Integration", "Reporter", PermissionComparison.EXACT),
        PermissionRule("dev014", "Appentwicklung", None, PermissionComparison.NONE),
        PermissionRule("dev014", "Webentwicklung", None, PermissionComparison.EXACT),
        PermissionRule("dev014", "Finanzen", "Reporter", PermissionComparison.MISSING_OK),
        PermissionRule("dev014", "Infrastruktur", None, PermissionComparison.NONE),
        PermissionRule("dev014", "Server", None, PermissionComparison.NONE),
        PermissionRule("dev014", "Network", None, PermissionComparison.NONE),
        PermissionRule("dev015", "Reporting", "Reporter", PermissionComparison.OR_LOWER),
        PermissionRule("dev015", "Metriken", "Developer", PermissionComparison.EXACT),
        PermissionRule("dev015", "Integration", "Reporter", PermissionComparison.EXACT),
        PermissionRule("dev015", "Appentwicklung", None, PermissionComparison.NONE),
        PermissionRule("dev015", "Webentwicklung", None, PermissionComparison.EXACT),
        PermissionRule("dev015", "Finanzen", "Reporter", PermissionComparison.MISSING_OK),
        PermissionRule("dev015", "Infrastruktur", None, PermissionComparison.NONE),
        PermissionRule("dev015", "Server", None, PermissionComparison.NONE),
        PermissionRule("dev015", "Network", None, PermissionComparison.NONE),
        PermissionRule("dev016", "Reporting", "Reporter", PermissionComparison.OR_LOWER),
        PermissionRule("dev016", "Metriken", "Developer", PermissionComparison.EXACT),
        PermissionRule("dev016", "Integration", "Reporter", PermissionComparison.EXACT),
        PermissionRule("dev016", "Appentwicklung", None, PermissionComparison.NONE),
        PermissionRule("dev016", "Webentwicklung", None, PermissionComparison.EXACT),
        PermissionRule("dev016", "Finanzen", "Reporter", PermissionComparison.MISSING_OK),
        PermissionRule("dev016", "Infrastruktur", None, PermissionComparison.NONE),
        PermissionRule("dev016", "Server", None, PermissionComparison.NONE),
        PermissionRule("dev016", "Network", None, PermissionComparison.NONE),
        PermissionRule("dev017", "Reporting", "Reporter", PermissionComparison.OR_LOWER),
        PermissionRule("dev017", "Metriken", "Developer", PermissionComparison.EXACT),
        PermissionRule("dev017", "Integration", "Reporter", PermissionComparison.EXACT),
        PermissionRule("dev017", "Appentwicklung", None, PermissionComparison.NONE),
        PermissionRule("dev017", "Webentwicklung", None, PermissionComparison.EXACT),
        PermissionRule("dev017", "Finanzen", "Reporter", PermissionComparison.MISSING_OK),
        PermissionRule("dev017", "Infrastruktur", None, PermissionComparison.NONE),
        PermissionRule("dev017", "Server", None, PermissionComparison.NONE),
        PermissionRule("dev017", "Network", None, PermissionComparison.NONE),

        # QA001-QA005 - QA Testers
        PermissionRule("qa001", "Webentwicklung", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa001", "Appentwicklung", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa001", "Integration", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa001", "Reporting", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa001", "Finanzen", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa001", "Metriken", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa001", "Infrastruktur", None, PermissionComparison.NONE),
        PermissionRule("qa001", "Server", None, PermissionComparison.NONE),
        PermissionRule("qa001", "Network", None, PermissionComparison.NONE),
        PermissionRule("qa002", "Webentwicklung", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa002", "Appentwicklung", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa002", "Integration", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa002", "Reporting", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa002", "Finanzen", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa002", "Metriken", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa002", "Infrastruktur", None, PermissionComparison.NONE),
        PermissionRule("qa002", "Server", None, PermissionComparison.NONE),
        PermissionRule("qa002", "Network", None, PermissionComparison.NONE),
        PermissionRule("qa003", "Webentwicklung", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa003", "Appentwicklung", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa003", "Integration", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa003", "Reporting", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa003", "Finanzen", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa003", "Metriken", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa003", "Infrastruktur", None, PermissionComparison.NONE),
        PermissionRule("qa003", "Server", None, PermissionComparison.NONE),
        PermissionRule("qa003", "Network", None, PermissionComparison.NONE),
        PermissionRule("qa004", "Webentwicklung", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa004", "Appentwicklung", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa004", "Integration", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa004", "Reporting", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa004", "Finanzen", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa004", "Metriken", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa004", "Infrastruktur", None, PermissionComparison.NONE),
        PermissionRule("qa004", "Server", None, PermissionComparison.NONE),
        PermissionRule("qa004", "Network", None, PermissionComparison.NONE),
        PermissionRule("qa005", "Webentwicklung", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa005", "Appentwicklung", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa005", "Integration", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa005", "Reporting", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa005", "Finanzen", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa005", "Metriken", "Reporter", PermissionComparison.EXACT),
        PermissionRule("qa005", "Infrastruktur", None, PermissionComparison.NONE),
        PermissionRule("qa005", "Server", None, PermissionComparison.NONE),
        PermissionRule("qa005", "Network", None, PermissionComparison.NONE),

        # EXT001 - External Developer
        PermissionRule("ext001", "Appentwicklung", "Developer", PermissionComparison.EXACT),
        PermissionRule("ext001", "Integration", "Reporter", PermissionComparison.NONE),
        PermissionRule("ext001", "Webentwicklung", None, PermissionComparison.NONE),
        PermissionRule("ext001", "Reporting", None, PermissionComparison.NONE),
        PermissionRule("ext001", "Finanzen", None, PermissionComparison.NONE),
        PermissionRule("ext001", "Metriken", None, PermissionComparison.NONE),
        PermissionRule("ext001", "Infrastruktur", None, PermissionComparison.NONE),
        PermissionRule("ext001", "Server", None, PermissionComparison.NONE),
        PermissionRule("ext001", "Network", None, PermissionComparison.NONE),

        # EXT002 - External Reviewer
        PermissionRule("ext002", "Webentwicklung", "Reporter", PermissionComparison.EXACT),
        PermissionRule("ext002", "Appentwicklung", None, PermissionComparison.NONE),
        PermissionRule("ext002", "Integration", None, PermissionComparison.NONE),
        PermissionRule("ext002", "Reporting", None, PermissionComparison.NONE),
        PermissionRule("ext002", "Finanzen", None, PermissionComparison.NONE),
        PermissionRule("ext002", "Metriken", None, PermissionComparison.NONE),
        PermissionRule("ext002", "Infrastruktur", None, PermissionComparison.NONE),
        PermissionRule("ext002", "Server", None, PermissionComparison.NONE),
        PermissionRule("ext002", "Network", None, PermissionComparison.NONE),

        # BOT001-BOT007 - DevOps Bots
        PermissionRule("bot001", "Webentwicklung", "Developer", PermissionComparison.EXACT),
        PermissionRule("bot002", "Appentwicklung", "Developer", PermissionComparison.EXACT),
        PermissionRule("bot003", "Integration", "Developer", PermissionComparison.EXACT),
        PermissionRule("bot004", "Infrastruktur", "Developer", PermissionComparison.EXACT),
        PermissionRule("bot005", "Reporting", "Developer", PermissionComparison.EXACT),
        PermissionRule("bot006", "Finanzen", "Developer", PermissionComparison.EXACT),
        PermissionRule("bot007", "Metriken", "Developer", PermissionComparison.EXACT),
    ]
