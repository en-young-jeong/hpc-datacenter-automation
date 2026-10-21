import yaml
import threading
from jinja2 import Template
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException
import logging

logging.basicConfig(filename='stage2.log',level=logging.DEBUG, filemode='w')
logging.getLogger('netmiko')

def load_inventory(config_path="inventory.yaml"):
    with open(config_path,"r") as f:
        return yaml.safe_load(f)

def load_template(template_path="templates/cisco_ios_fabric.j2"):
    with open(template_path,"r") as f:
        return f.read()

def deploy_underlay(hostname, device_info, global_vars, template_source):
    print(f"[{hostname}] underlaying fabric generationg... ")

    j2_template = Template(template_source)
    rendered_config = j2_template.render(
        loopback = device_info["loopback"],
        interfaces = device_info["interfaces"],
        asn = device_info["asn"],
        bgp_peers = device_info["bgp_peers"]
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
    "secret": global_vars["ansible_password"],
    }

    try:
        net_connect = ConnectHandler(**cisco_device)
        net_connect.enable()

        print(f"[{hostname}] Transferring interface IP, BGP neighboring commands... \n Total {len(config_commands)} line")
        net_connect.send_config_set(config_commands)

#        net_connect.send_command("write memory")
        net_connect.save_config()
        net_connect.disconnect()
        print(f"[{hostname}] underlaying eBGP fabric deployment completed.\n")

    except (NetmikoTimeoutException, NetmikoAuthenticationException) as e:
        print(f"ERROR: [{hostname}] connection failed : {e}")


def main():
    inventory = load_inventory()
    template_source = load_template()
    global_vars = inventory["all"]["vars"]

    threads = []

    for group in ["spines", "leafs"]:
        if group in inventory["all"]:
            for hostname, device_info in inventory["all"][group].items():
                t = threading.Thread(
                    target = deploy_underlay,
                    args = (hostname, device_info, global_vars, template_source)
                )
                threads.append(t)
                t.start()

    for t in threads:
        t.join()
    print("Spine-Leaf underlaying infra has been successfully deployed!")

if __name__ == "__main__":
    main()
