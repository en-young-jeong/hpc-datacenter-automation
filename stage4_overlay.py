import yaml
import threading
from jinja2 import Template
from netmiko import ConnectHandler

def load_inventory():
    path = input("Enter the device file name: ")
    with open(path, "r") as f:
        return yaml.safe_load(f)

def load_template():
    template = "templates/"
    template += input("Enter the template file name: ")
    with open(template, "r") as f:
        return f.read()

def deploy_overlay(hostname, device_info, global_vars, template_source):
    print(f"{[hostname]} VXLAN EVPN fabric generationg... ")

    j2_template = Template(template_source)
    rendered_config = j2_template.render(
    asn = device_info["asn"],
    bgp_peers = device_info["bgp_peers"],
    anycast_mac = global_vars["anycast_mac"]
    )

    config_commands = [
    line.strip() for line in rendered_config.split("\n")
    if line.strip() and not line.startswith("!")
    ]
    print(config_commands)

    cisco_device = {
    "device_type": "cisco_ios",
    "host": device_info["mgmt_ip"],
    "username": global_vars["ansible_user"],
    "password": global_vars["ansible_password"],
    "port": global_vars["ansible_port"],
    "secret": global_vars["ansible_password"]
    }

    try:
        net_connect = ConnectHandler(**cisco_device)
        net_connect.enable()
        print(f"[{hostname}] transferring commandss...")
        net_connect.send_config_set(config_commands)
        net_connect.save_config()
        print(f"[{hostname}] overrlaying eBGP fabric deployment completed.\n")
        net_connect.disconnect()

    except Exception as e:
        print(f"ERROR: [{hostname}] connection failed : {e}")

def main():
    inventory = load_inventory()
    template_source = load_template()
    global_vars = inventory["all"]["vars"]

    threads = []

    # Parallel Configuarion Push
    for group in ["spines","leafs"]:
        if group in inventory["all"]:
            for hostname, device_info in inventory["all"][group].items():
                t = threading.Thread(
                    target = deploy_overlay,
                    args = (hostname, device_info, global_vars, template_source)
                )
                threads.append(t)
                t.start()

    for t in threads:
        t.join()
    print("Spine-Leaf overlaying infra has been successfully deployed!")

if __name__ == "__main__":
    main()
