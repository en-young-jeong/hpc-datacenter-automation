# hpc-datacenter-automation
## Project Overview
This project demonstrates advanced data center network automation using Python with Netmiko, Ansible Playbook (YAML), and Jinja2 templates. It automates the end-to-end deployment, optimization, and state-driven auditing of a high-performance computing (HPC) Spine-Leaf network fabric, utilizing standard eBGP Underlay and VXLAN EVPN Overlay architectures.

## Features
* **Decoupled Architecture:** Use a Single Source of Truth (`inventory.yaml`) to separate multi-tenant parameters and topology maps from Python deployment logic.
* **Idempotent Operations:** Declarative validation checks before modifying SSH security vectors and device banners to prevent redundant deployment state errors.
* **Concurrent Execution & Logging:** Spawns asynchronous worker threads to interact with multiple infrastructure nodes simultaneously, dramatically accelerating automation speeds while maintaining localized debug logs
* **HPC Network Resilience:** Pushes multi-path routing parameters (`maximum-paths 2`) for 50:50 ECMP line-rate load-balancing, alongside millisecond link-state recovery via **BGP over BFD** coupling.
* **Closed-Loop Audit:** Executes post-deployment monitoring scripts to capture IPv4/EVPN BGP tables and automatically isolate down peers.
```text
[ 1. Deploy Config ] ───▶ [ 2. Run Telemetry Check ]
          ▲                                │
          │                                ▼
[ 4. Fix or Alert ]  ◀─── [ 3. Parse & Verify State ]
```
---
## Multi-Stage Pipeline
The automation is sequentially modularized into 5 discrete operational phases:

### [Stage 1] Bootstrapping & Idempotency Baseline
* `stage1_init.py`
`inventory.yaml`
* Retrieves the current operational state of target nodes,
* Dynamically updates uniform login banners and hardens device management layers by standardizing SSHv2 timers and authentication retry thresholds.

### [Stage 2] eBGP core routing establishment
* `stage2_underlay.py`
`templates/cisco_ios_fabric.j2`
`inventory.yaml`
* Configures loopback interfaces and eBGP peering architectures at once by a Jinja2 template using a structured, industry-standard eBGP design for data center architecture.

### [Stage 3] BFD Acceleration and 50:50 ECMP verification
* `stage3_hpc_optimize.py`
`templates/cisco_ios_fabric2.j2`
`inventory.yaml`
* Pushes ultra-fast sub-second link failure detection to physical links.
* Immediately executes a validation engine using regular expressions (`re`) to parse Leaf routing tables and ensure equal-cost paths are actively load-balancing packets across all Spines.

### [Stage 4] Multi-Tenant VXLAN EVPN Overlay Deployment
* `stage4_overlay.py`
`vxlan_evpn_template.j2`
`inventory2.yaml`
* Uses standard CLI input to dynamically distribute software-defined infrastructure parameters across the Leaf layer
* Binds Layer 2 broadcast domains (VLAN 10, VLAN 20) to VXLAN (VNI 10100, VNI 10200)

### [Stage 5] Control-plane Integrity Checks
* `scripts/stage5_health_check.py`
`inventory2.yaml`
* Extracts live telemetry tables from `IPv4` and `L2VPN EVPN` BGP routing engines from all devices concurrently.
* Parses line-by-line device metrics into Python arrays to detect, isolate, and log non-established peering states.

## Tools & Environment
- **Python 3.10+** (Netmiko, YAML, Jinja2, Multithreading)
- **GNS3 / GNS3 VM**
- **Cisco IOS routers & switches (simulated)**

## Topology Diagram
```text
              [ Spine-1 ]                            [ Spine-2 ]
              [AS 65100]                             [AS 65100]
             Lo0: 1.1.1.1                            Lo0: 1.1.1.2
       Gi0/1           Gi0/2                  Gi0/1            Gi0/2
    10.1.11.1         10.1.12.1              10.1.21.1       10.1.22.1

               [ Leaf-1 ]                             [ Leaf-2 ]
               [AS 65200]                             [AS 65200]
              Lo0: 2.2.2.1                           Lo0: 2.2.2.2
        Gi0/1           Gi0/2                  Gi0/1            Gi0/2
     10.1.11.2         10.1.21.2              10.1.12.2       10.1.22.2
```
<img width="525" height="624" alt="image" src="https://github.com/user-attachments/assets/b4b4e7a3-408b-4ea7-b36f-0f39a445d4d3" />

### Out-Of-Band Management Network
```text
                          [ NAT / Internet ]
                                   │	
        [ Linux node ] ──── [ Ethernet Switch ]
(eth0) ── IP: 192.168.122.214      ├─── [Spine-1] (Gi0/0) ── IP: 192.168.122.11/24
                                   ├─── [Spine-2] (Gi0/0) ── IP: 192.168.122.12/24
                                   ├─── [Leaf-1]  (Gi0/0) ── IP: 192.168.122.21/24
                                   └─── [Leaf-2]  (Gi0/0) ── IP: 192.168.122.22/24
```
## How to Run
1. Clone this repository:
2. Install dependencies:
   ```bash
   pip3 install netmiko
   pip3 install yaml
   pip3 install jinja2
   ```
3. Update `inventory.yaml` `inventory2.yaml` with your device access credentials and interface allocation arrays.
4. Run scripts sequentially:
---
## Example Outputs
```text
└── bgp_status_backups/
    ├── Spine-1_BGP_Status_20261021_025500.txt
    ├── Leaf-1_BGP_Status_20261021_025500.txt
    └── ...
```
```text
# Sample stage5 output:
[+] Status snapshot successfully saved to: ./bgp_status_backups/Leaf-1_BGP_Status_20261021_025500.txt
[Leaf-1] System integrity Check: Passed. All BGP state machines are fully ESTABLISHED.
```
```text
# Sample '.txt' output (When Leaf-2 is down):
```
<img width="929" height="482" alt="image" src="https://github.com/user-attachments/assets/eee05347-a60a-4744-bb11-4b13fbec65b4" />

<img width="804" height="497" alt="image" src="https://github.com/user-attachments/assets/7d04c4b2-9742-45d7-b769-db8f803138dd" />

