#!/usr/bin/python

# Copyright (C) 2023 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

from __future__ import absolute_import, division, print_function

__metaclass__ = type

RDT_PATH = "/sys/fs/resctrl/"

DOCUMENTATION = r"""
---
module: rdt_new_cos

short_description: Creat new Class of Service (COS)
description:
  - requires RDT CAT support and a mounted resctrl pseudo-filesystem at /sys/fs/resctrl
  - requires root privileges
  - assumes that no all possible Classes of Service (COS) are already in use
  - creates the new COS (a new directory within /sys/fs/resctrl) with default schemata utilizing all cache-ways
  - creates a deterministic name in the format 'yyyymmddhhmmss' and adds 4 random characters
  - checks the rdt command status afterwards
  - see <https://docs.kernel.org/x86/resctrl.html> for more details about resctrl

author:
    - Wolfgang Pross
"""

EXAMPLES = r"""
# Create new COS in "/sys/fs/resctrl"
- name: Create new COS
  rdt_new_cos:
  become: true
"""

RETURN = r"""
# Return values with samples
cos_name:
    description: the name of the Class of Service (COS)
    type: str
    returned: always
    sample: '20230504122939966009'
"""

from ansible.module_utils.basic import AnsibleModule
from pathlib import Path
import datetime, re, uuid


def run_module():
    # module input
    module_args = dict()

    # module output
    result = dict(changed=False, cos_name="")

    # instantiate AnsibleModule object
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=False)

    # get unique name containing current date and time
    result["cos_name"] = (
        datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        + "-"
        + str(uuid.uuid4().hex)[:4]
    )
    rdt_path = Path(RDT_PATH)
    cos_path = rdt_path.joinpath(result["cos_name"])

    # apply changes: create new cos
    try:
        cos_path.mkdir()
    except Exception as e:
        # check rdt for errors
        rdt_cmd_status_path = rdt_path.joinpath("info", "last_cmd_status")
        rdt_cmd_status = rdt_cmd_status_path.open().read()
        if re.search(r"ok", rdt_cmd_status) is None:
            module.fail_json(
                f"rdt error when creating new COS at {cos_path}: {e.args}: {rdt_cmd_status}",
                **result,
            )

    # return result
    result["changed"] = True
    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
