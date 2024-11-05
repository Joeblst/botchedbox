import logging
import math
from typing import List, Dict

from benchmark.models import Response, Testcase
from test_helper.smb_config_helper import SambaShare, SambaConfig, SambaConfigParser

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
test_count = 0


def verify(testcase: Testcase, response: Response) -> int:
    """Verify SMB configuration and return a score."""
    global test_count
    score = 0
    issues = []

    try:
        config = SambaConfigParser().parse_string(response.response_file)
    except Exception as e:
        response.check_result = f"### SMB Configuration Error\n\n```\n{str(e)}\n```"
        response.set_valid(False)
        return 0

    response.set_valid(True)

    # Global security checks
    global_checks = [
        (check_authentication, "Authentication Settings"),
        (check_protocol_security, "Protocol Security"),
        (check_encryption, "Encryption Settings"),
        (check_logging, "Logging Configuration"),
        (check_acl_security, "ACL Security"),
        (check_symlink_security, "Symlink Security"),
        (check_ldap_security, "LDAP Security"),
        (check_printer_security, "Printer Security"),
        (check_general_security, "General Security Settings")
    ]

    # Run global checks
    for check_func, check_name in global_checks:
        check_score = check_func(config.global_options, issues)
        score += check_score

    # Share-specific checks
    for share in config.shares:
        share_checks = [
            (check_share_security, "Share Security Settings"),
            (check_share_permissions, "Share Permissions"),
            (check_share_access, "Share Access Control"),
            (check_shadow_copy_security, "Shadow Copy Security"),
            (check_recycle_bin_security, "Recycle Bin Security"),
            (check_vfs_security, "VFS Security"),
            (check_audit_configuration, "Audit Configuration")
        ]
        for check_func, check_name in share_checks:
            check_score = check_func(share, config, issues)
            score += check_score

    if issues:
        response.check_result = "### Configuration Issues Found\n\n" + "\n".join(issues)
    else:
        response.check_result = "### Configuration Validation Successful\n\nAll security checks passed."

    if test_count == 0:
        return 0

    score = (score / test_count) * 100
    return math.floor(score)

def check_encryption(global_options: Dict[str, str], issues: List[str]) -> int:
    """Check encryption settings."""
    global test_count
    test_count += 2
    score = 0

    # SMB encryption check
    encryption = global_options.get('smb encrypt', '').lower()
    if encryption != 'required':
        issues.append("- SMB encryption should be set to 'required' (current: " + (encryption if encryption else 'not set') + ")")
    else:
        score += 1

    # Cipher configuration - block weak ciphers
    ciphers = global_options.get('server ciphers', '').lower()
    weak_ciphers = {'rc4', '3des', 'des', 'aes-128-cbc'}
    if ciphers:
        if any(weak in ciphers for weak in weak_ciphers):
            issues.append("- Weak ciphers detected in configuration")
        else:
            score += 1
    else:
        score += 1

    return score

def check_share_security(share: SambaShare, samba_config: SambaConfig, issues: List[str]) -> int:
    """Check security settings for individual shares."""
    global test_count
    test_count += 2
    score = 0

    # Basic share security checks
    security_checks = {
        'guest ok': ('no', "Guest access should be disabled"),
        'browseable': ('no', "Share should not be browseable"),
    }

    for option, (secure_value, message) in security_checks.items():
        value = samba_config.get_option_value(option, share)
        if value != secure_value:
            issues.append(f"- Share [{share.name}]: {message}")
        else:
            score += 1

    return score

def check_share_permissions(share: SambaShare, samba_config: SambaConfig, issues: List[str]) -> int:
    """Check file and directory permissions for shares."""
    global test_count
    test_count += 4
    score = 0

    # Check for dangerous path variables
    path = share.options.get('path', '')
    if '%' in path:
        issues.append(f"- Share [{share.name}]: Path contains variables which could enable traversal")
    else:
        score += 1

    # Check permission masks
    mask_checks = {
        'create mask': (0o644, "Create mask too permissive"),
        'directory mask': (0o755, "Directory mask too permissive"),
        'force create mode': (0o600, "Force create mode not restrictive enough")
    }

    for mask_type, (max_value, message) in mask_checks.items():
        value = samba_config.get_option_value(mask_type, share)
        if not value or not value.isdigit():
            issues.append(f"- Share [{share.name}]: {mask_type} not set")
        elif int(value, 8) > max_value:
            issues.append(f"- Share [{share.name}]: {message}")
        else:
            score += 1

    return score

