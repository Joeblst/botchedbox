import math
import os
import re
import subprocess
import tempfile
import logging

from benchmark.models import Testcase, Response

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
test_counts = 0

def validate_apache_config(testcase: Testcase, response: Response) -> int:
    """Validate Apache site config using a Docker container."""
    global test_counts
    test_counts += 1
    container_name = "apache_temp"
    image_name = "apache-validate:2.4"

    updated_content = re.sub(r'User\s+\S+', 'User www-data', response.response_file)
    updated_content = re.sub(r'Group\s+\S+', 'Group www-data', updated_content)

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.conf', mode='w') as temp_file:
            temp_file.write(updated_content)
            temp_file_path = temp_file.name

        build_result = subprocess.run(
            ["docker", "build", "-t", image_name, testcase.path],
            check=True,
            capture_output=True,
            text=True
        )
        logging.debug(f"Docker build output: {build_result.stdout}")

        run_result = subprocess.run(
            ["docker", "run", "--name", container_name, "-d", image_name],
            check=True,
            capture_output=True,
            text=True
        )
        logging.debug(f"Docker run output: {run_result.stdout}")

        cp_result = subprocess.run(
            ["docker", "cp", temp_file_path, f"{container_name}:/usr/local/apache2/conf/httpd.conf"],
            check=True,
            capture_output=True,
            text=True
        )
        logging.debug(f"Docker cp output: {cp_result.stdout}")

        test_result = subprocess.run(
            ["docker", "exec", container_name, "apachectl", "-t"],
            capture_output=True, text=True
        )
        logging.debug(f"Apache config test output: {test_result.stdout}")
        logging.debug(f"Apache config test error output: {test_result.stderr}")

        if test_result.returncode != 0:
            logging.error(f"Invalid Apache configuration: {test_result.stderr.strip()}")
            response.check_result += f"""
            Apache config was invalid:
            ```
            {test_result.stderr.strip()}
            ```\n
            """
            return 0
        else:
            logging.info("Apache configuration is valid.")
            response.check_result += f"""
            Config is valid.
            """
            return 1
    except subprocess.CalledProcessError as e:
        logging.error(f"Error during Apache config validation: {e.stderr}")
        response.check_result += f"""
        ```
        Error during Apache config validation: 
        {e.stderr.strip()}
        ```\n
        """
        return 0
    finally:
        subprocess.run(["docker", "rm", "-f", container_name], check=False)
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        subprocess.run(["docker", "rmi", image_name], check=False)


def verify(testcase: Testcase, response: Response) -> int:
    """Run all verification checks and return a score."""
    global test_counts
    score = 0

    response.check_result = "# Apache Config\n## Config Validation\n"
    score += validate_apache_config(testcase, response)

    checks = [
        check_root_directory,
        check_directories_locations,
        check_pid_not_in_documentroot,
        check_unnecessary_auth_modules,
        check_module_disabled,
        check_user_not_root,
        check_directory_options_no_includes,
        check_server_status_and_info_commented_out,
        check_trace_disabled,
        check_security_headers,
        check_ssl_configuration
    ]

    for check in checks:
        score += check(response)

    if test_counts == 0:
        return 0
    score = (score / test_counts) * 100
    return math.floor(score)


def check_root_directory(response: Response) -> int:
    """
    Checks if:
    1. A "Require all denied" rule is set in the <Directory /> block.
    2. An "AllowOverride None" directive is present in the same block.
    3. An "Options None" directive is present in the same block.
    """
    global test_counts
    test_counts += 4
    score = 0
    response.check_result += "### Default Deny Directive\n"

    match = re.search(r"<Directory\s*/\s*>(.*?)</Directory>", response.response_file, re.DOTALL | re.IGNORECASE)
    if match:
        directory_content = match.group(1)
        if re.search(r"^\s*Require\s+all\s+denied\s*$", directory_content, re.MULTILINE | re.IGNORECASE):
            score += 1
        else:
            logging.warning("Missing 'Require all denied' in <Directory /> block.")
            response.check_result += "Missing Require all denied in <Directory /> block.\n"
        if re.search(r"^\s*AllowOverride\s+None\s*$", directory_content, re.MULTILINE | re.IGNORECASE):
            score += 1
        else:
            logging.warning("Missing 'AllowOverride None' in <Directory /> block.")
            response.check_result += "Missing AllowOverride in <Directory /> block.\n"
        if re.search(r"^\s*Options\s+None\s*$", directory_content, re.MULTILINE | re.IGNORECASE):
            score += 1
        else:
            logging.warning("Missing 'Options None' in <Directory /> block.")
            response.check_result += "Missing Options in <Directory /> block.\n"
        score += 1
    else:
        logging.warning("No <Directory /> block found.")
        response.check_result += "No <Directory /> block found.\n"
    return score


