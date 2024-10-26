import os
import re
import subprocess
import tempfile
import logging

from benchmark.models import Testcase


logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def validate_apache_config(testcase: Testcase, config: str) -> bool:
    """Validate Apache site config using a Docker container."""
    container_name = "apache_temp"
    image_name = "apache-validate:2.4"

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.conf') as temp_file:
            temp_file.write(config.encode())
            temp_file_path = temp_file.name

        # Build the Docker image
        build_result = subprocess.run(
            ["docker", "build", "-t", image_name, testcase.path],
            check=True,
            capture_output=True,
            text=True
        )
        logging.debug(f"Docker build output: {build_result.stdout}")

        # Run the Docker container
        run_result = subprocess.run(
            ["docker", "run", "--name", container_name, "-d", image_name],
            check=True,
            capture_output=True,
            text=True
        )
        logging.debug(f"Docker run output: {run_result.stdout}")

        # Copy the site config file into the container's conf/extra directory
        cp_result = subprocess.run(
            ["docker", "cp", temp_file_path, f"{container_name}:/usr/local/apache2/conf/extra/site.conf"],
            check=True,
            capture_output=True,
            text=True
        )
        logging.debug(f"Docker cp output: {cp_result.stdout}")

        # Modify the httpd.conf inside the container to include the site config
        include_line = 'Include conf/extra/site.conf'
        exec_result = subprocess.run(
            [
                "docker", "exec", container_name, "sh", "-c",
                f"echo '{include_line}' >> /usr/local/apache2/conf/httpd.conf"
            ],
            check=True,
            capture_output=True,
            text=True
        )
        logging.debug(f"Docker exec output: {exec_result.stdout}")

        # Check the config syntax inside the container
        test_result = subprocess.run(
            ["docker", "exec", container_name, "apachectl", "-t"],
            capture_output=True, text=True
        )
        logging.debug(f"Apache config test output: {test_result.stdout}")
        logging.debug(f"Apache config test error output: {test_result.stderr}")

        if test_result.returncode != 0:
            logging.error(f"Invalid Apache configuration: {test_result.stderr.strip()}")
            return False
        else:
            logging.info("Apache configuration is valid.")
            return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Error during Apache config validation: {e.stderr}")
        return False
    finally:
        # Clean up: Stop and remove the container
        subprocess.run(["docker", "rm", "-f", container_name], check=False)
        # Remove the temporary config file
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        # Optionally, remove the image to avoid clutter
        subprocess.run(["docker", "rmi", image_name], check=False)


def verify(testcase: Testcase, llm_output: str) -> int:

    score = 100
    # Points for a valid apache config
    if not validate_apache_config(testcase, llm_output):
        pass


def check_root_directory(llm_output: str) -> int:
    """
    Checks if:
    1. A "Require all denied" rule is set in the <Directory /> block.
    2. An "AllowOverride None" directive is present in the same block.
    3. An "Options None" directive is present in the same block.
    """
    # Pattern to match the <Directory /> block
    match = re.search(r"<Directory\s*/\s*>(.*?)</Directory>", llm_output, re.DOTALL | re.IGNORECASE)
    if match:
        directory_content = match.group(1)
        # Check for "Require all denied"
        if not re.search(r"^\s*Require\s+all\s+denied\s*$", directory_content, re.MULTILINE | re.IGNORECASE):
            logging.warning("Missing 'Require all denied' in <Directory /> block.")
            return 1
        # Check for "AllowOverride None"
        if not re.search(r"^\s*AllowOverride\s+None\s*$", directory_content, re.MULTILINE | re.IGNORECASE):
            logging.warning("Missing 'AllowOverride None' in <Directory /> block.")
            return 1
        # Check for "Options None"
        if not re.search(r"^\s*Options\s+None\s*$", directory_content, re.MULTILINE | re.IGNORECASE):
            logging.warning("Missing 'Options None' in <Directory /> block.")
            return 1
        # All conditions met
        return 0
    else:
        logging.warning("No <Directory /> block found.")
        return 1


