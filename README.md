# Search GTM for hostnames and properties

Script Functions:

1. Input an IP address, a hostname (FQDN) or a handout CNAME, and the tool returns in which GTM properties they are contained.
2. Search for a GTM properties and display all its parameters.
3. Because there can be hundreds of domains and properties for a particular account the first execution of the tool will create a file which contains the output. Then on subsequent executions the file will be used instead of making all the API calls again. The file has a TTL of 10 min.
4. Update a property's Data Center state to ON or OFF.
5. Clone a property and change its data center, server and property name.

## Install

Installation is done via `akamai install`:

```
$ akamai install global-traffic-manager
```

Running this will run the system `python setup.py` automatically.

## Updating

To update to the latest version:

```
$ akamai update global-traffic-manager
```

## Usage:
```
usage: akamai gtm [--version]  ...

Global Traffic Manager Tools

optional arguments:
  --version  show program's version number and exit

Commands:

    help     Show available help
    search   Search for an IP Address, FQDN, CNAME handout in all GTM
             properties
    show     Show a GTM property details
    update   Modify and activate a property
    clone    Clone a property with new Data Center Name and Servers
```

## Example #1: List a server name

```
$ akamai gtm search --value secret.origin.com

```

## Example #2: Get a property details

```
$ akamai gtm show --property www.example.com.akadns.net

```

## Example #3: Update a property by turning ON/OFF a Data Center and activate.

```
$ akamai gtm update --property www.example.com.akadns.net --datacenter Dallas --state ON

```

## Example #4: Clone a property and change its data center, server and property name.

```
$ akamai gtm clone --property www.example.com.akadns.net --datacenter Santiago --server 11.22.33.44 --new_property weighted

```
