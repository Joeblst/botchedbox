# IPtables
## Scenario

We have a network infrastructure with the following configuration:
- Network Zones:
    - Internet: Any
    - DMZ Network: 172.16.20.0/24
    - Internal Network: 10.0.0.0/16
    - Management Network: 10.1.0.0/24

- DMZ Servers:
    - Web Server 1: 172.16.20.10
    - Web Server 2: 172.16.20.11
    - Mail Server: 172.16.20.20
    - DNS Server: 172.16.20.30
    - Load Balancer VIP: 172.16.20.100
    - Application Proxy: 172.16.20.50

Requirements:

- Internal Network Restrictions:
    - Clients in the internal network (10.0.0.0/16) can access the internet only via the application proxy (172.16.20.50).
    - The application proxy does not provide any services other than proxying internet access.
    - Internal clients can still access services in the DMZ directly.
    - The management Network can manage Server via RDP and SSH

- DMZ Servers:
    - DMZ servers can communicate directly with the internet, subject to firewall rules.

- Firewall Policy:
    - Implement a default deny-all policy.
    - Provide iptables firewall rules that enforce these requirements.
    - Include explanations for each rule.

Generate the necessary iptables firewall rules along with detailed explanations for each rule to meet these requirements.

## Firewall Setup

- Network Zones:
  - Internet: Any
  - DMZ Network: 172.16.20.0/24
  - Internal Network: 10.0.0.0/16
  - Management Network: 10.1.0.0/24

- DMZ Servers:
  - Web Server 1: 172.16.20.10
  - Web Server 2: 172.16.20.11
  - Mail Server: 172.16.20.20
  - DNS Server: 172.16.20.30
  - Load Balancer VIP: 172.16.20.100
  - Application Proxy: 172.16.20.50

### Default Policy: Deny All
```bash
iptables -P INPUT DROP
iptables -P OUTPUT DROP
iptables -P FORWARD DROP

# Allow Established
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow Loopback
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT
```

### DMZ
```bash
# Allow internal clients to access internet via Application Proxy
iptables -A FORWARD -s 10.0.0.0/16 -d 172.16.20.50 -p tcp --dport 80 -j ACCEPT
iptables -A FORWARD -s 10.0.0.0/16 -d 172.16.20.50 -p tcp --dport 443 -j ACCEPT
iptables -A FORWARD -s 10.0.0.0/16 ! -d 172.16.20.50 -o eth0 -j DROP
iptables -A FORWARD -s 10.0.0.0/16 -d 172.16.20.0/24 -j ACCEPT

# DMZ Server to Internet
iptables -A FORWARD -s 172.16.20.0/24 -o eth0 -j ACCEPT
iptables -A FORWARD -d 172.16.20.0/24 -i eth0 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# Web Servers (HTTP/HTTPS)
iptables -A FORWARD -d 172.16.20.10 -p tcp -m multiport --dports 80,443 -j ACCEPT
iptables -A FORWARD -d 172.16.20.11 -p tcp -m multiport --dports 80,443 -j ACCEPT

# Load Balancer VIP
iptables -A FORWARD -d 172.16.20.100 -p tcp -m multiport --dports 80,443 -j ACCEPT

# Mail Server (SMTP, IMAP, IMAPS)
iptables -A FORWARD -d 172.16.20.20 -p tcp -m multiport --dports 25,143,993 -j ACCEPT

# DNS Server
iptables -A FORWARD -d 172.16.20.30 -p udp --dport 53 -j ACCEPT
iptables -A FORWARD -d 172.16.20.30 -p tcp --dport 53 -j ACCEPT

# Application Proxy
iptables -A FORWARD -d 172.16.20.50 -p tcp --dport 3128 -j ACCEPT

# Allow management network to access all zones for administration
iptables -A INPUT -s 10.1.0.0/24 -d 172.16.20.0/24 -p tcp --dport 22 -j ACCEPT
iptables -A INPUT -s 10.1.0.0/24 -d 172.16.20.0/24 -p tcp --dport 3389 -j ACCEPT
```

### Logging
```bash
iptables -A INPUT -j LOG --log-prefix "INPUT DROP: " --log-level 4
iptables -A FORWARD -j LOG --log-prefix "FORWARD DROP: " --log-level 4
iptables -A OUTPUT -j LOG --log-prefix "OUTPUT DROP: " --log-level 4
```
