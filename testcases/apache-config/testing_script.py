import os
import re
import subprocess
import tempfile

from benchmark.models import Testcase


def validate_apache_config(testcase: Testcase, config: str) -> bool:
    """Validate Apache site config using a Docker container."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.conf') as temp_file:
        temp_file.write(config.encode())
        temp_file_path = temp_file.name

    container_name = "apache_temp"
    image_name = "apache-validate:2.4"

    try:
        subprocess.run(
            ["docker", "build", "-t", image_name, testcase.path],
            check=True
        )

        subprocess.run(
            ["docker", "run", "--name", container_name, "-d", image_name],
            check=True
        )

        # Copy the site config file into the container's conf/extra directory
        subprocess.run(
            ["docker", "cp", temp_file_path, f"{container_name}:/usr/local/apache2/conf/extra/site.conf"],
            check=True
        )

        # Modify the httpd.conf inside the container to include the site config
        include_line = 'Include conf/extra/site.conf\n'
        subprocess.run(
            [
                "docker", "exec", container_name, "sh", "-c",
                f"echo '{include_line}' >> /usr/local/apache2/conf/httpd.conf"
            ],
            check=True
        )

        # Check the config syntax inside the container
        result = subprocess.run(
            ["docker", "exec", container_name, "apachectl", "-t"],
            capture_output=True, text=True
        )

        if result.returncode != 0:
            print(f"Invalid Apache configuration: {result.stderr.strip()}")
            return False
        else:
            print("Apache configuration is valid.")
            return True
    except subprocess.CalledProcessError as e:
        print(f"Error during Apache config validation: {e}")
        return False
    finally:
        # Clean up: Stop and remove the container
        subprocess.run(["docker", "rm", "-f", container_name], check=False)
        # Remove the temporary config file
        os.remove(temp_file_path)


def verify(testcase: Testcase, llm_output: str) -> int:

    score = 100
    # Points for a valid apache config
    if not validate_apache_config(testcase, llm_output):
        pass

def check_default_deny(llm_output: str) -> int:
    """
    Checks if:
    1. A "Require all denied" rule is set in the <Directory /> block.
    2. An "AllowOverride None" directive is present in the same block.
    3. An "Options None" directive is present in the same block.

    Parameters:
    - llm_output (str): The configuration text to be checked.

    Returns:
    - int: 0 if all conditions are met, 1 if any condition is missing.
    """
    # Pattern to match the <Directory /> block with "Require all denied", "AllowOverride None", and "Options None"
    directory_pattern = (
        r"<Directory\s*/?\s*>\s*"           # Start of <Directory /> block
        r"(?=.*?Require\s+all\s+denied)"    # Require all denied inside the block
        r"(?=.*?AllowOverride\s+None)"      # AllowOverride None inside the block
        r"(?=.*?Options\s+None)"            # Options None inside the block
        r".*?</Directory>"                  # End of </Directory> block
    )

    # Check if all conditions are met within the <Directory /> block
    if re.search(directory_pattern, llm_output, re.DOTALL | re.IGNORECASE):
        return 0  # All directives are present
    else:
        return 1  # One or more directives are missing


def check_require_and_allowoverride(llm_output: str) -> int:
    """
    Checks if:
    1. Every <Directory> and <Location> directive contains a "Require" directive.
    2. Every "AllowOverride" directive is set to "None".

    Parameters:
    - llm_output (str): The configuration text to be checked.

    Returns:
    - int: 0 if all conditions are met, 1 if any condition is missing.
    """
    # Pattern to match <Directory> and <Location> directives
    dir_loc_pattern = r"<(Directory|Location)\b[^>]*>(.*?)</\1>"

    # Find all <Directory> and <Location> blocks
    dir_loc_directives = re.findall(dir_loc_pattern, llm_output, re.DOTALL | re.IGNORECASE)

    missing_require = []
    allowoverride_not_none = []

    for tag, contents in dir_loc_directives:
        # Check if "Require" is present
        if not re.search(r"\bRequire\b", contents, re.IGNORECASE):
            missing_require.append(tag)

        # Check if "AllowOverride" is set to "None" or is missing
        allowoverride_match = re.search(r"AllowOverride\s+(\w+)", contents, re.IGNORECASE)
        if not allowoverride_match or allowoverride_match.group(1).lower() != "none":
            allowoverride_not_none.append(tag)

    # Check if both requirements are satisfied
    if not missing_require and not allowoverride_not_none:
        return 0  # All conditions are met
    else:
        # Output any missing configurations
        if missing_require:
            print(f"Missing 'Require' directive in: {missing_require}")
        if allowoverride_not_none:
            print(f"'AllowOverride' is not set to 'None' in: {allowoverride_not_none}")
        return 1  # Conditions are missing

def check_pid_not_in_documentroot(llm_output: str) -> int:
    """
    Checks if the PidFile is located outside the DocumentRoot.

    Parameters:
    - llm_output (str): The configuration text to be checked.

    Returns:
    - int: 0 if the PidFile is outside the DocumentRoot or if the DocumentRoot/PidFile is missing,
           1 if the PidFile is located within the DocumentRoot.
    """
    # Match DocumentRoot and PidFile paths
    document_root_match = re.search(r"DocumentRoot\s+\"([^\"]+)\"", llm_output, re.IGNORECASE)
    pidfile_match = re.search(r"PidFile\s+\"([^\"]+)\"", llm_output, re.IGNORECASE)

    # Extract paths if present
    document_root = document_root_match.group(1) if document_root_match else None
    pidfile_path = pidfile_match.group(1) if pidfile_match else None

    # Check if PidFile is within DocumentRoot
    if document_root and pidfile_path:
        if pidfile_path.startswith(document_root):
            print("Error: The PidFile is located within the DocumentRoot, which is not recommended.")
            return 1  # Non-compliant: PidFile is in DocumentRoot
        else:
            return 0  # Compliant: PidFile is outside DocumentRoot
    else:
        print("DocumentRoot or PidFile not specified in the configuration.")
        return 0  # Considered compliant if either directive is missing

def check_unnecessary_auth_modules(llm_output: str) -> int:
    """
    Checks if only necessary LDAP authentication modules are enabled.

    Parameters:
    - llm_output (str): The configuration text to be checked.

    Returns:
    - int: 0 if only necessary LDAP modules are enabled, 1 if unnecessary auth modules are loaded.
    """
    # Define required modules for LDAP authentication
    required_modules = {"authnz_ldap_module", "ldap_module"}

    # Pattern to find all loaded modules
    loaded_modules = re.findall(r"LoadModule\s+(\w+)\s+modules/\w+\.so", llm_output, re.IGNORECASE)

    # Identify unnecessary auth modules
    unnecessary_auth_modules = [
        module for module in loaded_modules
        if module.startswith("auth") and module not in required_modules
    ]

    # Check if unnecessary authentication modules are present
    if unnecessary_auth_modules:
        print("The following unnecessary auth modules should be disabled:")
        for module in unnecessary_auth_modules:
            print(f"Disable {module}")
        return 1  # Non-compliant: unnecessary auth modules are enabled
    else:
        return 0  # Compliant: only necessary LDAP modules are enabled


def check_module_disabled(llm_output: str) -> int:
    """
    Checks if specified modules are disabled (either commented out or missing).

    Parameters:
    - llm_output (str): The configuration text to be checked.

    Returns:
    - int: 0 if all specified modules are disabled, 1 if any are enabled.
    """
    # List of modules that should be disabled
    disabled_modules = ["autoindex_module", "status_module"]

    # Check each module to ensure it is disabled
    for module in disabled_modules:
        # Pattern to find if the module is loaded (enabled)
        match = re.search(rf"#?\s*LoadModule\s+{module}\s+modules/\w+\.so", llm_output, re.IGNORECASE)

        # If the module is found and not commented out, return non-compliance
        if match and not match.group().strip().startswith("#"):
            print(f"{module} is enabled and should be disabled.")
            return 1  # Non-compliant: the module is enabled

    # All specified modules are disabled
    return 0  # Compliant: all specified modules are disabled

def check_user_not_root(llm_output: str) -> int:
    """
    Checks if the User and Group directives are not set to 'root'.

    Parameters:
    - llm_output (str): The configuration text to be checked.

    Returns:
    - int: 0 if both User and Group are not set to 'root', 1 if either is set to 'root'.
    """
    # Match the User directive
    user_match = re.search(r"^\s*User\s+(\w+)", llm_output, re.MULTILINE | re.IGNORECASE)
    user = user_match.group(1) if user_match else None

    # Match the Group directive
    group_match = re.search(r"^\s*Group\s+(\w+)", llm_output, re.MULTILINE | re.IGNORECASE)
    group = group_match.group(1) if group_match else None

    # Check if either User or Group is set to "root"
    if user == "root" or group == "root":
        if user == "root":
            print("Error: User is set to 'root'.")
        if group == "root":
            print("Error: Group is set to 'root'.")
        return 1  # Non-compliant: either User or Group is set to "root"

    # Compliant if neither is set to "root"
    return 0


def check_directory_options_none(llm_output: str) -> int:
    """
    Checks if the <Directory "/usr/local/apache2/htdocs"> block contains the directive "Options None".

    Parameters:
    - llm_output (str): The configuration text to be checked.

    Returns:
    - int: 0 if the <Directory "/usr/local/apache2/htdocs"> block contains "Options None", 1 if not.
    """
    # Pattern to match the <Directory "/usr/local/apache2/htdocs"> block with "Options None"
    directory_pattern = (
        r"<Directory\s+\"/usr/local/apache2/htdocs\"\s*>\s*"  # Start of <Directory> block
        r"(?=.*?Options\s+None)"  # Options None inside the block
        r".*?</Directory>"  # End of </Directory> block
    )

    # Check if the specified <Directory> block contains "Options None"
    if re.search(directory_pattern, llm_output, re.DOTALL | re.IGNORECASE):
        return 0  # Compliant: "Options None" is present
    else:
        return 1  # Non-compliant: "Options None" is missing