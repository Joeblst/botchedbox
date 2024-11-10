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

- Default Policy: Deny All

### Inbound Rules (Internet to DMZ)
```bash
iptables -A FORWARD -i eth0 -o eth1 -p tcp -d 172.16.20.100 --dport 80 -m state --state NEW,ESTABLISHED -j ACCEPT 
iptables -A FORWARD -i eth0 -o eth1 -p tcp -d 172.16.20.100 --dport 443 -m state --state NEW,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i eth0 -o eth1 -p tcp -d 172.16.20.20 --dport 25 -m state --state NEW,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i eth0 -o eth1 -p udp -d 172.16.20.30 --dport 53 -m state --state NEW,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i eth0 -o eth1 -p tcp -d 172.16.20.30 --dport 53 -m state --state NEW,ESTABLISHED -j ACCEPT
```

### Outbound Rules (DMZ to Internet)
```bash
iptables -A FORWARD -i eth1 -o eth0 -p tcp -s 172.16.20.20 --dport 25 -m state --state NEW,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i eth1 -o eth0 -p tcp -s 172.16.20.30 --dport 53 -m state --state NEW,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i eth1 -o eth0 -p udp -s 172.16.20.30 --dport 53 -m state --state NEW,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i eth1 -o eth0 -p tcp -s 172.16.20.0/24 --dport 80 -m state --state NEW,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i eth1 -o eth0 -p tcp -s 172.16.20.0/24 --dport 443 -m state --state NEW,ESTABLISHED -j ACCEPT
```

### DMZ to Internal Rules (Very Restricted)
```bash
iptables -A FORWARD -i eth1 -o eth2 -p tcp -s 172.16.20.0/24 -d 10.0.0.0/16 --dport 1433 -m state --state NEW,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i eth1 -o eth2 -p tcp -s 172.16.20.0/24 -d 10.0.0.0/16 --dport 3306 -m state --state NEW,ESTABLISHED -j ACCEPT
```

### Management Access
```bash
iptables -A FORWARD -i eth2 -o eth1 -p tcp -s 10.1.0.0/24 -d 172.16.20.0/24 --dport 22 -m state --state NEW,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i eth2 -o eth1 -p tcp -s 10.1.0.0/24 -d 172.16.20.0/24 --dport 3389 -m state --state NEW,ESTABLISHED -j ACCEPT
```

### Rate Limiting Rules
```bash
iptables -A FORWARD -p tcp --dport 80 -m limit --limit 25/minute --limit-burst 100 -j ACCEPT
iptables -A FORWARD -p tcp --dport 443 -m limit --limit 25/minute --limit-burst 100 -j ACCEPT
```

### Log Dropped Packets
```bash
iptables -A FORWARD -j LOG --log-prefix "IPTables-Dropped: "
iptables -A FORWARD -j DROP
```
