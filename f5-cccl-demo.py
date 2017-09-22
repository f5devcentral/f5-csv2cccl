#!/usr/bin/env python
#
# Copyright 2017 F5 Networks
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function
import json
import logging
import configargparse
import sys
from urlparse import urlparse
from f5.bigip import ManagementRoot
from f5_cccl.api import F5CloudServiceManager
from f5_cccl.exceptions import F5CcclError
logger = logging.getLogger()

def parse_log_level(log_level_arg):
    """Parse the log level from the args.

    Args:
        log_level_arg: String representation of log level
    """
    LOG_LEVELS = ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']
    if log_level_arg not in LOG_LEVELS:
        msg = 'Invalid option: {0} (Valid choices are {1})'.format(
            log_level_arg, LOG_LEVELS)
        raise argparse.ArgumentTypeError(msg)

    log_level = getattr(logging, log_level_arg, logging.INFO)

    return log_level


def setup_logging(logger, log_format, log_level):
    """Configure logging."""
    logger.setLevel(log_level)

    formatter = logging.Formatter(log_format)

    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setFormatter(formatter)
    logger.addHandler(consoleHandler)
    logger.propagate = False


def set_logging_args(parser):
    """Add logging-related args to the parser."""
    parser.add_argument("--log-format",
                        env_var='F5_CC_LOG_FORMAT',
                        help="Set log message format",
                        default="%(asctime)s %(name)s: %(levelname)"
                        " -8s: %(message)s")
    parser.add_argument("--log-level",
                        env_var='F5_CC_LOG_LEVEL',
                        type=parse_log_level,
                        help="Set logging level. Valid log levels are: "
                        "DEBUG, INFO, WARNING, ERROR, and CRITICAL",
                        default='INFO')
    return parser


def get_arg_parser():
    """Create the parser for the command-line args."""
    parser = configargparse.getArgumentParser()
    parser.add_argument("--longhelp",
                        help="Print out configuration details",
                        action="store_true")
    parser.add_argument("--hostname",
                        help="F5 BIG-IP hostname")
    parser.add_argument("--username",
                        help="F5 BIG-IP username")
    parser.add_argument("--password",
                        help="F5 BIG-IP password")
    parser.add_argument("--partition",
                        help="[required] Only generate config for apps which"
                        " match the specified partition."
                        " Can use this arg multiple times to"
                        " specify multiple partitions",
                        action="append",
                        default=list())
    parser.add_argument("--filename",
                        help="Input file with BIG-IP config")

    parser = set_logging_args(parser)
    return parser


def parse_args():
    """Entry point for parsing command-line args."""
    # Process arguments
    arg_parser = get_arg_parser()
    args = arg_parser.parse_args()

    # Print the long help text if flag is set
    if args.longhelp:
        print(__doc__)
        sys.exit()
    # otherwise make sure that a Marathon URL was specified
    else:
        if len(args.partition) == 0:
            arg_parser.error('argument --partition is required: please ' +
                             'specify at least one partition name')
        if not args.hostname:
            arg_parser.error('argument --hostname is required: please ' +
                             'specify')
        if not args.username:
            arg_parser.error('argument --username is required: please ' +
                             'specify')
        if not args.password:
            arg_parser.error('argument --password is required: please ' +
                             'specify')
        if not args.filename:
            arg_parser.error('argument --filename is required: please ' +
                             'specify')

        if not urlparse(args.hostname).scheme:
            args.hostname = "https://" + args.hostname
        url = urlparse(args.hostname)

        if url.scheme and url.scheme != 'https':
            arg_parser.error(
                'argument --hostname requires \'https\' protocol')
        if url.path and url.path != '/':
            arg_parser.error(
                'argument --hostname: path must be empty or \'/\'')

        args.host = url.hostname
        args.port = url.port
        if not args.port:
            args.port = 443

    return args


if __name__ == '__main__':
    # parse args
    args = parse_args()

    # Setup logging
    setup_logging(logging.getLogger(), args.log_format, args.log_level)

    # BIG-IP to manage
    bigip = ManagementRoot(
        args.host,
        args.username,
        args.password,
        port=args.port,
        token="tmos")

    # Management for the BIG-IP partitions
    cccls = []
    for partition in args.partition:
        cccl = F5CloudServiceManager(
            bigip,
            partition,
            prefix="")
        cccls.append(cccl)

    with open(args.filename) as json_data:
        config = json.load(json_data)

    cfg = config['resources']
    incomplete = 0

    for cccl in cccls:
        try:
            incomplete += cccl.apply_config(cfg[cccl.get_partition()])
        except F5CcclError as e:
            logger.error("CCCL Error: %s", e.msg)
    c = bigip.tm.sys.config
    c.exec_cmd('save')
