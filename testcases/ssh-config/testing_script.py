import logging
import os
import re
import subprocess
import tempfile
import math
from typing import Tuple, List

from benchmark.models import Testcase, Response
from test_helper.ssh_config_helper import SSHConfigParser, MatchBlock

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
test_count = 0


def get_ssh_test_output(testcase: Testcase, response: Response) -> Tuple[int, str]:
    """Validate SSH configuration using a Docker container and return the output."""
    container_name = "ssh_temp"
    image_name = "ssh-validate:sshd"

    try:
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as temp_file:
            temp_file.write(response.response_file)
            temp_file_path = temp_file.name

        subprocess.run(
            ["docker", "build", "-t", image_name, testcase.path],
            check=True,
            capture_output=False,
            text=True
        )

        subprocess.run(
            ["docker", "run", "--name", container_name, "-d", image_name],
            check=True,
            capture_output=False,
            text=True
        )

        subprocess.run(
            ["docker", "cp", temp_file_path, f"{container_name}:/etc/ssh/sshd_config"],
            check=True,
            capture_output=False,
            text=True
        )

        test_result = subprocess.run(
            ["docker", "exec", container_name, "sshd", "-T"],
            capture_output=True,
            text=True
        )
        logging.debug(f"SSHD config test output: {test_result.stdout}")
        logging.debug(f"SSHD config test error output: {test_result.stderr}")

        if test_result.returncode != 0:
            logging.error(f"Invalid SSH configuration: {test_result.stderr.strip()}")
            return test_result.returncode, test_result.stderr.strip()
        else:
            return test_result.returncode, test_result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logging.error(f"Error during SSH config validation: {e.stderr}")
        return -1, e.stderr.strip()
    finally:
        subprocess.run(["docker", "rm", "-f", container_name], check=False)
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        subprocess.run(["docker", "rmi", image_name], check=False)


def verify(testcase: Testcase, response: Response) -> int:
    global test_count
    score = 0
    issues = []

    return_code, ssh_test_output = get_ssh_test_output(testcase, response)
    if return_code != 0:
        response.check_result = "### SSH Configuration Error\n\n```\n" + ssh_test_output + "\n```"
        return -1

    config = SSHConfigParser().parse_string(response.response_file)

    ssh_test_output_checks = [
        (check_permit_root, "Root Login Settings"),
        (check_host_based_authentication, "Host-based Authentication"),
        (check_login_grace, "Login Grace Time"),
        (check_max_startups, "Maximum Startups"),
        (check_for_weak_ciphers, "Cipher Configuration"),
        (check_forwarding, "Port Forwarding Settings"),
        (check_max_auth_tries, "Maximum Authentication Attempts"),
        (check_gssapi, "GSSAPI Authentication"),
        (check_max_sessions, "Maximum Sessions"),
        (check_client_alive, "Client Alive Settings"),
        (check_kex, "Key Exchange Methods"),
        (check_empty_password, "Empty Password Settings")
    ]

    for check_func, check_name in ssh_test_output_checks:
        check_score = check_func(ssh_test_output, issues)
        score += check_score

    for match_block in config.match_blocks:
        match_score, match_issues = check_match_blocks(match_block)
        score += match_score
        issues.extend(match_issues)

    if issues:
        response.check_result = "### Configuration Issues Found\n\n" + "\n".join(issues)
        response.check_result += "\n### sshd -T Output\n"
        response.check_result += f"```\n{ssh_test_output}\n```"
    if test_count == 0:
        return 0
    score = (score / test_count) * 100
    return math.floor(score)


def check_for_weak_ciphers(ssh_test: str, issues: List[str]) -> int:
    global test_count
    test_count += 1
    pattern = r"^\s*ciphers\s+([^#\n\r]+,)?(3des|blowfish|cast128|aes(128|192|256))-cbc|arcfour(128|256)?|rijndael-cbc@lysator\.liu\.se|chacha20-poly1305@openssh\.com"
    if re.search(pattern, ssh_test, re.MULTILINE | re.IGNORECASE):
        issues.append("- Weak ciphers detected in configuration")
        return 0
    return 1


def check_client_alive(ssh_test: str, issues: List[str]) -> int:
    global test_count
    test_count += 2
    score = 0
    interval_pattern = r"^\s*clientaliveinterval\s+(\d+)"
    count_pattern = r"^\s*clientalivecountmax\s+(\d+)"

    interval_match = re.search(interval_pattern, ssh_test, re.MULTILINE | re.IGNORECASE)
    count_match = re.search(count_pattern, ssh_test, re.MULTILINE | re.IGNORECASE)

    interval = int(interval_match.group(1)) if interval_match else None
    count = int(count_match.group(1)) if count_match else None

    if not interval or interval <= 0:
        issues.append("- ClientAliveInterval should be set to a positive value")
    else:
        score += 1

    if not count or count <= 0:
        issues.append("- ClientAliveCountMax should be set to a positive value")
    else:
        score += 1

    return score


