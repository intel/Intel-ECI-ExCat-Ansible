#!/usr/bin/python

# Copyright (C) 2023 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

RDT_PATH = "/sys/fs/resctrl/"

DOCUMENTATION = r'''
---
module: rdt_schemata

short_description: Write bitmask to rdt schemata file
description:
  - requires RDT CAT support and a mounted resctrl pseudo-filesystem at /sys/fs/resctrl
  - requires root privileges
  - writes the provided bitmask to all cache_ids for a given cache-level
  - checks the rdt command status afterwards
  - see <https://docs.kernel.org/x86/resctrl.html> for more details about resctrl

options:
    cache_level:
        description: cache level to which the bitmask shall be applied
        required: true
        type: int
    bitmask_hex:
        description:
            - bitmask that describes the cache ways to be assigned to the cache buffer
            - only consecutive bits are allowed
            - has to be in hex
        required: true
        type: string
    cos_name:
        description:
            - name of the Class of Service (COS), which in fact is the cache buffer
            - can be either "default" for cos0 (the default class at the root folder "/sys/fs/resctrl")
            - or another COS with an existing directory "/sys/fs/resctrl/<cos_name>"
        required: true
        type: string

author:
    - Wolfgang Pross
'''

EXAMPLES = r'''
# Assign 2 cache ways in "/sys/fs/resctrl/myCacheBuffer/schemata" at the 3rd and 4th bit position
- name: Size buffer
  rdt_schemata:
    cache_level: 2
    bitmask_hex: "000c"
    cos_name: "myCacheBuffer"
  become: true
'''

RETURN = r'''
# Return values with samples
schemata:
    description: the schemata file of the desired COS after the applied change
    type: str
    returned: always
    sample: [
        "    L3:0=0003;1=0003",
        "    L2:0=ffff;1=ffff;2=ffff;3=ffff",
        "    MB:0= 100;1= 100"
    ]
schemata_path:
    description: the path to the schemata file
    type: str
    returned: always
    sample: '/sys/fs/resctrl/myCos'
'''

from ansible.module_utils.basic import AnsibleModule
from pathlib import Path
import re, yaml, os

def run_module():
    # module input
    module_args = dict(
        cache_level=dict(type='int', required=True),
        bitmask_hex=dict(type='str', required=True),
        cos_name=dict(type='str', required=True)
    )

    # module output
    result = dict(
        changed=False,
        schemata_path='',
        schemata=[],
        diff = {}
    )

    # instantiate AnsibleModule object
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    # get current schemata
    rdt_path = Path(RDT_PATH)
    if module.params["cos_name"] == "default":
        schemata_path = rdt_path.joinpath("schemata")
    else:
        schemata_path = rdt_path.joinpath(module.params["cos_name"], "schemata")

    if not schemata_path.exists():
        module.fail_json(
                f'cos with cos_name = {module.params["cos_name"]} does not exist',
                **result)

    result['schemata_path'] = str(schemata_path)
    got = schemata_path.open().read().splitlines()
    wanted = []

    # create desired schemata
    for line in got:
        if re.search(rf'L{str(module.params["cache_level"])}', line) is not None:
            wanted.append(re.sub(r"(?<=[0-9]=)[0-9a-f]+", module.params["bitmask_hex"], line))
        else:
            wanted.append(line)

    # check if changes would be introduced
    if got != wanted:
        result['changed'] = True
        result['diff'] = dict(
                before = yaml.safe_dump(got),
                after = yaml.safe_dump(wanted)
        )

    # if no changes, return with result['changed'] = False
    if module.check_mode or not result['changed']:
        result['schemata'] = wanted
        module.exit_json(**result)

    # apply changes: write new schemata
    try:
        schemata_file = schemata_path.open('w')
        for line in wanted:
            print(line, file=schemata_file)
        schemata_file.flush()
        os.fsync(schemata_file)
        schemata_file.close()
    except Exception as e:
        # check rdt for errors
        rdt_cmd_status_path = rdt_path.joinpath("info", "last_cmd_status")
        rdt_cmd_status = rdt_cmd_status_path.open().read()
        if re.search(r'ok', rdt_cmd_status) is None:
            module.fail_json(
                    f"rdt error when writing schemata to {schemata_path}: {e.args}: {rdt_cmd_status}",
                    **result)

    result['schemata'] = wanted

    # return result
    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
