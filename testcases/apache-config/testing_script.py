import logging
import os
import re
import subprocess
import tempfile

import math

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
            response.check_result += f"Apache config was invalid:\n```\n{test_result.stderr.strip()}\n```\n"
            response.set_valid(False)
            return 0
        else:
            response.check_result += "Config is valid."
            response.set_valid(True)
            return 1
    except subprocess.CalledProcessError as e:
        logging.error(f"Error during Apache config validation: {e.stderr}")
        response.check_result += f"```\nError during Apache config validation:\n{e.stderr.strip()}\n```\n"
        response.set_valid(False)
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
    Checks security configurations for root directory access:
    1. Finds DocumentRoot value
    2. Checks for security directives in <Directory /> block if it exists
    3. If no / block exists, checks for directives in DocumentRoot block
    4. Verifies "Require all denied", "AllowOverride None", and "Options None" directives
    """
    global test_counts
    test_counts += 4
    score = 0
    response.check_result += "### Default Deny Directive\n"

    doc_root_match = re.search(r"^\s*DocumentRoot\s+[\"']?([^\"'\s]+)[\"']?\s*$",
                               response.response_file,
                               re.MULTILINE | re.IGNORECASE)
    if not doc_root_match:
        response.check_result += "- DocumentRoot not found in configuration.\n"
        return score

    doc_root = doc_root_match.group(1)

    root_match = re.search(
        r"<Directory\s*/\s*>(.*?)</Directory>",
        response.response_file,
        re.DOTALL | re.IGNORECASE
    )

    # If no root block, check for DocumentRoot block
    if not root_match:
        doc_root_escaped = re.escape(doc_root)
        root_match = re.search(
            f"<Directory\s+[\"']?{doc_root_escaped}[\"']?\s*>(.*?)</Directory>",
            response.response_file,
            re.DOTALL | re.IGNORECASE
        )
        if not root_match:
            response.check_result += "- No root directory configuration block found.\n"
            return score

    directory_content = root_match.group(1)

    if re.search(
            r"^\s*Require\s+all\s+denied\s*$",
            directory_content,
            re.MULTILINE | re.IGNORECASE
    ):
        score += 1
    else:
        response.check_result += "- Missing Require all denied in root directory block.\n"

    if re.search(
            r"^\s*AllowOverride\s+None\s*$",
            directory_content,
            re.MULTILINE | re.IGNORECASE
    ):
        score += 1
    else:
        response.check_result += "- Missing AllowOverride in root directory block.\n"

    if re.search(r"^\s*Options\s+None\s*$",
                 directory_content,
                 re.MULTILINE | re.IGNORECASE):
        score += 1
    else:
        response.check_result += "- Missing Options in root directory block.\n"
    score += 1

    return score


def get_effective_directives(current_content: str, inherited_content: str) -> dict:
    """
    Determines effective directives by combining inherited and current content,
    with current content taking precedence.
    """
    directives = {
        'require': None,
        'allowoverride': None,
        'options': None
    }

    # Check inherited content first (will be overridden by current if present)
    if inherited_content:
        require_match = re.search(r"^\s*Require\s+(.+)$", inherited_content, re.MULTILINE | re.IGNORECASE)
        if require_match:
            directives['require'] = require_match.group(1)

        allowoverride_match = re.search(r"^\s*AllowOverride\s+(\S+)", inherited_content, re.MULTILINE | re.IGNORECASE)
        if allowoverride_match:
            directives['allowoverride'] = allowoverride_match.group(1)

        options_match = re.search(r"^\s*Options\s+(.+)$", inherited_content, re.MULTILINE | re.IGNORECASE)
        if options_match:
            directives['options'] = options_match.group(1)

    # Check current content and override inherited values
    require_match = re.search(r"^\s*Require\s+(.+)$", current_content, re.MULTILINE | re.IGNORECASE)
    if require_match:
        directives['require'] = require_match.group(1)

    allowoverride_match = re.search(r"^\s*AllowOverride\s+(\S+)", current_content, re.MULTILINE | re.IGNORECASE)
    if allowoverride_match:
        directives['allowoverride'] = allowoverride_match.group(1)

    options_match = re.search(r"^\s*Options\s+(.+)$", current_content, re.MULTILINE | re.IGNORECASE)
    if options_match:
        directives['options'] = options_match.group(1)

    return directives


def check_directories(response: Response) -> int:
    """
    Checks Directory blocks for security configurations, handling directive inheritance
    and overrides correctly.
    """
    score = 0
    directory_blocks = {}

    # Find all Directory blocks and store them by path
    matches = re.findall(
        r"<Directory[ \t]+(?:\"([^\"]+)\"|'([^']+)'|([^> \t]+))[ \t]*>(.*?)</Directory>",
        response.response_file,
        re.DOTALL | re.IGNORECASE
    )

    # Process matches into dictionary
    for match in matches:
        path = next(p for p in match[:-1] if p)  # Get first non-empty path group
        content = match[-1]
        directory_blocks[path] = content

    # Sort paths by length to handle inheritance (parent paths first)
    sorted_paths = sorted(directory_blocks.keys(), key=len)

    all_require = True
    all_allowoverride = True
    all_options = True

    for path in directory_blocks:
        current_content = directory_blocks[path]
        inherited_content = ""

        # Find parent paths that this path inherits from
        for parent_path in sorted_paths:
            if path.startswith(parent_path) and path != parent_path:
                inherited_content += "\n" + directory_blocks[parent_path]

        # Get effective directives after handling overrides
        effective = get_effective_directives(current_content, inherited_content)

        # Check Require directive
        if not effective['require']:
            response.check_result += f"- Missing Require directive in Directory block for {path}\n"
            all_require = False

        # Check AllowOverride directive
        if not effective['allowoverride'] or effective['allowoverride'].lower() != "none":
            response.check_result += f"- AllowOverride is not set to 'None' in Directory block for {path}\n"
            all_allowoverride = False

        # Check Options directive
        if effective['options'] and (
                "includes" in effective['options'].lower()
                and not "-includes" in effective['options'].lower()
                and not "includesnoexec" in effective['options'].lower()
        ):
            response.check_result += f"- Options allows Includes in Directory block for {path} \n"
            all_options = False

    score += 1 if all_require else 0
    score += 1 if all_allowoverride else 0
    score += 1 if all_options else 0
    return score


def check_locations(response: Response) -> int:
    """
    Checks Location blocks for security configurations, handling directive inheritance
    and overrides correctly.
    """
    score = 0
    location_blocks = {}

    # Find all Location blocks and store them by path
    matches = re.findall(
        r"<Location[ \t]+(?:\"([^\"]+)\"|'([^']+)'|([^> \t]+))[ \t]*>(.*?)</Location>",
        response.response_file,
        re.DOTALL | re.IGNORECASE
    )

    # Process matches into dictionary
    for match in matches:
        path = next(p for p in match[:-1] if p)  # Get first non-empty path group
        content = match[-1]
        location_blocks[path] = content

    # Sort paths by length to handle inheritance (parent paths first)
    sorted_paths = sorted(location_blocks.keys(), key=len)

    all_require = True
    all_allowoverride = True
    all_options = True

    for path in location_blocks:
        current_content = location_blocks[path]
        inherited_content = ""

        # Find parent paths that this path inherits from
        for parent_path in sorted_paths:
            if path.startswith(parent_path) and path != parent_path:
                inherited_content += "\n" + location_blocks[parent_path]

        # Get effective directives after handling overrides
        effective = get_effective_directives(current_content, inherited_content)

        # Check Require directive
        if not effective['require']:
            response.check_result += f"- Missing Require directive in Location block for {path}\n"
            all_require = False

        # Check AllowOverride directive (though not typically used in Location)
        if not effective['allowoverride'] or effective['allowoverride'].lower() != "none":
            response.check_result += f"- AllowOverride is not set to 'None' in Location block for {path}\n"
            all_allowoverride = False

        # Check Options directive
        if effective['options'] and (
                "includes" in effective['options'].lower()
                and not "-includes" in effective['options'].lower()
                and not "IncludesNOEXEC" in effective['options'].lower()
        ):
            response.check_result += f"- Options allows Includes in Location block for {path}\n"
            all_options = False

    score += 1 if all_require else 0
    score += 1 if all_allowoverride else 0
    score += 1 if all_options else 0
    return score


def check_directories_locations(response: Response) -> int:
    """
    Checks Directory and Location blocks for security configurations.
    Returns combined score from both checks.
    """
    global test_counts
    test_counts += 6  # 3 checks each for Directory and Location
    response.check_result += "### Directory and Location Directives\n"

    dir_score = check_directories(response)
    loc_score = check_locations(response)

    return dir_score + loc_score


def check_pid_not_in_documentroot(response: Response) -> int:
    """
    Checks if the PidFile is located outside the DocumentRoot.
    """
    global test_counts
    test_counts += 1
    score = 0
    response.check_result += "### Check PIDFile in DocumentRoot\n"
    document_root_match = re.search(r"DocumentRoot\s+\"([^\"]+)\"", response.response_file, re.IGNORECASE)
    pidfile_match = re.search(r"PidFile\s+\"([^\"]+)\"", response.response_file, re.IGNORECASE)

    # Extract paths if present
    document_root = document_root_match.group(1) if document_root_match else None
    pidfile_path = pidfile_match.group(1) if pidfile_match else None

    if document_root and pidfile_path:
        if os.path.commonpath([document_root]) == os.path.commonpath([document_root, pidfile_path]):
            response.check_result += "PidFile is located inside the DocumentRoot.\n"
        else:
            score += 1
    else:
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
        response.check_result += "The following unnecessary auth modules are not enabled:\n"
        for module in unnecessary_auth_modules:
            response.check_result += f"- Disable {module}\n"
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
            response.check_result += f"- Disable {module}\n"
            score -= 1

    return score


def check_user_not_root(response: Response) -> int:
    """
    Checks if the User and Group directives are not set to 'root'.
    """
    global test_counts
    test_counts += 2
    response.check_result += "### Apache User Directives\n"
    score = 0

    user_match = re.search(r"^\s*User\s+(\S+)", response.response_file, re.MULTILINE | re.IGNORECASE)
    if user_match and user_match.group(1).lower() == "root":
        response.check_result += "- User is set to 'root'.\n"
    else:
        score += 1
    group_match = re.search(r"^\s*Group\s+(\S+)", response.response_file, re.MULTILINE | re.IGNORECASE)
    if group_match and group_match.group(1).lower() == "root":
        response.check_result += "- Group is set to 'root'.\n"
    else:
        score += 1
    return score


def check_directory_options_no_includes(response) -> int:
    """
    Checks if every <Directory> block does allow Includes
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
    Checks if the <Location /server-status> and <Location /server-info> blocks are disabled
    """
    global test_counts
    test_counts += 2
    response.check_result += "### Server Status and Info Directives\n"
    score = 0

    # Check if the <Location /server-status> block is active
    if re.search(
            r"(?<!#)\s*<Location\s+/server-status>\s*.*?</Location>",
            response.response_file,
            re.DOTALL | re.IGNORECASE
    ):
        response.check_result += "- The <Location /server-status> block is active and should be commented out.\n"
    else:
        score += 1

    server_info_match = re.search(
        r"(?<!#)\s*<Location\s+/server-info>\s*(.*?)</Location>",
        response.response_file,
        re.DOTALL | re.IGNORECASE
    )
    if server_info_match:
        server_info_content = server_info_match.group(1)

        if re.search(r"(?<!#)\s*Deny\s+from\s+all", server_info_content, re.IGNORECASE):
            score += 1
        else:
            response.check_result += "- The <Location /server-info> block should deny access to all clients.\n"
    else:
        score += 1

    return score


def check_trace_disabled(response) -> int:
    """
    Checks if TRACE is disabled by verifying:
    1. 'TraceEnable' is set to 'off', or
    2. Every <Directory> block contains a <LimitExcept> directive that disables 'TRACE'.
    """
    global test_counts
    test_counts += 2
    response.check_result += "### Trace Disable Directives\n"
    score = 0

    if re.search(r"^\s*TraceEnable\s+off\s*$", response.response_file, re.MULTILINE | re.IGNORECASE):
        score += 1
    else:
        response.check_result += "- TraceEnable is not set to 'off'.\n"

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
                response.check_result += "- TRACE is allowed in a <LimitExcept\> directive, which is not recommended.\n"
                break
        else:
            all_directories_compliant = False
            response.check_result += "- No <LimitExcept\> directive found in a <Directory\> block.\n"
            break

    if all_directories_compliant:
        score += 1

    return score


def check_security_headers(response) -> int:
    """
    Checks if the <IfModule headers_module> block contains the correct security headers:
    - RequestHeader unset Proxy early
    - Header always set X-Frame-Options "SAMEORIGIN" or "DENY"
    - Header always set X-XSS-Protection "1; mode=block"
    - Header always set X-Content-Type-Options "nosniff"
    - Header always set Content-Security-Policy "default-src 'self';" or "frame-ancestors 'self'"
    """
    global test_counts
    test_counts += 5
    response.check_result += "### Security Headers\n"
    score = 0

    # Patterns for individual security headers
    patterns = {
        "Proxy early": r"RequestHeader\s+unset\s+Proxy\s+early",
        "X-Frame-Options": r"Header\s+always\s+set\s+X-Frame-Options\s+\"?(SAMEORIGIN|DENY)\"?",
        "X-XSS-Protection": r"Header\s+always\s+set\s+X-XSS-Protection\s+\"?1;\s+mode=block\"?",
        "X-Content-Type-Options": r"Header\s+always\s+set\s+X-Content-Type-Options\s+\"?nosniff\"?",
        "Content-Security-Policy": r"Header\s+always\s+set\s+Content-Security-Policy\s+\"?(default-src\s+'self';|frame-ancestors\s+'self')\"?"
    }

    # Check each pattern and award points for each correctly configured header
    for header, pattern in patterns.items():
        if re.search(pattern, response.response_file, re.IGNORECASE):
            score += 1
        else:
            response.check_result += f"- Missing or incorrect {header} configuration.\n"

    return score


def check_ssl_configuration(response) -> int:
    """
    Checks if the SSL configuration meets security criteria for Apache 2.4:
    1. SSLProtocol allows only secure protocols (TLSv1.2 and TLSv1.3) or disables insecure ones
    2. SSLHonorCipherOrder is set to On
    3. SSLCipherSuite is properly configured with secure ciphers
    """
    global test_counts
    test_counts += 3
    response.check_result += "### SSL Configuration\n"
    score = 0

    # Check SSLProtocol configuration
    ssl_protocol_pattern = r"^\s*SSLProtocol\s+(.*)$"
    protocol_match = re.search(ssl_protocol_pattern, response.response_file, re.MULTILINE | re.IGNORECASE)
    if protocol_match:
        protocols = protocol_match.group(1).lower().strip().split()

        # Handle both additive and subtractive approaches
        if "all" in protocols and not "-all" in protocols:
            # Subtractive approach: must disable all insecure protocols
            required_disabled = {"-sslv3", "-tlsv1", "-tlsv1.1"}
            if all(proto in [p.lower() for p in protocols] for proto in required_disabled):
                score += 1
        else:
            # Additive approach: check if only TLSv1.2 and/or TLSv1.3 are enabled
            allowed_protocols = {"+tlsv1.2", "+tlsv1.3", "tlsv1.2", "tlsv1.3"}
            disabled_base = {"-all"}

            protocols_lower = {p.lower() for p in protocols}

            # Check if configuration starts with -all and only enables secure protocols
            if (disabled_base.intersection(protocols_lower) or len(protocols_lower) == len(
                    allowed_protocols.intersection(protocols_lower))) and \
                    all(p.lower() in allowed_protocols for p in protocols):
                score += 1

        if score == 0:
            response.check_result += "- SSLProtocol should either:\n  1. Use 'all -SSLv3 -TLSv1 -TLSv1.1' or\n  2. Use '-all +TLSv1.2 +TLSv1.3'\n"
    else:
        response.check_result += "- SSLProtocol is not set\n"

    # Check if SSLHonorCipherOrder is set to On
    ssl_honor_cipher_order_pattern = r"^\s*SSLHonorCipherOrder\s+On\s*$"
    if re.search(ssl_honor_cipher_order_pattern, response.response_file, re.MULTILINE | re.IGNORECASE):
        score += 1
    else:
        response.check_result += "- SSLHonorCipherOrder must be set to On\n"

    # Check SSLCipherSuite configuration
    ssl_cipher_suite_pattern = r"^\s*SSLCipherSuite\s+(.*)$"
    cipher_suite_match = re.search(ssl_cipher_suite_pattern, response.response_file, re.MULTILINE | re.IGNORECASE)
    if cipher_suite_match:
        cipher_suite = cipher_suite_match.group(1).lower().strip()

        # Required security settings
        required_exclusions = {"!null", "!anull", "!enull", "!exp", "!rc4", "!des", "!3des", "!md5",
                               "!psk", "!dss", "!dh", "!low", "!medium"}
        required_inclusions = {"high", "tlsv1.2", "tlsv1.3", "aesgcm", "chacha20"}

        exclusions_present = {e.lower() for e in re.findall(r"!\S+", cipher_suite)}
        inclusions_present = {i.lower() for i in re.findall(r"\b\S+\b", cipher_suite)}

        if (required_exclusions.issubset(exclusions_present) and
                any(inc in inclusions_present for inc in required_inclusions)):
            score += 1
        else:
            missing_exclusions = required_exclusions - exclusions_present
            response.check_result += f"- SSLCipherSuite should exclude: {', '.join(missing_exclusions)}\n"
    else:
        response.check_result += "- SSLCipherSuite is not set\n"

    return score