def check_share_access(share: SambaShare, samba_config: SambaConfig, issues: List[str]) -> int:
    """Check access control settings and group permissions for shares."""
    global test_count
    test_count += 6
    score = 0

    # Check for proper user/group restrictions
    if 'valid users' not in share.options and 'valid users' not in samba_config.global_options:
        issues.append(f"- Share [{share.name}]: Must specify valid users")
    else:
        score += 1

    # Share-specific group validations
    if share.name == 'documents':
        score += check_documents_share_access(share, samba_config, issues)
    elif share.name == 'financials':
        score += check_financials_share_access(share, samba_config, issues)
    elif share.name == 'home_directories':
        score += check_home_directories_access(share, samba_config, issues)
    elif share.name == 'applications':
        score += check_applications_share_access(share, samba_config, issues)
    else:
        score += 4

    # Check for dangerous settings
    if 'force user' in share.options or 'force user' in samba_config.global_options:
        issues.append(f"- Share [{share.name}]: force user setting is dangerous")
    else:
        score += 1

    return score


def check_documents_share_access(share: SambaShare, samba_config: SambaConfig, issues: List[str]) -> int:
    """Validate documents share access permissions."""
    score = 0

    # Valid users check
    valid_users = set(samba_config.get_option_value('valid users', share).split())
    if valid_users != {'@staff'}:
        issues.append(f"- Share [documents]: Invalid valid users configuration. Should only be @staff")
    else:
        score += 1

    # Write list check
    write_users = set(samba_config.get_option_value('write list', share).split())
    if write_users != {'@staff'}:
        issues.append(f"- Share [documents]: Invalid write list. Should only be @staff")
    else:
        score += 1

    # Check for unnecessary groups
    all_groups = set()
    for option in ['valid users', 'write list', 'read list']:
        groups = samba_config.get_option_value(option, share).split()
        all_groups.update(group for group in groups if group.startswith('@'))

    unexpected_groups = all_groups - {'@staff'}
    if unexpected_groups:
        issues.append(f"- Share [documents]: Unexpected groups found: {', '.join(unexpected_groups)}")
    else:
        score += 1

    return score

def check_financials_share_access(share: SambaShare, samba_config: SambaConfig, issues: List[str]) -> int:
    """Validate financials share access permissions."""
    score = 0

    # Valid users check
    valid_users = set(samba_config.get_option_value('valid users', share).split())
    if valid_users != {'@finances'}:
        issues.append(f"- Share [financials]: Invalid valid users configuration. Should be @staff and @finances")
    else:
        score += 1

    # Write list check
    write_users = set(samba_config.get_option_value('write list', share).split())
    if write_users != {'@finances'}:
        issues.append(f"- Share [financials]: Invalid write list. Should be @finances and @admin")
    else:
        score += 1

    # Check for unnecessary groups
    all_groups = set()
    for option in ['valid users', 'write list', 'read list']:
        groups = samba_config.get_option_value(option, share).split()
        all_groups.update(group for group in groups if group.startswith('@'))

    unexpected_groups = all_groups - {'@finances'}
    if unexpected_groups:
        issues.append(f"- Share [financials]: Unexpected groups found: {', '.join(unexpected_groups)}")
    else:
        score += 1

    return score

def check_home_directories_access(share: SambaShare, samba_config: SambaConfig, issues: List[str]) -> int:
    """Validate home directories access permissions."""
    score = 0

    # Valid users check - should only be %S (current service name)
    valid_users = samba_config.get_option_value('valid users', share).strip()
    if valid_users != '%s':
        issues.append(f"- Share [home_directories]: Invalid valid users configuration. Should be %S")
    else:
        score += 1

    # Check for any group access (should be none)
    for option in ['valid users', 'write list', 'read list']:
        groups = [g for g in samba_config.get_option_value(option, share).split() if g.startswith('@')]
        if groups:
            issues.append(f"- Share [home_directories]: Unexpected group access found in {option}: {', '.join(groups)}")
            break
    else:
        score += 1

    # Check for proper variable usage
    if '%u' not in share.options.get('path', ''):
        issues.append(f"- Share [home_directories]: Path should use %U variable")
    else:
        score += 1

    return score

def check_applications_share_access(share: SambaShare, samba_config: SambaConfig, issues: List[str]) -> int:
    """Validate applications share access permissions."""
    score = 0

    # Valid users check
    valid_users = set(samba_config.get_option_value('valid users', share).split())
    if valid_users != {'@staff', '@admins'}:
        issues.append(f"- Share [applications]: Invalid valid users configuration. Should be @staff and @admins")
    else:
        score += 1

    # Write list check
    write_users = set(samba_config.get_option_value('write list', share).split())
    if write_users != {'@admins'}:
        issues.append(f"- Share [applications]: Invalid write list. Should only be @admins")
    else:
        score += 1

    # Admin users check
    admin_users = set(samba_config.get_option_value('admin users', share).split())
    if admin_users != {'@admins'}:
        issues.append(f"- Share [applications]: Invalid admin users configuration. Should only be @admins")
    else:
        score += 1

    # Check for unnecessary groups
    all_groups = set()
    for option in ['valid users', 'write list', 'read list', 'admin users']:
        groups = samba_config.get_option_value(option, share).split()
        all_groups.update(group for group in groups if group.startswith('@'))

    unexpected_groups = all_groups - {'@staff', '@admins'}
    if unexpected_groups:
        issues.append(f"- Share [applications]: Unexpected groups found: {', '.join(unexpected_groups)}")
    else:
        score += 1

    return score


