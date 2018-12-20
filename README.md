# What is this?
Docserv² is a set of scripts and configuration files to automatically build
DocBook XML documentation in several languages and publish the result as
static web content.

# Installing Docserv²
RPM builds are available in the openSUSE Build Service in the
[`Documentation:Tools` repository](https://build.opensuse.org/project/show/Documentation:Tools).

## openSUSE Leap 15.0
   1. ```zypper ar --refresh https://download.opensuse.org/repositories/Documentation:/Tools/openSUSE_Leap_15.0/Documentation:Tools.repo```
   2. ```zypper in docserv```
   3. ```systemctl enable docker.service && systemctl start docker.service```
   4. Change the configuration in ```/etc/docserv```
   5. ```systemctl enable docserv@docserv.service && systemctl start docserv@docserv.service```


# Running Docserv² From the Git Repository

Docserv² does not run straight out of the Git repository. To use it, first
set up a development environment:

   1. `cd` to the local repository checkout
   2. Source the dev-mode.sh script: `. dev-mode.sh`
   3. Create a virtual environment with Python: `python3 -m venv .venv`
   4. Activate the virtual environment: `source .venv/bin/activate`
   5. Install Docserv² with setuptools in develop mode: `python3 setup.py develop`


# Scripts in This Repository

Parts of Docserv² that can be run individually:
  * `docserv`: The main build scheduling script (see below).
  * `docserv-createconfig`: Create the outline of an XML configuration for a
     product (see below)
  * `docserv-stitch`: Validate the Docserv² XML configuration and merge it into
    a single big XML file (see `--help`).
  * `docserv-buildoverview`: Build the overview HTML pages for Docserv²
    (see `--help`).


# Docserv² Configuration

The Docserv² configuration consists of three parts:

  * INI file: Configures paths and basic parameters.
  * XML configuration files: Configures product definitions
  * Web Templates: Configures HTML templates and UI translation strings


# Running Docserv² Itself

   1. Start the server with `docserv docserv`
   2. Send a build instruction, for example: `curl --header "Content-Type: application/json" --request POST --data '[{"docset": "15ga","lang": "de-de", "product": "sles", "target": "internal"}, {"docset": "15ga","lang": "en-us", "product": "sles", "target": "internal"}]' http://localhost:8080`


# Using `docserv-createconfig`

The `docserv-createconfig` tool helps to create a template for the XML
configuration from an DocBook XML repository. It scans through available
branches and DC files and creates an XML file that then needs to be fixed.
The script will guess some basic values, but everything should be checked.

Example:
```
docserv-createconfig --languages="en-us de-de" --contact="mail@example.com" /path/to/repo
```