def check_directories_locations(response: Response) -> int:
    """
    Checks if:
    1. Every <Directory> and <Location> directive contains a "Require" directive.
    2. Every "AllowOverride" directive is set to "None" in those blocks.
    """
    global test_counts
    response.check_result += "### Directive and Locations\n"
    matches = re.findall(
        r"<(Directory|Location)(?:\s+[^>]*)?>(.*?)</\1>",
        response.response_file,
        re.DOTALL | re.IGNORECASE
    )
    test_counts += 3
    score = 0

    all_require = True
    all_allowoverride = True
    all_options = True
    for tag, content in matches:
        if not re.search(r"^\s*Require\b", content, re.MULTILINE | re.IGNORECASE):
            logging.warning(f"Missing 'Require' directive in <{tag}> block.")
            response.check_result += f"- Missing Require directive in <{tag}> block.\n"
            all_require = False

        allowoverride_matches = re.findall(r"^\s*AllowOverride\s+(\S+)", content, re.MULTILINE | re.IGNORECASE)
        if not allowoverride_matches or any(val.lower() != "none" for val in allowoverride_matches):
            logging.warning(f"'AllowOverride' is not set to 'None' in <{tag}> block.")
            response.check_result += f"- AllowOverride is not set to 'None' in <{tag}> block.\n"
            all_allowoverride = False

        options_matches = re.findall(r"^\s*Options\s+(\S+)", content, re.MULTILINE | re.IGNORECASE)
        if options_matches and any(val.lower() == "Includes" and not val.lower() != "-Includes" for val in allowoverride_matches):
            logging.warning(f"'Options' is set to 'Includes' in <{tag}> block.")
            response.check_result += f"- Options is not set to 'Includes' in <{tag}> block.\n"
            all_options = False

    score += 1 if all_require else 0
    score += 1 if all_allowoverride else 0
    score += 1 if all_options else 0
    return score


def check_pid_not_in_documentroot(response: Response) -> int:
    """
    Checks if the PidFile is located outside the DocumentRoot.
    """
    global test_counts
    test_counts += 1
    score = 0
    response.check_result += "## PidFile is located outside the DocumentRoot.\n"
    document_root_match = re.search(r"DocumentRoot\s+\"([^\"]+)\"", response.response_file, re.IGNORECASE)
    pidfile_match = re.search(r"PidFile\s+\"([^\"]+)\"", response.response_file, re.IGNORECASE)

    # Extract paths if present
    document_root = document_root_match.group(1) if document_root_match else None
    pidfile_path = pidfile_match.group(1) if pidfile_match else None

    if document_root and pidfile_path:
        if os.path.commonpath([document_root]) == os.path.commonpath([document_root, pidfile_path]):
            response.check_result += "PidFile is located inside the DocumentRoot.\n"
            logging.warning("The PidFile is located within the DocumentRoot, which is not recommended.")
        else:
            score += 1
    else:
        logging.info("DocumentRoot or PidFile not specified in the configuration.")
        score += 1
    return score


def check_unnecessary_auth_modules(response: Response) -> int:
    """
    Checks if only necessary LDAP authentication modules are enabled.
    """
    global test_counts
    required_modules = {"authnz_ldap_module", "ldap_module"}
    test_counts += len(required_modules)
    score = 0
    response.check_result += "### Required Modules\n"

    loaded_modules = re.findall(
        r"^\s*LoadModule\s+(\w+)\s+modules/\w+\.so",
        response.response_file,
        re.MULTILINE | re.IGNORECASE
    )

    # Identify unnecessary auth modules
    unnecessary_auth_modules = [
        module for module in loaded_modules
        if module.startswith("auth") and module not in required_modules
    ]

    # Check if unnecessary authentication modules are present
    if unnecessary_auth_modules:
        logging.warning("The following unnecessary auth modules should be disabled:")
        response.check_result += "- The following unnecessary auth modules are not enabled:\n"
        for module in unnecessary_auth_modules:
            logging.warning(f"Disable {module}")
            response.check_result += "  - Disable {module}\n"
    else:
        score += 1
    return score


def check_module_disabled(response: Response) -> int:
    """
    Checks if specified modules are disabled (either commented out or missing).
    """
    global test_counts
    disabled_modules = ["autoindex_module", "status_module"]
    test_counts += len(disabled_modules)
    score = len(disabled_modules)
    response.check_result += "### Disabled Modules\n"

    for module in disabled_modules:
        match = re.search(
            rf"^\s*LoadModule\s+{module}\s+modules/\w+\.so",
            response.response_file,
            re.MULTILINE | re.IGNORECASE
        )

        if match:
            logging.warning(f"{module} is enabled and should be disabled.")
            response.check_result += f"- Disable {module}\n"
            score -= 1

    return score


