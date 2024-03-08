#!/usr/bin/python

# Copyright (C) 2023 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""
rdt_exec_in_cos ansible module See documentation below for usage details
"""
from __future__ import absolute_import, division, print_function

import datetime
import os
import re
import subprocess
import uuid
from pathlib import Path

import yaml
from ansible.module_utils.basic import AnsibleModule

__metaclass__ = type # pylint: disable=invalid-name

RDT_PATH = "/sys/fs/resctrl/"
LOG_PATH = "/tmp/"

DOCUMENTATION = r"""
---
module: rdt_exec_in_cos

short_description: Start executable and assign it's PID to the given COS
description:
  - requires a pre-configured Class of Service (COS) in /sys/fs/resctrl
  - requires root privileges
  - writes the output and errors from the executable to a log_file
  - if the COS is already used, a warning is printed with the PIDs in the tasks file
  - see <https://docs.kernel.org/x86/resctrl.html> for more details about resctrl

options:
    executable:
        description: path to executable
        required: true
        type: string
    args:
        description: list of arguments to be passed to the executable at startup
        required: false
        type: list of strings
    cos_name:
        description:
            - name of the Class of Service (COS), which in fact is the cache buffer
            - must be an existing directory in "/sys/fs/resctrl"
        required: true
        type: string
    log_file:
        description:
            - path to the log file that the output and error messages of the executable is written to
            - the directory has to exist
            - if not specified, a file with a unique name based on the date and time is created in "/tmp"
        required: false
        type: string


author:
    - Wolfgang Pross
"""

EXAMPLES = r"""
# Start myWorkload and assign the pre-defined cache-buffer in /sys/fs/resctrl/myCacheBuffer to it
- name: Start workload with exclusive CAT buffer
  rdt_exec_in_cos:
    executable: "/path/to/myWorkload"
    cos_name: "myCacheBuffer"
    log_file: "/path/to/stdout.log"
  become: true
"""

RETURN = r"""
# Return values with samples
pid:
    description: the PID of the started executable
    type: str
    returned: always
    sample: 1016885,
tasks:
    description: tasks file of the COS after assigning the new PID
    type: list of strings
    returned: always
    sample: [
        "942892",
        "1012075"
    ]
log_file:
    description: path to the log_file that the output and errors of the executable are written to
    type: str
    returned: always
    sample: "/tmp/20230505193659-77cc.log"
"""


def run_module():
    """This function will first check if the COS exists, start the executable and write
    the executable PID to the tasks file of COS
    """
    # module input
    module_args = {
        "executable": {"type": "str", "required": True},
        "args": {"type": "list", "required": False},
        "cos_name": {"type": "str", "required": True},
        "log_file": {"type": "str", "required": False},
    }

    # module output
    result = {"changed": False, "pid": "", "tasks": [], "log_file": "", "diff": {}}

    # instantiate AnsibleModule object
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    # check if given executable exists and make sure it's executable
    exec_path = Path(module.params["executable"])
    if not exec_path.exists():
        module.fail_json(
            f'executable {module.params["executable"]} does not exist', **result
        )
    elif not exec_path.is_file():
        module.fail_json(
            f'executable {module.params["executable"]} is not a file', **result
        )
    elif not os.access(exec_path, os.X_OK):
        exec_path.chmod(exec_path.stat().st_mode | 0o000100)

    # make sure the COS exists
    rdt_path = Path(RDT_PATH)
    cos_path = rdt_path.joinpath(module.params["cos_name"])
    if not cos_path.exists():
        module.fail_json(
            f'/sys/fs/resctrl/{module.params["cos_name"]} does not exist', **result
        )

    # get current tasks file
    tasks_path = cos_path.joinpath("tasks")
    with tasks_path.open(encoding="utf-8") as got:
        got.read().splitlines()
        if got:
            module.warn(
                f"COS {module.params['cos_name']} is already in use by PID(s) {got}"
            )

        # set output log file
        if module.params["log_file"]:
            result["log_file"] = module.params["log_file"]
        else:
            result["log_file"] = (
                LOG_PATH
                + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                + "-"
                + str(uuid.uuid4().hex)[:4]
                + ".log"
            )
        try:
            with Path(result["log_file"]).open("w", encoding="utf-8") as log_file:
                # check args
                if module.params["args"]:
                    [str(exec_path)].extend(module.params["args"])

                command = [str(exec_path)]

                # start executable
                with subprocess.Popen(
                    command,
                    stdin=subprocess.DEVNULL,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                ) as subprocess_h:
                    result["pid"] = subprocess_h.pid
                wanted = got.append(result["pid"])
                result["changed"] = True
                result["diff"] = {
                    "before": yaml.safe_dump(got),
                    "after": yaml.safe_dump(wanted),
                }
        except Exception as e:
            module.fail_json(
                f"log_file {result['log_file']} can not be opened for writing: {e.args}",
                **result,
            )

    # apply changes: write new PID to tasks file of COS
    try:
        with tasks_path.open("w", encoding="utf-8") as tasks_file:
            print(result["pid"], file=tasks_file)
            tasks_file.flush()
            os.fsync(tasks_file)
    except IOError as e:
        # check rdt for errors
        rdt_cmd_status_path = rdt_path.joinpath("info", "last_cmd_status")
        with rdt_cmd_status_path.open(encoding="utf-8") as rdt_cmd_status:
            rdt_cmd_status.read()
            if re.search(r"ok", rdt_cmd_status) is None:
                module.fail_json(
                    f"rdt err: writing PID {result['pid']} \
                    to {tasks_path}: {e.args}: {rdt_cmd_status}",
                    **result,
                )

    with tasks_path.open(encoding="utf-8") as tasks_file:
        result["tasks"] = tasks_file.read().splitlines()

    # return result
    module.exit_json(**result)


def main():
    """main"""
    run_module()


if __name__ == "__main__":
    main()
