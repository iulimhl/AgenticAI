# Incident Report: Unauthorized Access and Persistence

## Executive Summary
An analysis of `auth.log` revealed a targeted compromise of host `srv-auth-01`. The attacker successfully brute-forced SSH access to the `root` account from external IP `198.51.100.77`, performed reconnaissance/downloaded a malicious script using `curl`, and established persistence by creating a backdoor privileged user account (`svc-backup`).

---

## Evidence & Timeline
- **01:05:57 - 01:06:33**: Continuous failed password attempts for `root` originating from external IP `198.51.100.77`.
- **01:12:00**: Successful SSH login (`Accepted password for root`) from `198.51.100.77`.
- **01:07:36**: `root` executed `curl` to download a payload (`http://198.51.100.77/x.sh` to `/tmp/.x`).
- **01:10:46**: Attacker created a persistent backdoor user `svc-backup` with UID=0, GID=0 (root privileges), and `/bin/bash` shell.

---

## Attacker Profile
- **IP Address**: `198.51.100.77`
- **Compromised Account**: `root` (via SSH password authentication)

---

## Post-Exploitation Activity
1. **Payload Retrieval**: Downloaded an external script (`/tmp/.x`) from the attacker's infrastructure via `curl`.
2. **Privilege Escalation / Persistence**: Created a shadow superuser account named `svc-backup` mapped to UID 0 and GID 0 with `/root` home directory.

---

## Firewall / Remediation Commands
Execute the following commands on the affected host to block the attacker and remove persistence:

```bash
# Block the attacker IP
iptables -A INPUT -s 198.51.100.77 -j DROP
ufw deny from 198.51.100.77

# Remove the backdoor user and associated files
userdel -f svc-backup
rm -rf /tmp/.x

# Invalidate active sessions / force password and SSH key rotation for root and privileged users
pkill -u root -t pts/3
```
