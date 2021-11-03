#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

"""
Setup file for multinode server and client configuration for executing
the sanity in K8s environment.
"""
import os
import configparser
import json
import logging
import argparse
from commons.helpers.pods_helper import LogicalNode
from commons.utils import system_utils as sysutils
from commons import commands as com_cmds

CONF_FILE = 'scripts/cicd_k8s/config.ini'
config = configparser.ConfigParser()
config.read(CONF_FILE)
LOGGER = logging.getLogger(__name__)

# pylint: disable=too-many-arguments
# pylint: disable-msg=too-many-locals
def create_db_entry(m_node, username: str, password: str, mgmt_vip: str,
                    admin_user: str, admin_passwd: str, ext_ip) -> str:
    """
    Creation of new host entry in database.
    :param str m_node: hostname of master node
    :param str username: username of nodes
    :param str password: password of nodes
    :param str mgmt_vip: csm mgmt vip
    :param str admin_user: admin user for cortxcli
    :param str admin_passwd: admin password for cortxcli
    :param str ext_ip: external LB IP
    :return: Target name
    """
    host_list = []
    host_list.append(m_node)
    json_file = config['default']['setup_entry_json']
    new_setupname = os.getenv("Target_Node")
    node_obj = LogicalNode(hostname=m_node, username=username, password=password)
    output_node = node_obj.execute_cmd(com_cmds.CMD_GET_NODE, read_lines=True)
    for line in output_node:
        if "worker" in line:
            out = line.split()[0]
            host_list.append(out)
    LOGGER.info("Creating DB entry for setup: %s", new_setupname)
    with open(json_file, 'r') as file:
        json_data = json.load(file)

    json_data["setupname"] = new_setupname
    json_data["product_family"] = "LC"
    json_data["product_type"] = "k8s"
    json_data["lb"] = ext_ip
    nodes = list()
    node_info = {
        "host": "srv-node-1",
        "hostname": "node 1 hostname",
        "username": "node 1 username",
        "password": "node 1 password",
    }
    for count, host in enumerate(host_list, start=1):
        node = dict()
        node_info["host"] = f"srvnode-{count}"
        node_info["hostname"] = host
        node_info["username"] = username
        node_info["password"] = password
        if count == 1:
            node_info["node_type"] = "master"
        else:
            node_info["node_type"] = "worker"
        node.update(node_info)
        nodes.append(node)

    json_data["nodes"] = nodes
    json_data["csm"]["mgmt_vip"] = mgmt_vip
    json_data["csm"]["csm_admin_user"].update(
        username=admin_user, password=admin_passwd)

    LOGGER.info("new file data: %s", json_data)
    with open(json_file, 'w') as file:
        json.dump(json_data, file)

    return new_setupname

def configure_haproxy_lb(m_node: str, username: str, password: str):
    """
    Implement external Haproxy LB
    :param m_node: hostname for master node
    :param username: username for node
    :param password: password for node
    :return: external LB IP
    """
    resp = sysutils.execute_cmd(cmd=com_cmds.CMD_GET_IP_IFACE.format("eth1"))
    ext_ip = resp[1].strip("'\\n'b'")
    LOGGER.info("External LB IP: %s", ext_ip)
    m_node_obj = LogicalNode(hostname=m_node, username=username, password=password)
    resp = m_node_obj.execute_cmd(cmd=com_cmds.CMD_SRVC_STATUS, read_lines=True)
    LOGGER.info("Response for services status: %s", resp)
    # TODO: HAProxy changes to file
    LOGGER.info("Setting s3 endpoints of ext LB on client.")
    sysutils.execute_cmd(cmd="rm -f /etc/hosts")
    with open("/etc/hosts", 'w') as file:
        file.write("127.0.0.1   localhost localhost.localdomain localhost4 "
                   "localhost4.localdomain4\n")
        file.write("::1         localhost localhost.localdomain localhost6 "
                   "localhost6.localdomain6\n")
        file.write("{} s3.seagate.com sts.seagate.com iam.seagate.com "
                   "sts.cloud.seagate.com\n".format(ext_ip))
    return ext_ip


def main():
    """
    Main Function.
    """
    parser = argparse.ArgumentParser(
        description="Multinode server and client configuration for executing the R2 regression")
    parser.add_argument("--master_node", help="Hostname for master node", required=True)
    parser.add_argument("--node_count", help="Number of worker nodes in cluster",
                        required=True, type=int)
    parser.add_argument("--password", help="password for nodes", required=True)
    parser.add_argument("--mgmt_vip", help="csm mgmt vip", required=True)
    parser.add_argument("--ext_ip_list", help="External IPs list for LB", required=True)
    args = parser.parse_args()
    master_node = args.master_node
    node_count = args.node_count
    LOGGER.info("Total number of nodes in cluster: %s", node_count)
    username = "root"
    admin_user = os.getenv("ADMIN_USR")
    admin_passwd = os.getenv("ADMIN_PWD")

    ext_ip = configure_haproxy_lb(master_node, username=username, password=args.password)
    setupname = create_db_entry(master_node, username=username, password=args.password,
                                mgmt_vip=args.mgmt_vip, admin_user=admin_user,
                                admin_passwd=admin_passwd, ext_ip=ext_ip)
    LOGGER.info("target_name: %s", setupname)
    sysutils.execute_cmd(cmd="cp /root/secrets.json .")
    with open("/root/secrets.json", 'r') as file:
        json_data = json.load(file)
    output = sysutils.execute_cmd("python3.7 tools/setup_update/setup_entry.py --fpath {} "
        "--dbuser {} --dbpassword {}".format(config['default']['setup_entry_json'],
                    json_data['DB_USER'], json_data['DB_PASSWORD']))
    if "Entry already exits" in str(output):
        LOGGER.info("DB already exists for target: %s, so will update it.", setupname)
        sysutils.execute_cmd("python3.7 tools/setup_update/setup_entry.py --fpath {} "
            "--dbuser {} --dbpassword {} --new_entry False"
                             .format(config['default']['setup_entry_json'],
                                     json_data['DB_USER'], json_data['DB_PASSWORD']))

    LOGGER.info("Mutlinode Server-Client Setup Done.")


if __name__ == "__main__":
    main()