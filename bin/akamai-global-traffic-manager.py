#!/usr/bin/python

# DISCLAIMER:
"""
This script is for demo purposes only which provides customers with programming information regarding the Developer APIs. This script is supplied "AS IS" without any warranties and support.

We assume no responsibility or liability for the use of the script, convey no license or title under any patent or copyright.

We reserve the right to make changes in the script without notification and make no representation or warranty that such application will be suitable for the specified use without further testing or modification.
"""

# USAGE:
"""
usage: gtm_tool.py [--version]  ...

Global Traffic Manager Tools

optional arguments:
  --version  show program's version number and exit

Commands:

    help     Show available help
    search   Search for an IP Address, FQDN, CNAME handout in all GTM
             properties
    show     Show a GTM property details
    update   Modify and activate a property

Example #1: Find a server name or IP in all GTM properties
$ python3 gtm_tool.py search --value secret.origin.com

Example #2: Get a property details
$ python3 gtm_tool.py show --property www.example.com.akadns.net

Example #3: Update a property by turning ON/OFF a Data Center and activate.
$ python3 gtm_tool.py update --property www.example.com.akadns.net --datacenter Dallas --state ON

Example #4: Clone a property and change its data center, server and property name.
python3 gtm_tool.py clone --property www.example.com.akadns.net --datacenter Santiago --server 11.22.33.44 --new_property weighted --key F-AC-788308

"""

import requests, json, sys, os, time, re
from akamai.edgegrid import EdgeGridAuth,EdgeRc
import urllib
import subprocess
import argparse
import logging

if sys.version_info[0] < 3:
    from urlparse import urljoin
else:
    from urllib.parse import urljoin


class MyArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_help(sys.stderr)
        self.exit(0, '%s: error: %s\n' % (self.prog, message))

# Initialization of section and edgerc.
def init_config(edgerc_file, section):
    global baseurl, session
    # Check if the edgerc_file variable or the AKAMAI_EDGERC env var exist then use a default value if they don't exist.
    if not edgerc_file:
        if not os.getenv("AKAMAI_EDGERC"):
            edgerc_file = os.path.join(os.path.expanduser("~"), '.edgerc')
        else:
            edgerc_file = os.getenv("AKAMAI_EDGERC")

    if not os.access(edgerc_file, os.R_OK):
        print("Unable to read edgerc file \"%s\"" % edgerc_file)
        exit(1)

    if not section:
        if not os.getenv("AKAMAI_EDGERC_SECTION"):
            section = "default"
        else:
            section = os.getenv("AKAMAI_EDGERC_SECTION")

    try:
        edgerc = EdgeRc(edgerc_file)
        baseurl = 'https://%s' % edgerc.get(section, 'host')

        session = requests.Session()
        session.auth = EdgeGridAuth.from_edgerc(edgerc, section)

        return(baseurl, session)

    except configparser.NoSectionError:
        print("Edgerc section \"%s\" not found" % section)
        exit(1)
    except Exception:
        print("Unknown error occurred trying to read edgerc file (%s)" % edgerc_file)
        exit(1)

# Function to get a list of all the GTM domains
def gtm_domains(accountKey_unique):
    domains = []
    api_endpoint = urljoin(baseurl, '/config-gtm/v1/domains/' + accountKey_unique)
    logging.info('API Endpoint: ' + api_endpoint)
    response = session.get(api_endpoint)
    # Convert JSON response to a dictionary for better management
    dict_response = json.loads(response.text)
    # Caputure all the domain names, i.e. ['items'][n]['name']
    for entry in dict_response['items']:
        domains.append(entry['name'])
    return(domains)


# Function to get GTM property details, and capture the server names or IPs.
def gtm_domain_properties(domain_name, accountKey_unique):
    print(domain_name)
    api_endpoint = urljoin(baseurl, '/config-gtm/v1/domains/' + domain_name + accountKey_unique)
    logging.info('API Endpoint: ' + api_endpoint)
    response = session.get(api_endpoint)
    dict_response = json.loads(response.text)

    # Handle case for domains that contain a property type 'asmapping'. Send the "Accept: application/vnd.config-gtm.v1.1+json" request header.
    if response.status_code == 406:
        headers = {'Accept':  str(dict_response['minimumMediaTypeRequired'])}
        api_endpoint = urljoin(baseurl, '/config-gtm/v1/domains/' + domain_name + accountKey_unique)
        logging.info('API Endpoint: ' + api_endpoint)
        response = session.get(api_endpoint, headers=headers)
        dict_response = json.loads(response.text)

    return(dict_response)