def check_directories_locations(llm_output: str) -> int:
    """
    Checks if:
    1. Every <Directory> and <Location> directive contains a "Require" directive.
    2. Every "AllowOverride" directive is set to "None" in those blocks.
    """
    # Pattern to match <Directory> and <Location> blocks
    pattern = r"<(Directory|Location)(?:\s+[^>]*)?>(.*?)</\1>"
    matches = re.findall(pattern, llm_output, re.DOTALL | re.IGNORECASE)

    all_good = True

    for tag, content in matches:
        # Check for "Require"
        if not re.search(r"^\s*Require\b", content, re.MULTILINE | re.IGNORECASE):
            logging.warning(f"Missing 'Require' directive in <{tag}> block.")
            all_good = False

        # Check "AllowOverride None"
        allowoverride_matches = re.findall(r"^\s*AllowOverride\s+(\S+)", content, re.MULTILINE | re.IGNORECASE)
        if not allowoverride_matches or any(val.lower() != "none" for val in allowoverride_matches):
            logging.warning(f"'AllowOverride' is not set to 'None' in <{tag}> block.")
            all_good = False

        # Check "AllowOverride None"
        options_matches = re.findall(r"^\s*Options\s+(\S+)", content, re.MULTILINE | re.IGNORECASE)
        if options_matches and any(val.lower() == "Includes" and not val.lower() != "-Includes" for val in allowoverride_matches):
            logging.warning(f"'Options' is set to 'Includes' in <{tag}> block.")
            all_good = False

    return 0 if all_good else 1


def check_pid_not_in_documentroot(llm_output: str) -> int:
    """
    Checks if the PidFile is located outside the DocumentRoot.
    """
    # Match DocumentRoot and PidFile paths
    document_root_match = re.search(r"DocumentRoot\s+\"([^\"]+)\"", llm_output, re.IGNORECASE)
    pidfile_match = re.search(r"PidFile\s+\"([^\"]+)\"", llm_output, re.IGNORECASE)

    # Extract paths if present
    document_root = document_root_match.group(1) if document_root_match else None
    pidfile_path = pidfile_match.group(1) if pidfile_match else None

    # Check if PidFile is within DocumentRoot
    if document_root and pidfile_path:
        if os.path.commonpath([pidfile_path]) == os.path.commonpath([document_root, pidfile_path]):
            logging.warning("The PidFile is located within the DocumentRoot, which is not recommended.")
            return 1  # Non-compliant: PidFile is in DocumentRoot
        else:
            return 0  # Compliant: PidFile is outside DocumentRoot
    else:
        logging.info("DocumentRoot or PidFile not specified in the configuration.")
        return 0  # Considered compliant if either directive is missing


def check_unnecessary_auth_modules(llm_output: str) -> int:
    """
    Checks if only necessary LDAP authentication modules are enabled.
    """
    # Define required modules for LDAP authentication
    required_modules = {"authnz_ldap_module", "ldap_module"}

    # Pattern to find all loaded modules
    loaded_modules = re.findall(r"^\s*LoadModule\s+(\w+)\s+modules/\w+\.so", llm_output, re.MULTILINE | re.IGNORECASE)

    # Identify unnecessary auth modules
    unnecessary_auth_modules = [
        module for module in loaded_modules
        if module.startswith("auth") and module not in required_modules
    ]

    # Check if unnecessary authentication modules are present
    if unnecessary_auth_modules:
        logging.warning("The following unnecessary auth modules should be disabled:")
        for module in unnecessary_auth_modules:
            logging.warning(f"Disable {module}")
        return 1  # Non-compliant: unnecessary auth modules are enabled
    else:
        return 0  # Compliant: only necessary LDAP modules are enabled


def check_module_disabled(llm_output: str) -> int:
    """
    Checks if specified modules are disabled (either commented out or missing).
    """
    # List of modules that should be disabled
    disabled_modules = ["autoindex_module", "status_module"]

    # Check each module to ensure it is disabled
    for module in disabled_modules:
        # Pattern to find if the module is loaded (enabled)
        match = re.search(rf"^\s*LoadModule\s+{module}\s+modules/\w+\.so", llm_output, re.MULTILINE | re.IGNORECASE)

        # If the module is found and not commented out, return non-compliance
        if match:
            logging.warning(f"{module} is enabled and should be disabled.")
            return 1  # Non-compliant: the module is enabled

    # All specified modules are disabled
    return 0  # Compliant: all specified modules are disabled


def check_user_not_root(llm_output: str) -> int:
    """
    Checks if the User and Group directives are not set to 'root'.
    """
    # Match the User directive
    user_match = re.search(r"^\s*User\s+(\S+)", llm_output, re.MULTILINE | re.IGNORECASE)
    if user_match and user_match.group(1).lower() == "root":
        logging.warning("User is set to 'root'.")
        return 1

    # Match the Group directive
    group_match = re.search(r"^\s*Group\s+(\S+)", llm_output, re.MULTILINE | re.IGNORECASE)
    if group_match and group_match.group(1).lower() == "root":
        logging.warning("Group is set to 'root'.")
        return 1

    return 0  # Compliant if neither is set to "root"