def check_authentication(global_options: Dict[str, str], issues: List[str]) -> int:
    """Check authentication-related settings."""
    global test_count
    test_count += 5
    score = 0

    auth_checks = {
        'security': {
            'values': ('user', 'ads'),
            'message': "Security mode must be 'user' or 'ads'"
        },
        'map to guest': {
            'values': ('never',),
            'message': "Guest mapping must be set to 'never'"
        },
        'encrypt passwords': {
            'values': ('yes',),
            'message': "Password encryption must be enabled"
        },
        'guest ok': {
            'values': ('no',),
            'message': "Global guest access must be disabled"
        }
    }

    for option, check in auth_checks.items():
        value = global_options.get(option, '').lower()
        if not value or value not in check['values']:
            issues.append(f"- {check['message']} (current: {value if value else 'not set'})")
        else:
            score += 1

    # Check for password policies
    if 'password level' not in global_options or int(global_options.get('password level', '0')) < 8:
        issues.append("- Password complexity requirements not properly configured")
    else:
        score += 1

    return score


def check_protocol_security(global_options: Dict[str, str], issues: List[str]) -> int:
    """Check protocol-related security settings."""
    global test_count
    test_count += 4
    score = 0

    # Protocol version checks
    min_protocol = global_options.get('server min protocol', '').upper()
    if min_protocol != 'SMB3':
        issues.append(f"- Minimum protocol version should be SMB3 (current: {min_protocol})")
    else:
        score += 1

    # Signing requirements
    signing_checks = {
        'server signing': 'mandatory',
        'client signing': 'mandatory',
        'smb encrypt': 'required'
    }

    for option, required_value in signing_checks.items():
        value = global_options.get(option, '').lower()
        if value != required_value:
            issues.append(f"- {option} should be {required_value} (current: {value if value else 'not set'})")
        else:
            score += 1

    return score


def check_acl_security(global_options: Dict[str, str], issues: List[str]) -> int:
    """Check ACL-related security settings."""
    global test_count
    test_count += 4
    score = 0

    acl_checks = {
        'inherit acls': 'no',
        'inherit permissions': 'no',
        'inherit owner': 'no',
        'nt acl support': 'yes'
    }

    for option, required_value in acl_checks.items():
        value = global_options.get(option, '').lower()
        if value != required_value:
            issues.append(f"- {option} should be {required_value} (current: {value if value else 'not set'})")
        else:
            score += 1

    return score


def check_symlink_security(global_options: Dict[str, str], issues: List[str]) -> int:
    """Check symlink-related security settings."""
    global test_count
    test_count += 3
    score = 0

    symlink_checks = {
        'wide links': 'no',
        'follow symlinks': 'no',
        'unix extensions': 'yes'
    }

    for option, required_value in symlink_checks.items():
        value = global_options.get(option, '').lower()
        if value != required_value:
            issues.append(f"- {option} should be {required_value} (current: {value if value else 'not set'})")
        else:
            score += 1

    return score


def check_ldap_security(global_options: Dict[str, str], issues: List[str]) -> int:
    """Check LDAP-related security settings."""
    global test_count
    test_count += 3
    score = 0

    if 'passdb backend' in global_options and 'ldapsam:' in global_options['passdb backend']:
        ldap_checks = {
            'ldap ssl': ('yes', 'start_tls'),
            'ldap timeout': None,
            'ldap connection timeout': None
        }

        for option, required_values in ldap_checks.items():
            value = global_options.get(option, '').lower()
            if required_values and value not in required_values:
                issues.append(f"- {option} not properly configured (current: {value if value else 'not set'})")
            elif not required_values and not value:
                issues.append(f"- {option} must be set")
            else:
                score += 1
    else:
        score += 3

    return score


def check_printer_security(global_options: Dict[str, str], issues: List[str]) -> int:
    """Check printer-related security settings."""
    global test_count
    test_count += 1
    score = 0

    printer_checks = [
        'load printers',
        'printing',
        'printcap name'
    ]

    present = False
    for option in printer_checks:
        value = global_options.get(option, '').lower()
        if value and value != 'no':
            present = True
    if present:
        issues.append(f"- Unnecessary printing service exposure")
    else:
        score += 1

    return score


