import yaml
import threading
from jinja2 import Template
from netmiko import ConnectHandler
import logging
import re

logging.basicConfig(filename='stage3.log',level=logging.DEBUG, filemode='w')

def load_inventory():
    with open("inventory.yaml","r") as f:
        return yaml.safe_load(f)

def load_template():
    with open("templates/cisco_ios_fabric_2.j2","r") as f:
        return f.read()

def deploy_hpc_optimization(hostname, device_info, global_vars, template_source):
    print(f"[{hostname}] Optimizing for HPC (ECMP + BFD)...")

    j2_template = Template(template_source)
    rendered_config = j2_template.render(
        loopback = device_info["loopback"],
        interfaces = device_info["interfaces"],
        asn = device_info["asn"],
        bgp_peers = device_info["bgp_peers"],
    )

    config_commands = [
    line.strip() for line in rendered_config.split("\n")
    if line.strip() and not line.strip().startswith("!")
    ]

#    print(config_commands)

    cisco_device = {
        "device_type" : "cisco_ios",
        "host" : device_info["mgmt_ip"],
        "username" : global_vars["ansible_user"],
        "password" : global_vars["ansible_password"],
        "port" : global_vars["ansible_port"],
        "secret" : global_vars["ansible_password"],
    }

    try:
        net_connect = ConnectHandler(**cisco_device)
        net_connect.enable()
        net_connect.send_config_set(config_commands)
        net_connect.send_command("write memory", read_timeout=200)
        net_connect.disconnect()
        print(f"[{hostname}] HPC Optimizations pushed successfully.")

    except Exception as e:
        print(f"ERROR: [{hostname}] Optimization failed: {e}")

def verify_hpc_fabric(leaf_info, global_vars):
    print("\n==================================================")
    print("Automated Fabric Post-check : Verifying ECMP...")
    print("==================================================")

    cisco_device = {
        "device_type" : "cisco_ios",
        "host" : leaf_info["mgmt_ip"],
        "username" : global_vars["ansible_user"],
        "password" : global_vars["ansible_password"],
        "port" : global_vars["ansible_port"],
        "secret" : global_vars["ansible_password"],
    }

    try:
        net_connect = ConnectHandler(**cisco_device)
        net_connect.enable()

        # Parse routing table for Leaf-2's Loopback 2.2.2.2 from Leaf-1's perspective
        route_output = net_connect.send_command("show ip route 2.2.2.2")
        print(f"[Leaf-1 Raw Route Output]: \n{route_output}\n")

        # Validation Logic: Check if there are TWO active paths (ECMP)
        ecmp_paths = re.findall(r"from\s(10\.1\.\d+\.\d+),", route_output)
        path_count = len(ecmp_paths)

        if path_count == 2:
            print("Success: 50:50 ECMP Load-Balancing Detected \nacross both Spine-1 and Spine-2")
        else:
            print(f"Failure: Expected 2 balanced paths, but found {path_count}. Check configuration.")

        # Verify BFD state
        bfd_output = net_connect.send_command("show bfd neighbors")
        print(f"[Leaf-1 BFD Session Status]: \n{bfd_output}")

        net_connect.disconnect()
    except Exception as e:
        print(f"Verification Failed: {e}")
        
def main():
    inventory = load_inventory()
    template_source = load_template()
    global_vars = inventory["all"]["vars"]

    threads = []

    # 1. Parallel Configuarion Push
    for group in ["spines","leafs"]:
        if group in inventory["all"]:
            for hostname, device_info in inventory["all"][group].items():
                t = threading.Thread(
                    target = deploy_hpc_optimization,
                    args = (hostname, device_info, global_vars, template_source)
                )
                threads.append(t)
                t.start()

    for t in threads:
        t.join()

    # 2. Validation Run (Checking Leaf-1)
    leaf1_info = inventory["all"]["leafs"]["Leaf-1"]
    verify_hpc_fabric(leaf1_info, global_vars)

if __name__ == "__main__":
    main()


