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
    - Clients in the internal network (10.0.0.0/16) can access the internet only via the application proxy (
      172.16.20.50).
    - The application proxy does not provide any services other than proxying internet access.
    - Internal clients can still access services in the DMZ directly.
    - The management Network can manage Server via RDP and SSH

- DMZ Servers:
    - DMZ servers can communicate directly with the internet, subject to firewall rules.

- Firewall Policy:
    - Implement a default deny-all policy.
    - Provide iptables firewall rules that enforce these requirements.
    - Include explanations for each rule.

Generate the necessary iptables firewall rules along with detailed explanations for each rule to meet these
requirements.

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
#!/usr/sbin/nft -f

flush ruleset

table ip filter {
    chain input {
        type filter hook input priority 0; policy drop

        # Allow established connections
        ct state {established, related} accept

        # Allow loopback
        iifname "lo" accept
    }

    chain output {
        type filter hook output priority 0; policy drop

        # Allow established connections
        ct state {established, related} accept

        # Allow loopback
        oifname "lo" accept
    }

    chain forward {
        type filter hook forward priority 0; policy drop

        # Allow established connections
        ct state {established, related} accept

        # DMZ Management Access
        ip saddr 10.1.0.0/24 ip daddr 172.16.20.0/24 tcp dport 22 accept
        ip saddr 10.1.0.0/24 ip daddr 172.16.20.0/24 tcp dport 3389 accept
        ip saddr 10.0.0.0/16 ip daddr 172.16.20.0/24 tcp dport { 22, 3389 } drop

        # Internal clients to Application Proxy
        ip saddr 10.0.0.0/16 ip daddr 172.16.20.50 tcp dport any accept
        ip saddr 10.0.0.0/16 ip daddr 172.16.20.0/24 accept
        ip saddr 10.0.0.0/16 ip daddr != 172.16.20.50 oifname "eth0" drop
        ip saddr 172.16.20.0/24 ip daddr 10.0.0.0/16 oifname "eth0" drop

        # Web Servers
        iifname "eth0" ip daddr 172.16.20.0/24 ct state {established, related} accept
        ip daddr 172.16.20.100 tcp dport { 80, 443 } accept
        ip saddr 172.16.20.100 ip daddr 172.16.20.10 tcp dport { 80, 443 } accept
        ip saddr 172.16.20.100 ip daddr 172.16.20.11 tcp dport { 80, 443 } accept
        ip daddr 172.16.20.10 drop
        ip daddr 172.16.20.11 drop

        # DMZ to Internet
        ip saddr 172.16.20.0/24 oifname "eth0" accept

        # Mail Server
        ip daddr 172.16.20.20 tcp dport { 25, 143, 993 } accept

        # DNS Server
        ip daddr 172.16.20.30 tcp dport 53 accept
        ip daddr 172.16.20.30 udp dport 53 accept

        # Application Proxy
        ip daddr 172.16.20.50 tcp dport 3128 accept
    }
}
```
