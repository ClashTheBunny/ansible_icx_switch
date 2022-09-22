import re

split_ethernets = re.compile(r"ethe(?:rnet)? (?:([\d/]+)(?: to ([\d/]+))?)")

def running_ports_status(on_device_config, section_name):
    """Converts the interface and lag dicts to a vlan membership dict"""
    section_current = {}


    inside_section = False
    section_identifier = ""
    for line in on_device_config.split("\n"):
        if line.startswith("!"):
            inside_section = False
            continue
        if line.startswith(section_name):
            inside_section = True
            section_identifier = line.split(" ")[1]
            section_current[section_identifier] = {}
            continue
        if inside_section:
            if " ethe" in line:
                prefix = line.strip().split(" ")[0]
                if prefix not in section_current[section_identifier]:
                    section_current[section_identifier][prefix] = []
                ports = split_ethernets.findall(line)
                for port_range in ports:
                    port_list = expand_port_range(*port_range)
                    section_current[section_identifier][prefix].extend(port_list)

    return section_current

def lag_ports_diff(current, config):
    status = {}
    print(current, config)
    for section_identifer in [x["name"] for x in config]:
        if section_identifer not in current:
            current[section_identifer] = {"ports": []}
        for prefix in current[section_identifer].keys():
            if section_identifer in current:
                if prefix in current[section_identifer]:
                    current_set = set(current[section_identifer][prefix])
                else:
                    current_set = set()
            else:
                current_set = set()

            configured_set = set([x["ports"] for x in config if x["name"] == section_identifer][0])
            ports_to_add = list(configured_set - current_set)
            ports_to_remove = list(current_set - configured_set)
            ports_actual = list(current_set & configured_set)
            status[section_identifer] = {
                "ports_to_add": ports_to_add,
                "ports_to_remove": ports_to_remove,
                "ports_actual": ports_actual,
            }

    return status

def vlan_ports_diff(current, config):
    status = {}
    print(current, config)
    for section_identifer in set([str(x) for x in config.keys()] + list(current.keys())):
        status[int(section_identifer)] = {}
        if section_identifer not in current:
            current[section_identifer] = {"tagged": [], "untagged": []}
        if current[section_identifer] == {}:
            current[section_identifer] = {"tagged": [], "untagged": []}
        for prefix in current[section_identifer].keys():
            if section_identifer in current:
                if prefix in current[section_identifer]:
                    current_set = set(current[section_identifer][prefix])
                else:
                    current_set = set()
            else:
                current_set = set()

            if int(section_identifer) in config and prefix in config[int(section_identifer)]:
                configured_set = set(config[int(section_identifer)][prefix])
            else:
                configured_set = set()
            print(current_set,configured_set)
            ports_to_add = list(configured_set - current_set)
            ports_to_remove = list(current_set - configured_set)
            ports_actual = list(current_set & configured_set)
            status[int(section_identifer)][prefix] = {
                "ports_to_add": ports_to_add,
                "ports_to_remove": ports_to_remove,
                "ports_actual": ports_actual,
            }

    return status

def expand_port_range(start_port, end_port):
    if end_port == '':
       return [start_port]
    start_parts = start_port.split("/")
    end_parts = end_port.split("/")
    ports = []
    for unit in range(int(start_parts[0]),int(end_parts[0])+1):
        for mezzanine in range(int(start_parts[1]),int(end_parts[1])+1):
            for port in range(int(start_parts[2]),int(end_parts[2])+1):
                ports.append(f'{unit}/{mezzanine}/{port}')
    return ports

def vlan_membership(interfaces, lags):
    """Converts the interface and lag dicts to a vlan membership dict"""
    vlans = {}

    def ensureVlan(vlan):
        if vlan not in vlans:
            vlans[vlan] = {
                "tagged": [],
                "untagged": [],
            }

    def addAllLagMembers(portList, portPrefix, portName):
        for item in portList:
            if "tagged" in item:
                for vlan in item["tagged"]:
                    ensureVlan(vlan)
                    for port in item[portName]:
                        vlans[vlan]["tagged"].append(portPrefix + str(port))
            if "untagged" in item:
                for vlan in item["untagged"]:
                    ensureVlan(vlan)
                    for port in item[portName]:
                        vlans[vlan]["untagged"].append(portPrefix + str(port))

    def addAllMembers(portList, portPrefix, portName):
        for item in portList:
            if "tagged" in item:
                for vlan in item["tagged"]:
                    ensureVlan(vlan)
                    vlans[vlan]["tagged"].append(portPrefix + str(item[portName]))
            if "untagged" in item:
                for vlan in item["untagged"]:
                    ensureVlan(vlan)
                    vlans[vlan]["untagged"].append(portPrefix + str(item[portName]))

    addAllMembers(interfaces, "", "port")
    addAllLagMembers(lags, "", "ports")
    print(vlans)
    return vlans


class FilterModule(object):
    def filters(self):
        return {
            "vlan_membership": vlan_membership,
            "running_ports_status": running_ports_status,
            "vlan_ports_diff": vlan_ports_diff,
            "lag_ports_diff": lag_ports_diff,
        }
