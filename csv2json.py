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
import json
import csv
import sys
partition = sys.argv[2]
output = {'resources': { partition: {} }}
vs_addrs = set()
for row in csv.reader(open(sys.argv[1])):
    (svc,name,ip_port,pool_members) = row
    vs_name = "%s_vs" %(name)
    pool_name = "%s_pool" %(name)
    (ip,port) = ip_port.split(":")
    pool_members = [a.split(':') for a in pool_members.split(',')]
    if svc in ['tcp','fastl4','http','https']:
        json_template = json.load(open('%s.json' %(svc)))
        if 'virtualServer' in json_template:
            vs_list = output['resources'][partition].get("virtualServers",[])
            json_template['virtualServer']['name'] = vs_name
            json_template['virtualServer']['destination'] = ip_port
            json_template['virtualServer']['pool'] = pool_name
            vs_list.append(json_template['virtualServer'])
            output['resources'][partition]['virtualServers'] = vs_list
        if 'pool' in json_template:
            pool_list = output['resources'][partition].get("pools",[])
            json_template['pool']['name'] = pool_name

            json_template['pool']['members'] = [{'address':a[0],'port':int(a[1])} for a in pool_members]

            pool_list.append(json_template['pool'])
            output['resources'][partition]['pools'] = pool_list
        vs_addrs.add(ip)
    elif svc.startswith('iapp'):
        json_template = json.load(open('%s.json' %(svc)))
        iapp_name = "%s_iapp" %(name)
        if 'iapp' in json_template:
            iapp_list = output['resources'][partition].get("iapps",[])
            json_template['iapp']['name'] = iapp_name
            json_template['iapp']['destination'] = ip_port
            json_template['iapp']["poolMemberTable"]["members"] = [{'address':a[0],'port':int(a[1])} for a in pool_members]
            json_template['iapp']['variables']["pool__addr"] = ip
            json_template['iapp']['variables']["pool__port"] = port
            json_template['iapp']['variables']["vs__Name"] = vs_name
            iapp_list.append(json_template['iapp'])
            output['resources'][partition]['iapps'] = iapp_list

output['resources'][partition]['virtualAddresses'] = [ { "name": a,"autoDelete": "false","enabled": "yes","address":a} for a in vs_addrs]


json.dump(output, open(sys.argv[3], 'w'), indent=4, sort_keys=True)