def check_forwarding(ssh_test: str, issues: List[str]) -> int:
    global test_count
    test_count += 3
    score = 0

    patterns = {
        "AllowAgentForwarding": r"^\s*AllowAgentForwarding\s+(\S*)",
        "AllowTcpForwarding": r"^\s*AllowTcpForwarding\s+(\S*)",
        "X11Forwarding": r"^\s*X11Forwarding\s+(\S*)"
    }

    for name, pattern in patterns.items():
        match = re.search(pattern, ssh_test, re.MULTILINE | re.IGNORECASE)
        value = match.group(1).strip().lower() if match else None

        if value != 'no':
            issues.append(f"- {name} should be set to 'no' for security")
        else:
            score += 1

    return score


def check_gssapi(ssh_test: str, issues: List[str]) -> int:
    global test_count
    test_count += 1
    gssapi = r"^\s*gssapiauthentication\s+(\S*)"
    gssapi_match = re.search(gssapi, ssh_test, re.MULTILINE | re.IGNORECASE)
    gssapi = gssapi_match.group(1).strip().lower() if gssapi_match else None
    if gssapi != 'no':
        issues.append("- GSSAPIAuthentication should be disabled")
        return 0
    return 1


def check_host_based_authentication(ssh_test: str, issues: List[str]) -> int:
    global test_count
    test_count += 1
    host_based_authentication = r"^\s*hostbasedauthentication\s+(\S*)"
    host_based_authentication_match = re.search(host_based_authentication, ssh_test, re.MULTILINE | re.IGNORECASE)
    host_based_authentication = host_based_authentication_match.group(1) if host_based_authentication_match else None

    if not host_based_authentication or host_based_authentication.strip().lower() != 'no':
        issues.append("- HostBasedAuthentication should be disabled (set to 'no')")
        return 0
    return 1


def check_kex(ssh_test: str, issues: List[str]) -> int:
    global test_count
    test_count += 1
    pattern = r"^\s*ciphers\s+([^#\n\r]+,)?(3des|blowfish|cast128|aes(128|192|256))-cbc|arcfour(128|256)?|rijndael-cbc@lysator\.liu\.se|chacha20-poly1305@openssh\.com"
    if re.search(pattern, ssh_test, re.MULTILINE | re.IGNORECASE):
        issues.append("- Insecure key exchange methods detected")
        return 0
    return 1


def check_login_grace(ssh_test: str, issues: List[str]) -> int:
    global test_count
    test_count += 1
    login_grace_time = r"^\s*logingracetime\s+(\d+)"
    login_grace_time_match = re.search(login_grace_time, ssh_test, re.MULTILINE | re.IGNORECASE)
    login_grace_time = int(login_grace_time_match.group(1)) if login_grace_time_match else None

    if not login_grace_time:
        issues.append("- LoginGraceTime not set")
        return 0
    elif login_grace_time <= 0 or login_grace_time >= 60:
        issues.append(f"- LoginGraceTime should be between 1 and 60 seconds (current: {login_grace_time})")
        return 0
    return 1


def check_max_auth_tries(ssh_test: str, issues: List[str]) -> int:
    global test_count
    test_count += 1
    max_auth_tries = r"^\s*maxauthtries\s+(\d+)"
    max_auth_tries_match = re.search(max_auth_tries, ssh_test, re.MULTILINE | re.IGNORECASE)
    max_auth_tries = int(max_auth_tries_match.group(1)) if max_auth_tries_match else None

    if not max_auth_tries:
        issues.append("- MaxAuthTries not set")
        return 0
    elif max_auth_tries > 4:
        issues.append(f"- MaxAuthTries should be 4 or less (current: {max_auth_tries})")
        return 0
    return 1


def check_max_sessions(ssh_test: str, issues: List[str]) -> int:
    global test_count
    test_count += 1
    max_sessions = r"^\s*maxsessions\s+(\d+)"
    max_sessions_match = re.search(max_sessions, ssh_test, re.MULTILINE | re.IGNORECASE)
    max_sessions = int(max_sessions_match.group(1)) if max_sessions_match else None

    if not max_sessions:
        issues.append("- MaxSessions not set")
        return 0
    elif max_sessions > 10:
        issues.append(f"- MaxSessions should be 10 or less (current: {max_sessions})")
        return 0
    return 1


