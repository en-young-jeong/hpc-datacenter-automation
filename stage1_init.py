from time import time
import yaml
import threading
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException
import logging

logging.basicConfig(filename='stage1.log',level=logging.DEBUG, filemode='w')
logging.getLogger('netmiko')

def load_inventory(config_path="inventory.yaml"):
    with open(config_path, "r") as f:
            return yaml.safe_load(f)
                #parse YAML strings into standard Python data types. Highly recommended for safety.
                #opposite functions is 'yaml.dump'

def load_banner(banner_path="banner_motd.txt"):
    with open(banner_path, "r") as f:
            return f.read().strip()
                # strip() removes leading and trailing whitespace

def configure_device(hostname, device_info, global_vars, banner_content):
    print(f"[{hostname}] Automation job started...")

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

        #Idempotency check 1. banner
        current_banner = net_connect.send_command("show banner motd", read_timeout=120)

        if "WARNING: AUTHORIZED USE ONLY" not in current_banner:
            print(f"[{hostname}] Old banner detected -> Updating banner...")
#            banner_command = f"banner motd {banner_content}"
#            net_connect.send_config_set([banner_command], read_timeout=30) #send multiple commands, Use list type.
            net_connect.send_config_from_file("banner_motd.txt")
            print(f"[{hostname}] banner update done.")
        else:
            print(f"[{hostname}] banner already updated. (Skip)")

            #Idempotency check 2. ssh
        ssh_config = net_connect.send_command("show run | include ip ssh", read_timeout=120)
        config_commands = []

        if "version 2" not in ssh_config:
            config_commands.append("ip ssh version 2")
        if "time-out 60" not in ssh_config:
            config_commands.append("ip ssh time-out 60")
        if "authentication-retries" not in ssh_config:
            config_commands.append("ip ssh authentication-retries 4")

        if config_commands:
            print(f"[{hostname}] SSH security vulnerability found -> Optimizing: {config_commands}")
            net_connect.send_config_set(config_commands, read_timeout=120)
            print(f"[{hostname}] SSH security update done.")

        else:
            print(f"[{hostname}] SSH already optimized. (Skip)")

        net_connect.send_command("write memory", read_timeout=200)
        net_connect.disconnect()
        print(f"[{hostname}] Initialization sequence completed safely.\n")

    except (NetmikoTimeoutException, NetmikoAuthenticationException) as e:
        print(f"Error: [{hostname}] connection failed: {e}")

def main():
    starting_time = time()
    inventory = load_inventory()
    banner_content = load_banner()
    global_vars = inventory["all"]["vars"]

    threads = []

    for group in ["spines", "leafs"]:
        if group in inventory["all"]:
            for hostname, device_info in inventory["all"][group].items():
                t = threading.Thread(
                    target=configure_device,
                    args=(hostname, device_info, global_vars, banner_content)
                )
                threads.append(t)
                t.start()

				
    for t in threads:
        t.join()
    print(f"---Script End, processing time :{time()-starting_time}")

if __name__ == "__main__":
    main()

	