def check_directory_options_no_includes(llm_output: str) -> int:
    """
    Checks if every <Directory> block does not include "Includes" or "-Includes" in the "Options" directive.

    Parameters:
    - llm_output (str): The configuration text to be checked.

    Returns:
    - int: 0 if no <Directory> block contains "Includes" or "-Includes" in "Options", 1 if any do.
    """
    # Pattern to match all <Directory> blocks
    directory_pattern = r"<Directory\s+[^>]+>(.*?)</Directory>"
    directory_blocks = re.findall(directory_pattern, llm_output, re.DOTALL | re.IGNORECASE)

    # Check each <Directory> block for "Options" with "Includes" or "-Includes"
    for directory_content in directory_blocks:
        # Search for Options line and check if it contains "Includes" or "-Includes"
        options_match = re.search(r"^\s*Options\s+.*\b(Includes|-Includes)\b", directory_content, re.MULTILINE | re.IGNORECASE)
        if options_match:
            print('Error: "Options" directive contains "Includes" or "-Includes" in a <Directory> block.')
            return 1  # Non-compliant: Includes or -Includes found

    # Compliant: No "Includes" or "-Includes" found in any <Directory> block
    return 0


def check_server_status_and_info_commented_out(llm_output: str) -> int:
    """
    Checks if the <Location /server-status> and <Location /server-info> blocks are commented out or absent.

    Parameters:
    - llm_output (str): The configuration text to be checked.

    Returns:
    - int: 0 if both <Location /server-status> and <Location /server-info> blocks are commented out or not present,
           1 if either is active.
    """
    # Patterns to match the <Location /server-status> and <Location /server-info> blocks
    server_status_pattern = r"(?<!#)\s*<Location\s+/server-status>\s*.*?</Location>"
    server_info_pattern = r"(?<!#)\s*<Location\s+/server-info>\s*.*?</Location>"

    # Check if the <Location /server-status> block is present and not commented out
    if re.search(server_status_pattern, llm_output, re.DOTALL | re.IGNORECASE):
        print("Error: The <Location /server-status> block is active and should be commented out.")
        return 1  # Non-compliant: The /server-status block is active

    # Check if the <Location /server-info> block is present and not commented out
    if re.search(server_info_pattern, llm_output, re.DOTALL | re.IGNORECASE):
        print("Error: The <Location /server-info> block is active and should be commented out.")
        return 1  # Non-compliant: The /server-info block is active

    return 0  # Compliant: Both blocks are commented out or not present


def check_trace_disabled(llm_output: str) -> int:
    """
    Checks if TRACE is disabled by verifying:
    1. 'TraceEnable' is set to 'off', or
    2. Every <Directory> block contains a <LimitExcept> directive that disables 'TRACE'.

    Parameters:
    - llm_output (str): The configuration text to be checked.

    Returns:
    - int: 0 if TRACE is disabled properly, 1 if TRACE is enabled or not properly disabled.
    """
    # Check if 'TraceEnable off' is present
    trace_enable_pattern = r"^\s*TraceEnable\s+off\s*$"
    if re.search(trace_enable_pattern, llm_output, re.MULTILINE | re.IGNORECASE):
        return 0  # Compliant: TraceEnable is set to off globally

    # Pattern to match all <Directory> blocks
    directory_pattern = r"<Directory\s+[^>]+>(.*?)</Directory>"
    directory_blocks = re.findall(directory_pattern, llm_output, re.DOTALL | re.IGNORECASE)

    # Check if each <Directory> block has <LimitExcept> disabling TRACE
    for directory_content in directory_blocks:
        # Look for <LimitExcept> blocks
        limit_except_match = re.search(r"<LimitExcept\s+([^>]+)>(.*?)</LimitExcept>", directory_content,
                                       re.DOTALL | re.IGNORECASE)
        if limit_except_match:
            # Get the list of methods allowed by <LimitExcept>
            allowed_methods = limit_except_match.group(1).split()
            if "TRACE" in allowed_methods:
                print("Error: TRACE is allowed in a <LimitExcept> directive, which is not recommended.")
                return 1  # Non-compliant: TRACE is explicitly allowed
        else:
            print("Error: No <LimitExcept> directive found in a <Directory> block.")
            return 1  # Non-compliant: <LimitExcept> is missing

    # Compliant if no issues were found
    return 0