def check_max_startups(ssh_test: str, issues: List[str]) -> int:
    global test_count
    test_count += 1
    max_startups_pattern = r"^\s*maxstartups\s+(\S*)"
    max_startups_match = re.search(max_startups_pattern, ssh_test, re.MULTILINE | re.IGNORECASE)
    max_startups = max_startups_match.group(1) if max_startups_match else None

    if not max_startups:
        issues.append("- MaxStartups not set")
        return 0

    max_startups_values = max_startups.split(':')
    expected_values = [10, 30, 60]

    if len(max_startups_values) != 3:
        issues.append("- MaxStartups should have three components (start:rate:full)")
        return 0

    for i, (expected_value, actual_value) in enumerate(zip(expected_values, max_startups_values)):
        if not actual_value.isdigit() or int(actual_value) != expected_value:
            component_names = ['start', 'rate', 'full']
            issues.append(
                f"- MaxStartups {component_names[i]} value should be {expected_value} (current: {actual_value})")
            return 0
    return 1


def check_empty_password(ssh_test: str, issues: List[str]) -> int:
    global test_count
    test_count += 1
    empty_password = r"^\s*permitemptypasswords\s+(\S*)"
    empty_password_match = re.search(empty_password, ssh_test, re.MULTILINE | re.IGNORECASE)
    empty_password = empty_password_match.group(1) if empty_password_match else None

    if not empty_password:
        issues.append("- PermitEmptyPasswords not set")
        return 0
    elif empty_password.strip().lower() != 'no':
        issues.append("- PermitEmptyPasswords should be set to 'no'")
        return 0
    return 1


def check_permit_root(ssh_test: str, issues: List[str]) -> int:
    global test_count
    test_count += 1
    permit_root = r"^\s*permitrootlogin\s+(\S*)"
    permit_root_match = re.search(permit_root, ssh_test, re.MULTILINE | re.IGNORECASE)
    permit_root = permit_root_match.group(1) if permit_root_match else None

    if not permit_root:
        issues.append("- PermitRootLogin not set")
        return 0
    elif permit_root.strip().lower() != 'no':
        issues.append("- PermitRootLogin should be set to 'no'")
        return 0
    return 1


def check_password_authentication(ssh_test: str, issues: List[str]) -> int:
    global test_count
    test_count += 1
    password_authentication = r"^\s*passwordauthentication\s+(\S*)"
    password_authentication_match = re.search(password_authentication, ssh_test, re.MULTILINE | re.IGNORECASE)
    password_authentication = password_authentication_match.group(1) if password_authentication_match else None

    if not password_authentication:
        issues.append("- PasswordAuthentication not set")
        return 0
    elif password_authentication.strip().lower() != 'no':
        issues.append("- PasswordAuthentication should be set to 'no'")
        return 0
    return 1


def check_match_blocks(match_block: MatchBlock) -> Tuple[int, List[str]]:
    global test_count
    test_count += 4
    score = 0
    issues = []

    network_configs = {
        '172.16.0.0/16': {
            'root_login': 'prohibit-password',
            'groups': {'accounting'},
            'forwarding': {'x11': 'yes', 'tcp': 'no', 'agent': 'no'},
            'password_auth': 'no'
        },
        '172.17.0.0/16': {
            'root_login': 'prohibit-password',
            'groups': {'admin', 'root'},
            'forwarding': {'x11': 'no', 'tcp': 'yes', 'agent': 'no'},
            'password_auth': 'no'
        },
        '172.18.0.0/16': {
            'root_login': 'no',
            'groups': {'guest'},
            'forwarding': {'x11': 'no', 'tcp': 'no', 'agent': 'no'},
            'password_auth': 'yes'
        }
    }

    criteria_value = match_block.criteria_value.strip().lower()
    if criteria_value in network_configs:
        expected_config = network_configs[criteria_value]
        for option in match_block.options:
            name = option.name.lower().strip()
            value = option.value.lower().strip()
            if name == 'permitrootlogin':
                if value != expected_config['root_login']:
                    issues.append(f"- Incorrect PermitRootLogin setting for network {criteria_value}")
                else:
                    score += 1
            elif name == 'allowgroups':
                groups = set(value.split())
                if groups != expected_config['groups']:
                    issues.append(f"- Incorrect AllowGroups setting for network {criteria_value}")
                else:
                    score += 1
            elif name in ['x11forwarding', 'allowtcpforwarding', 'allowagentforwarding']:
                forwarding_type = name.replace('allow', '').replace('forwarding', '').lower()
                if value != expected_config['forwarding'][forwarding_type]:
                    issues.append(f"- Incorrect {name} setting for network {criteria_value}")

            elif name == 'passwordauthentication':
                if value != expected_config['password_auth']:
                    issues.append(f"- Incorrect PasswordAuthentication setting for network {criteria_value}")

    return score, issues
