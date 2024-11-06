import pandas as pd

from benchmark.models import Testcase, Response
from typing import List

ACCESS_LEVELS = {
    "Guest": 10,
    "Reporter": 20,
    "Developer": 30,
    "Maintainer": 40,
    "Owner": 50,
}


def verify(testcase: Testcase, response: Response) -> int:
    try:
        df = pd.read_csv(response.response_file, sep=";")
    except Exception as e:
        response.set_check_result("# Permissions\n- CSV parsing failed")
        return 0

    score = 0
    issues = []
    for index, row in df.iterrows():
        if row[1] == "Webentwicklung":
            score += check_webentwicklung(response, issues)
        elif row[1] == "Appentwicklung":
            score += check_appentwicklung(response, issues)
        elif row[1] == "Integration":
            score += check_integration(response, issues)
        elif row[1] == "Infrastruktur":
            score += check_infrastruktur(response, issues)
        elif row[1] == "Netzwerk":
            score += check_netzwerk(response, issues)
        elif row[1] == "Server":
            score += check_server(response, issues)
        elif row[1] == "Reporting":
            score += check_reporting(response, issues)
        elif row[1] == "Finanzen":
            score += check_finanzen(response, issues)
        elif row[1] == "Metriken":
            score += check_metriken(response, issues)
        else:
            issues.append(f"- {row[1]} is not a specified group")


def check_webentwicklung(response: Response, issues: List[str]):
    pass


def check_appentwicklung(response: Response, issues: List[str]):
    pass


def check_integration(response: Response, issues: List[str]):
    pass


def check_infrastruktur(response: Response, issues: List[str]):
    pass


def check_netzwerk(response: Response, issues: List[str]):
    pass


def check_reporting(response: Response, issues: List[str]):
    pass


def check_server(response: Response, issues: List[str]):
    pass


def check_finanzen(response: Response, issues: List[str]):
    pass


def check_metriken(response: Response, issues: List[str]):
    pass