# Function to extract the traffic targets from each GTM property
def gtm_traffic_targets(domain_name, domains_with_properties):
    # Looping through all traffic targets. First loop is for capturing and constructing the property name
    n = 0

    for entry in domains_with_properties['properties']:
        property_name = json.dumps(entry['name'])
        # Construct the full property name: property+domain.
        full_property_name = (json.loads(property_name) + '.' + domain_name)
        # Second loop is for grabbing all the servers per property under the domain. There can be multiple 'trafficTargets' sections.

        for entry2 in domains_with_properties['properties'][n]['trafficTargets']:
            server_names = json.dumps(entry2['servers'])
            handout_cnames = json.dumps(entry2['handoutCName'])
            #Convert to list
            handout_cnames = json.loads(handout_cnames)
            dict_response_servers = json.loads(server_names)
            d_cname.setdefault(full_property_name, []).append(handout_cnames)
            # Third loop for going through each server
            for entry3 in dict_response_servers:
                # Create and update on every cicle our dictionary with the property name and its associated servers. The server names will be added as a list to the  dictionary value.
                d_server.setdefault(full_property_name, []).append(entry3)
        n = n +1
        d_full['server-name'] = d_server
        d_full['handout-cname'] = d_cname
    return()


# Function that searches for a string in our created dictionary 'd'
def gtm_search_server(ip_fqdn_cname):
    no_search_hit = True
    print('\nDomains that contain your IP, FQDN or Handout CNAME ' + ip_fqdn_cname + ':')
    for searchname, propertyname in d_full.items():
        #print(propertyname)
        for propertynames, serverlist in propertyname.items():
            #print(values)
            for servername in serverlist:
                if servername == ip_fqdn_cname:
                    print(searchname + ' in:',propertynames)
                    no_search_hit = False
    if no_search_hit:
        print('\n*** Entry Not Found ***\n')
    return()


# Function that splits the input property name into property and domain.
def gtm_property_and_domain(gtm_property, domains, accountKey_unique):
    property_name = 'Not_Found'
    # Caputure all the domain names, i.e. ['items'][n]['name']
    for domain in domains:
        domain_matchstring = '.'+domain
        if domain_matchstring in gtm_property:
            property_name = gtm_property.replace(domain_matchstring,'')
            break
    return(property_name, domain_matchstring[1:])


# Function used to search for GTM properties
def gtm_property_details(property_name, domain_name, accountKey_unique):
    api_endpoint = urljoin(baseurl, '/config-gtm/v1/domains/' + domain_name + '/properties/' + property_name + accountKey_unique)
    logging.info('API Endpoint: ' + api_endpoint)
    response = session.get(api_endpoint)
    return(response)


# Get the data centers IDs associated to the requested domain
def gtm_data_centers(domain_name, accountKey_unique):
    api_endpoint = urljoin(baseurl, '/config-gtm/v1/domains/' + domain_name + '/datacenters' + accountKey_unique)
    logging.info('API Endpoint: ' + api_endpoint)
    response = session.get(api_endpoint)
    print(json.dumps(response.json(), indent=4, sort_keys=True))
    data_centers = json.loads(response.text)
    return(data_centers)


# Correlate the data center IDs with the data center names
def match_datacenter_name(data_centers):
    for data_center in data_centers['items']:
        if data_center['nickname'] == args.datacenter:
            data_center_id = data_center['datacenterId']
            break
        else:
            data_center_id = 'NOT FOUND'
    return(data_center_id)


# Get a GTM full property name
def get_property_details(user_property_name, accountKey_unique):
        domains = gtm_domains(accountKey_unique)
        property_name, domain_name = gtm_property_and_domain(user_property_name, domains, accountKey_unique)
        property_details = gtm_property_details(property_name, domain_name, accountKey_unique)
        return(property_details, domain_name, property_name)


# Upload a GTM property
def gtm_property_upload(property_details_json, domain_name, property_name, accountKey_unique):
    headers = {'content-type': 'application/json'}
    api_endpoint = urljoin(baseurl, '/config-gtm/v1/domains/' + domain_name + '/properties/' + property_name + accountKey_unique)
    logging.info('API Endpoint: ' + api_endpoint)
    response = session.put(api_endpoint, data=property_details_json, headers=headers)
    print(json.dumps(response.json(), indent=4, sort_keys=True))
    if response.status_code == 201:
        print("Property", property_name, 'succesfully updated/created')
    return()