def check_logging(global_options: Dict[str, str], issues: List[str]) -> int:
    """Check logging configuration."""
    global test_count
    test_count += 2
    score = 0

    # Check log level
    log_level = global_options.get('log level', '0')
    if not log_level.isdigit() or int(log_level) < 3:
        issues.append("- Log level should be at least 3 for security events")
    else:
        score += 1

    # Check log size and rotation
    if 'max log size' not in global_options or int(global_options.get('max log size', '0')) < 1000:
        issues.append("- Max log size should be at least 1000 KB")
    else:
        score += 1

    return score


def check_shadow_copy_security(share: SambaShare, samba_config: SambaConfig, issues: List[str]) -> int:
    """Check shadow copy configuration security."""
    global test_count
    test_count += 2
    score = 0

    if 'shadow_copy2' in share.options.get('vfs objects', ''):
        # Check for exposed snapshot directory
        if 'shadow:snapdir' in share.options and '/.' not in share.options['shadow:snapdir']:
            issues.append(f"- Share [{share.name}]: Shadow copy snapdir should be hidden")
        else:
            score += 1

        # Check for quotas
        if 'shadow:snapsize' not in share.options:
            issues.append(f"- Share [{share.name}]: Shadow copy size limit not set")
        else:
            score += 1
    else:
        score += 2

    return score


def check_recycle_bin_security(share: SambaShare, samba_config: SambaConfig, issues: List[str]) -> int:
    """Check recycle bin configuration security."""
    global test_count
    test_count += 3
    score = 0

    if 'recycle' in share.options.get('vfs objects', ''):
        recycle_checks = {
            'recycle:repository': lambda x: '/.' in x,
            'recycle:maxsize': lambda x: x.isdigit() and int(x) > 0,
            'recycle:touch': lambda x: x.lower() == 'yes'
        }

        for option, check_func in recycle_checks.items():
            value = share.options.get(option)
            if not value or not check_func(value):
                issues.append(f"- Share [{share.name}]: {option} not properly configured")
            else:
                score += 1
    else:
        score += 3  # Skip checks if recycle bin not enabled

    return score


def check_vfs_security(share: SambaShare, samba_config: SambaConfig, issues: List[str]) -> int:
    """Check VFS module security configuration."""
    global test_count
    test_count += 2
    score = 0

    vfs_objects = share.options.get('vfs objects', '').split()

    # Check for required security modules
    if 'acl_xattr' not in vfs_objects:
        issues.append(f"- Share [{share.name}]: acl_xattr VFS module should be enabled")
    else:
        score += 1

    # Check for potentially dangerous modules
    dangerous_modules = {'streams_xattr', 'catia', 'fruit'}
    if any(module in vfs_objects for module in dangerous_modules):
        issues.append(f"- Share [{share.name}]: Contains potentially dangerous VFS modules")
    else:
        score += 1

    return score


def check_audit_configuration(share: SambaShare, samba_config: SambaConfig, issues: List[str]) -> int:
    """Check audit configuration security."""
    global test_count
    test_count += 3
    score = 0

    if 'full_audit' in samba_config.get_option_value('vfs objects', share):
        audit_checks = {
            'full_audit:success': lambda x: all(
                op in x for op in ['connect', 'disconnect', 'mkdir', 'rmdir', 'read', 'write', 'unlink']),
            'full_audit:failure': lambda x: all(
                op in x for op in ['connect', 'disconnect', 'mkdir', 'rmdir', 'read', 'write', 'unlink']),
            'full_audit:priority': lambda x: x in ['alert', 'critical', 'error']
        }

        for option, check_func in audit_checks.items():
            value = samba_config.get_option_value(option, share)
            if not value or not check_func(value):
                issues.append(f"- Share [{share.name}]: {option} not properly configured")
            else:
                score += 1
    else:
        issues.append(f"- Share [{share.name}]: Audit module should be enabled")

    return score


def check_general_security(global_options: Dict[str, str], issues: List[str]) -> int:
    """Check general security settings."""
    global test_count
    test_count += 4
    score = 0

    checks = [
        ('strict sync', 'yes', "Strict sync should be enabled"),
        ('strict locking', 'yes', "Strict locking should be enabled"),
        ('server multi channel support', 'yes', "Multi-channel support should be enabled"),
        ('use sendfile', 'no', "Sendfile should be disabled for security")
    ]

    for option, required_value, message in checks:
        value = global_options.get(option, '').lower()
        if value != required_value:
            issues.append(f"- {message}")
        else:
            score += 1

    return score