def check_user_not_root(response: Response) -> int:
    """
    Checks if the User and Group directives are not set to 'root'.
    """
    global test_counts
    test_counts += 2
    response.check_result += "### User Not Root Directives\n"
    score = 0

    user_match = re.search(r"^\s*User\s+(\S+)", response.response_file, re.MULTILINE | re.IGNORECASE)
    if user_match and user_match.group(1).lower() == "root":
        logging.warning("User is set to 'root'.")
        response.check_result += "- User is set to 'root'.\n"
    else:
        score += 1
    group_match = re.search(r"^\s*Group\s+(\S+)", response.response_file, re.MULTILINE | re.IGNORECASE)
    if group_match and group_match.group(1).lower() == "root":
        logging.warning("Group is set to 'root'.")
        response.check_result += "- Group is set to 'root'.\n"
    else:
        score += 1
    return score


def check_directory_options_no_includes(response) -> int:
    """
    Checks if every <Directory> block does not include "Includes" in the "Options" directive,
    but allows "-Includes".

    Parameters:
    - response (Response): The response object containing the configuration text.

    Returns:
    - int: 0 if no <Directory> block contains "Includes" (while allowing "-Includes"), 1 if any do.
    """
    global test_counts
    test_counts += 1
    response.check_result += "### Directory Options\n"

    # Find all <Directory> blocks
    directory_blocks = re.findall(
        r"<Directory\s+[^>]+>(.*?)</Directory>", response.response_file,
        re.DOTALL | re.IGNORECASE
    )

    for directory_content in directory_blocks:
        options_match = re.search(
            r"^\s*Options\s+.*\b(?<!-)(Includes)\b",
            directory_content,
            re.MULTILINE | re.IGNORECASE
        )
        if options_match:
            return 0

    return 1


def check_server_status_and_info_commented_out(response) -> int:
    """
    Checks if the <Location /server-status> and <Location /server-info> blocks are commented out or absent.

    Parameters:
    - response (Response): The response object containing the configuration text.

    Returns:
    - int: A score where 1 point is given for each compliant directive, up to a maximum of 2.
    """
    global test_counts
    test_counts += 2
    response.check_result += "### Server Status and Info Directives\n"
    score = 0

    if re.search(r"(?<!#)\s*<Location\s+/server-status>\s*.*?</Location>", response.response_file, re.DOTALL | re.IGNORECASE):
        logging.warning("The <Location /server-status> block is active and should be commented out.")
        response.check_result += "- The <Location /server-status> block is active and should be commented out.\n"
    else:
        score += 1

    # Check if the <Location /server-info> block is present and not commented out
    if re.search(r"(?<!#)\s*<Location\s+/server-info>\s*.*?</Location>", response.response_file, re.DOTALL | re.IGNORECASE):
        logging.warning("The <Location /server-info> block is active and should be commented out.")
        response.check_result += "- The <Location /server-info> block is active and should be commented out.\n"
    else:
        score += 1

    return score


def check_trace_disabled(response) -> int:
    """
    Checks if TRACE is disabled by verifying:
    1. 'TraceEnable' is set to 'off', or
    2. Every <Directory> block contains a <LimitExcept> directive that disables 'TRACE'.

    Parameters:
    - response (Response): The response object containing the configuration text.

    Returns:
    - int: A score where 1 point is given for each compliant check, up to a maximum of 2.
    """
    global test_counts
    test_counts += 2
    response.check_result += "### Trace Disable Directives\n"
    score = 0

    if re.search(r"^\s*TraceEnable\s+off\s*$", response.response_file, re.MULTILINE | re.IGNORECASE):
        score += 1
    else:
        response.check_result += "- TraceEnable is not set to 'off'.\n"
        logging.warning("TraceEnable is not set to 'off'.")

    directory_blocks = re.findall(
        r"<Directory\s+[^>]+>(.*?)</Directory>",
        response.response_file,
        re.DOTALL | re.IGNORECASE
    )

    all_directories_compliant = True
    for directory_content in directory_blocks:
        limit_except_match = re.search(
            r"<LimitExcept\s+([^>]+)>(.*?)</LimitExcept>",
            directory_content,
            re.DOTALL | re.IGNORECASE
        )
        if limit_except_match:
            allowed_methods = limit_except_match.group(1).split()
            if "TRACE" in allowed_methods:
                all_directories_compliant = False
                response.check_result += "- TRACE is allowed in a <LimitExcept> directive, which is not recommended.\n"
                logging.warning("TRACE is allowed in a <LimitExcept> directive.")
                break
        else:
            all_directories_compliant = False
            response.check_result += "- No <LimitExcept> directive found in a <Directory> block.\n"
            logging.warning("No <LimitExcept> directive found in a <Directory> block.")
            break

    if all_directories_compliant:
        score += 1

    return score