# Main function
def main():
    global args

    parser = MyArgumentParser(
            description='Global Traffic Manager Tools', add_help=False
    )
    parser.add_argument('--version', action='version', version='GTM Tool v1.0')

    subparsers = parser.add_subparsers(title='Commands', dest='command', metavar="")

    create_parser = subparsers.add_parser('help', help='Show available help').add_argument('args', metavar="", nargs=argparse.REMAINDER)
    parser_search = subparsers.add_parser('search', help='Search for an IP Address, FQDN, CNAME handout in all GTM properties', add_help=False)
    parser_show = subparsers.add_parser('show', help='Show a GTM property details', add_help=False)
    parser_update = subparsers.add_parser('update', help='Modify and activate a property', add_help=False)
    parser_clone = subparsers.add_parser('clone', help='Clone a property with new Data Center Name and Servers', add_help=False)

    mandatory_search = parser_search.add_argument_group('required arguments')
    mandatory_search.add_argument('--value', required=True, help='Search for an IP Address, FQDN, CNAME handout')

    optional_search = parser_search.add_argument_group('optional arguments')
    optional_search.add_argument('-e', '--edgerc', help='Config file [default: ~/.edgerc]')
    optional_search.add_argument('-s', '--section', help='Config section in .edgerc [default: cloudlets]')
    optional_search.add_argument('-k', '--key', help='Account Switch Key')
    optional_search.add_argument('-v', '--verbose', action='store_true', help='Enable verbose mode')
    optional_search.add_argument('-vv', '--debug', action='store_true', help='Enable verbose mode')


    mandatory_show = parser_show.add_argument_group('required arguments')
    mandatory_show.add_argument('--property', required=True, help='Property name to search')

    optional_show = parser_show.add_argument_group('optional arguments')
    optional_show.add_argument('-e', '--edgerc', help='Config file [default: ~/.edgerc]')
    optional_show.add_argument('-s', '--section', help='Config section in .edgerc [default: cloudlets]')
    optional_show.add_argument('-k', '--key', help='Account Switch Key')
    optional_show.add_argument('-v', '--verbose', action='store_true', help='Enable verbose mode')
    optional_show.add_argument('-vv', '--debug', action='store_true', help='Enable verbose mode')


    mandatory_update = parser_update.add_argument_group('required arguments')
    mandatory_update.add_argument('--property', required=True, help='Property name to update')
    mandatory_update.add_argument('--datacenter', required=True, help='Data Center name to update')
    mandatory_update.add_argument('--state', choices={'ON', 'OFF'}, required=True, help='Update a DC state')

    optional_update = parser_update.add_argument_group('optional arguments')
    optional_update.add_argument('-e', '--edgerc', help='Config file [default: ~/.edgerc]')
    optional_update.add_argument('-s', '--section', help='Config section in .edgerc [default: cloudlets]')
    optional_update.add_argument('-k', '--key', help='Account Switch Key')
    optional_update.add_argument('-v', '--verbose', action='store_true', help='Enable verbose mode')
    optional_update.add_argument('-vv', '--debug', action='store_true', help='Enable verbose mode')


    mandatory_clone = parser_clone.add_argument_group('required arguments')
    mandatory_clone.add_argument('--property', required=True, help='Property name to clone')
    mandatory_clone.add_argument('--datacenter', required=True, help='Data Center Name')
    mandatory_clone.add_argument('--server', required=True, help='Server name or IP address')
    mandatory_clone.add_argument('--new_property', required=True, help='New GTM property name')

    optional_clone = parser_clone.add_argument_group('optional arguments')
    optional_clone.add_argument('-e', '--edgerc', help='Config file [default: ~/.edgerc]')
    optional_clone.add_argument('-s', '--section', help='Config section in .edgerc [default: cloudlets]')
    optional_clone.add_argument('-k', '--key', help='Account Switch Key')
    optional_clone.add_argument('-v', '--verbose', action='store_true', help='Enable verbose mode')
    optional_clone.add_argument('-vv', '--debug', action='store_true', help='Enable verbose mode')

    args = parser.parse_args()

    if len(sys.argv) <= 1:
        parser.print_help()
        return 0

    accountKey_append = accountKey_unique = ''
    if args.key:
        accountKey_unique = '?accountSwitchKey=' + args.key
        accountKey_append = '&accountSwitchKey=' + args.key

    global baseurl, session

    # Dictionary variables, d_full will be made of d_server and d_cname
    global d_server, d_cname, d_full
    d_server = {}
    d_cname = {}
    d_full = {}

    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    elif args.debug:
        logging.basicConfig(level=logging.DEBUG)

    if args.command == 'help':
        if len(args.args) > 0:
            if args.args[0] == 'update':
                parser_update.print_help()
        else:
            parser.print_help()
        return 0


    elif args.command == 'search':
    # The API calls take longer to run. So on the first run we save the dictionary to a file and use it for subsequent executions of the script. With a TTL of 10min.
        init_config(args.edgerc, args.section)
        file_name = ('inventory')
        if os.path.isfile(file_name) and ((time.time()-os.path.getctime(file_name)) < 600):
            file = open(file_name,'r')
            d_full = json.loads(file.read())
        else:
            print('\n*** Calling the GTM API to get all the domains... ***\n')
            domains = gtm_domains(accountKey_unique)
            for domain in domains:
                domains_with_properties = gtm_domain_properties(domain, accountKey_unique)
                gtm_traffic_targets(domain, domains_with_properties)

            file = open(file_name,'w')
            file.write(json.dumps(d_full))
        gtm_search_server(args.value)

    # Example d = {'onlinecare.online-cingular.akadns.net': ['origin-onlinecare-allen.cingular.com', 'origin-onlinecare-bothell.cingular.com'], 'onlinestorez.online-cingular.akadns.net': ['origin-onlinestorez.cingular.com']}


    elif args.command == 'show':
        init_config(args.edgerc, args.section)
        print('\n*** Calling the GTM API to get the property details.. ***\n')
        property_details, domain_name, property_name = get_property_details(args.property, accountKey_unique)
        print(json.dumps(property_details.json(), indent=4, sort_keys=True))


    elif args.command == 'update':
        init_config(args.edgerc, args.section)
        property_details, domain_name, property_name = get_property_details(args.property, accountKey_unique)

        #print(json.dumps(property_details.json(), indent=4, sort_keys=True))

        property_details_json = json.loads(property_details.text)

        if args.datacenter:
            if args.state == 'ON':
                dc_state = True
            elif args.state == 'OFF':
                dc_state = False

            # Get the Data Center ID.
            data_centers = gtm_data_centers(domain_name, accountKey_unique)
            data_center_id = match_datacenter_name(data_centers)

            found = False
            for index, traffic_target in enumerate(property_details_json['trafficTargets']):
                #print('INDEX=',index)
                #print('TRAFFIC TARGET=',traffic_target)
                #print(traffic_target['datacenterId'])
                if traffic_target['datacenterId'] == data_center_id:
                    print('Data Center Found:', args.datacenter, 'ID:', data_center_id)
                    print('Data Center State modified to:', args.state)
                    found = True
                    property_details_json['trafficTargets'][index]['enabled'] = dc_state

            if found == False:
                print('Data Center NOT found in property', args.property)

            property_details_json = json.dumps(property_details_json)
            gtm_property_upload(property_details_json, domain_name, property_name, accountKey_unique)


    elif args.command == 'clone':
        init_config(args.edgerc, args.section)
        print('\n*** Calling the GTM API to get the property details.. ***\n')
        property_details, domain_name, property_name = get_property_details(args.property, accountKey_unique)

        property_details_json = json.loads(property_details.text)

        # Get the Data Center ID.
        data_centers = gtm_data_centers(domain_name, accountKey_unique)
        data_center_id = match_datacenter_name(data_centers)

        property_details_json['name'] = args.new_property
        property_details_json['trafficTargets'][0]['datacenterId'] = data_center_id
        property_details_json['trafficTargets'][0]['servers'] = args.server.split()

        property_details_json = json.dumps(property_details_json)

        print(json.dumps(property_details.json(), indent=4, sort_keys=True))
        gtm_property_upload(property_details_json, domain_name, args.new_property, accountKey_unique)



# MAIN PROGRAM
if __name__ == "__main__":
    # Main Function
    main()
