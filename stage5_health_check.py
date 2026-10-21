import yaml
import threading
import datetime
import os
from netmiko import ConnectHandler


def load_inventory():
    path = input("Enter the device file name: ")
    with open(path, "r") as f:
        return yaml.safe_load(f)


def parse_bgp_summary(bgp_output):
    failed_peers = []
    lines = bgp_output.strip().split("\n")
    parsing_started = False # starting point flag

    for line in lines:
        if "Neighbor" in line and "State/PfxRcd" in line:
            parsing_started = True
            continue # skip remaining codes at this loop

        # Parsing rule: last field is integer -> Established
        if parsing_started and line.strip():
            tokens = line.split()
            if len(tokens) >= 10: # the number of words in that line
                neighbor_ip = tokens[0]
                state_or_pfx = tokens[-1]
                if not state_or_pfx.isdigit():
                #if not re.match(r"^\d+$',state_or_pfx):
                    failed_peers.append({"neighbor": neighbor_ip, "state":state_or_pfx})
    return failed_peers

def check_infrastructure(hostname, device_info, global_vars):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = "./bgp_status_backups"
    os.makedirs(log_dir, exist_ok=True)

    alert_messages = [] # For future use. e.g.sending alerts through Slack

    print(f"[{hostname}] Capturing real-time control plane telemetry states...")

    cisco_device = {
        "device_type": "cisco_ios",
        "host": device_info["mgmt_ip"],
        "username": global_vars["ansible_user"],
        "password": global_vars["ansible_password"],
        "secret": global_vars["ansible_password"],
        "port": global_vars["ansible_port"]
    }

    try:
        net_connect = ConnectHandler(**cisco_device)
        net_connect.enable()
        underlay_output = net_connect.send_command("show ip bgp summary")
        overlay_output = net_connect.send_command("show bgp l2vpn evpn summary")

        backup_file_path = f"{log_dir}/{hostname}_BGP_Status_{timestamp}.txt"
        with open(backup_file_path, "w") as f:
            f.write(f"=== {hostname} Underlay BGP Status ===\n")
            f.write(underlay_output)
            f.write("\n\n=== Overlay EVPN BGP Status ===\n")
            f.write(overlay_output)
        print(f"[+] Status snapshot successfully saved to: {backup_file_path}")

        # Parsing and Verifing
        failed_underlay = parse_bgp_summary(underlay_output)
        failed_overlay = parse_bgp_summary(overlay_output)

        if failed_underlay:
            for peer in failed_underlay:
                print(f"[{hostname}] Underlay Peer {peer['neighbor']} is down! Current State: {peer['state']}")
                #alert_messages.append(f"[{hostname}] Underlay Peer {peer['neighbor']} is down! Current State: {peer['state']}")

        if failed_overlay:
            for peer in failed_overlay:
                print(f"[{hostname}] Overlay EVPN Peer {peer['neighbor']} is down! Current State: {peer['state']}")
                #alert_messages.append(f"[{hostname}] Overlay EVPN Peer {peer['neighbor']} is down! Current State: {peer['state']}")

        if not failed_underlay and not failed_overlay:
            print(f"[{hostname}] System integrity Check: Passed. All BGP state machines are fully ESTABLISHED.")
        net_connect.disconnect()

    except Exception as e:
        error_msg = f"[Critical] Failed to connect to {hostname} {device_info["mgmt_ip"]}. Error: {str(e)}"
        print(error_msg)
        #alert_messages.append(error_msg)

def main():
    inventory = load_inventory()
    global_vars = inventory["all"]["vars"]

    threads = []

    for group in ["spines","leafs"]:
        if group in inventory["all"]:
            for hostname, device_info in inventory["all"][group].items():
                t = threading.Thread(
                args = (hostname, device_info, global_vars),
                target = check_infrastructure
                )
                threads.append(t)
                t.start()

    for t in threads:
        t.join()

if __name__ == "__main__":
    main()