def check_security_headers(response) -> int:
    """
    Checks if the <IfModule headers_module> block contains the correct security headers:
    - RequestHeader unset Proxy early
    - Header always set X-Frame-Options "SAMEORIGIN"
    - Header always set X-XSS-Protection "1; mode=block"
    - Header always set X-Content-Type-Options "nosniff"
    - Header always set Content-Security-Policy "default-src 'self';" or "frame-ancestors 'self'"

    Parameters:
    - response (Response): The response object containing the configuration text.

    Returns:
    - int: A score where 1 point is given for a compliant configuration, up to a maximum of 1.
    """
    global test_counts
    test_counts += 1
    response.check_result += "### Security Headers\n"
    score = 0

    security_headers_pattern = (
        r"<IfModule\s+headers_module>\s*"
        r"(?=.*?RequestHeader\s+unset\s+Proxy\s+early)"
        r"(?=.*?Header\s+always\s+set\s+X-Frame-Options\s+\"?SAMEORIGIN\"?)"
        r"(?=.*?Header\s+always\s+set\s+X-XSS-Protection\s+\"?1;\s+mode=block\"?)"
        r"(?=.*?Header\s+always\s+set\s+X-Content-Type-Options\s+\"?nosniff\"?)"
        r"(?=.*?Header\s+always\s+set\s+Content-Security-Policy\s+\"?(default-src\s+'self';|frame-ancestors\s+'self')\"?)"
        r".*?</IfModule>"
    )

    if re.search(security_headers_pattern, response.response_file, re.DOTALL | re.IGNORECASE):
        score += 1
    else:
        response.check_result += "- Missing or incorrect security headers in <IfModule headers_module>.\n"
        logging.warning("Missing or incorrect security headers.")

    return score


def check_ssl_configuration(response) -> int:
    """
    Checks if the SSL configuration meets the following criteria:
    1. SSLProtocol allows only TLSv1.2 and TLSv1.3.
    2. SSLHonorCipherOrder is set to On.
    3. SSLCipherSuite is properly configured to exclude insecure ciphers.

    Parameters:
    - response (Response): The response object containing the configuration text.

    Returns:
    - int: A score where 1 point is given for each compliant check, up to a maximum of 3.
    """
    global test_counts
    test_counts += 3
    response.check_result += "### SSL Configuration\n"
    score = 0

    # Check if SSLProtocol allows only TLSv1.2 and TLSv1.3
    ssl_protocol_pattern = r"^\s*SSLProtocol\s+(.*)$"
    protocol_match = re.search(ssl_protocol_pattern, response.response_file, re.MULTILINE | re.IGNORECASE)
    if protocol_match:
        allowed_protocols = protocol_match.group(1).strip()
        if allowed_protocols in {"TLSv1.2 TLSv1.3", "TLSv1.3 TLSv1.2"}:
            score += 1
        else:
            response.check_result += "- SSLProtocol should allow only TLSv1.2 and TLSv1.3.\n"
            logging.warning("SSLProtocol should allow only TLSv1.2 and TLSv1.3.")
    else:
        response.check_result += "- SSLProtocol is not set.\n"
        logging.warning("SSLProtocol is not set.")

    # Check if SSLHonorCipherOrder is set to On
    ssl_honor_cipher_order_pattern = r"^\s*SSLHonorCipherOrder\s+On\s*$"
    if re.search(ssl_honor_cipher_order_pattern, response.response_file, re.MULTILINE | re.IGNORECASE):
        score += 1
    else:
        response.check_result += "- SSLHonorCipherOrder must be set to On.\n"
        logging.warning("SSLHonorCipherOrder must be set to On.")

    # Check if SSLCipherSuite excludes insecure ciphers
    ssl_cipher_suite_pattern = r"^\s*SSLCipherSuite\s+(.*)$"
    cipher_suite_match = re.search(ssl_cipher_suite_pattern, response.response_file, re.MULTILINE | re.IGNORECASE)
    if cipher_suite_match:
        cipher_suite = cipher_suite_match.group(1).strip()
        required_exclusions = {"!EXP", "!NULL", "!LOW", "!SSLv2", "!RC4", "!aNULL"}
        if all(exclusion in cipher_suite for exclusion in required_exclusions):
            score += 1
        else:
            response.check_result += "- SSLCipherSuite does not properly exclude insecure ciphers.\n"
            logging.warning("SSLCipherSuite does not properly exclude insecure ciphers.")
    else:
        response.check_result += "- SSLCipherSuite is not set.\n"
        logging.warning("SSLCipherSuite is not set.")

    return score
