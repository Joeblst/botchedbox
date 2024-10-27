# Apache Config
## Config Validation

            Apache config was invalid:
            ```
            AH00526: Syntax error on line 62 of /usr/local/apache2/conf/httpd.conf:
Invalid command 'AuthzLDAPAuthoritative', perhaps misspelled or defined by a module not included in the server configuration
            ```

            ### Default Deny Directive
Missing Options in <Directory /> block.
### Directive and Locations
- AllowOverride is not set to 'None' in <Directory> block.
- AllowOverride is not set to 'None' in <Directory> block.
- Missing Require directive in <Location> block.
- AllowOverride is not set to 'None' in <Location> block.
- AllowOverride is not set to 'None' in <Location> block.
- Missing Require directive in <Location> block.
- AllowOverride is not set to 'None' in <Location> block.
- Missing Require directive in <Location> block.
- AllowOverride is not set to 'None' in <Location> block.
## PidFile is located outside the DocumentRoot.
PidFile is located inside the DocumentRoot.
### Required Modules
- The following unnecessary auth modules are not enabled:
  - Disable {module}
  - Disable {module}
  - Disable {module}
  - Disable {module}
  - Disable {module}
  - Disable {module}
### Disabled Modules
- Disable autoindex_module
- Disable status_module
### User Not Root Directives
### Directory Options
### Server Status and Info Directives
- The <Location /server-status> block is active and should be commented out.
- The <Location /server-info> block is active and should be commented out.
### Trace Disable Directives
- TraceEnable is not set to 'off'.
- No <LimitExcept> directive found in a <Directory> block.
### Security Headers
- Missing or incorrect security headers in <IfModule headers_module>.
### SSL Configuration
- SSLProtocol should allow only TLSv1.2 and TLSv1.3.
- SSLHonorCipherOrder must be set to On.
- SSLCipherSuite is not set.
