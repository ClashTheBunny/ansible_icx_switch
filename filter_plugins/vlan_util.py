import re

def lag_ports_status(on_device_config, configuration_lags):
    """Converts the interface and lag dicts to a vlan membership dict"""
    lags_status = {}
    lags_current = {}

    split_ethernets = re.compile("ethernet (?:([\d/]+)(?: to ([\d/]+))?)")

    insideLag = False
    lag_name = ""
    for line in on_device_config.split("\n"):
        if line.startswith("!"):
            insideLag = False
            continue
        if line.startswith("lag "):
            insideLag = True
            lag_name = line.split(" ")[1]
            lags_current[lag_name] = []
            continue
        if insideLag:
            if "ports " in line:
                ports = split_ethernets.findall(line)
                for port_range in ports:
                    port_list = expand_port_range(*port_range)
                    lags_current[lag_name].extend(port_list)

    for lag in configuration_lags:
        if lag["name"] in lags_current:
            lags_current_set = set(lags_current[lag["name"]])
        else:
            lags_current_set = set()

        lags_configured_set = set(lag["ports"])
        ports_to_add = list(lags_configured_set - lags_current_set)
        ports_to_remove = list(lags_current_set - lags_configured_set)
        ports_actual = list(lags_current_set & lags_configured_set)
        lags_status[lag["name"]] = {
            "ports_to_add": ports_to_add,
            "ports_to_remove": ports_to_remove,
            "ports_actual": ports_actual,
        }
    return lags_status

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

    addAllMembers(interfaces, "ethernet ", "port")
    addAllLagMembers(lags, "ethernet ", "ports")
    return vlans


class FilterModule(object):
    def filters(self):
        return {
            "vlan_membership": vlan_membership,
            "lag_ports_status": lag_ports_status,
        }
