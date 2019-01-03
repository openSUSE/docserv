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

# Dependencies

Docserv² depends on the following software:

  * Linux with systemd
  * Python 3.4, 3.5, or 3.6
  * `pygit2`
  * Docker Engine
  * Bash
  * `xmllint`, `xsltproc`
  * `xmlstarlet`
  * Jing (needs a JVM)

# Running Docserv² From the Git Repository

Docserv² does not run straight out of the Git repository. To use it, first
make sure that the dependencies listed above are installed and then set up
a development environment:

   1. `cd` to the local repository checkout
   2. Source the dev-mode.sh script: `. dev-mode.sh`
   3. Create a virtual environment with Python: `python3 -m venv .venv`
   4. Activate the virtual environment: `source .venv/bin/activate`
   5. Update the pip Python package manager: `pip install -U pip setuptools`
   6. The next step depends on package compatibility, and hence is distribution-dependent:
      * *On openSUSE Leap 15.0:* Make sure the RPM package `python3-pygit2` is installed
      * *On other distributions:* Install requirements via pip: `pip install -r requirements.txt`
   7. Install Docserv² with setuptools in develop mode: `python3 setup.py develop`
   8. Make sure the Docker service is running: `systemctl start docker`
      (To run Docserv² as a regular user, make sure your user is part of the group `docker`.)

# Scripts That Are Part of Docserv²

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

Preparation:

   1. Enable/start the Docker engine: `systemctl enable docker.service && systemctl start docker.service`
   2. Adapt the configuration in `/etc/docserv` to your needs.
   3. Choose how to run Docserv²:
      * When running from an installed system package, you can run Docserv²
        as a service: `systemctl enable --now docserv@docserv.service`
      * When running from the Git repostory or you are just trying out
        Docserv², use: `docserv docserv`
        The second `docserv` denotes the name of your INI file.

Test your installation:
Send a build instruction, for example: `curl --header "Content-Type: application/json" --request POST --data '[{"docset": "15ga","lang": "de-de", "product": "sles", "target": "internal"}, {"docset": "15ga","lang": "en-us", "product": "sles", "target": "internal"}]' http://localhost:8080`


# Using `docserv-createconfig`

The `docserv-createconfig` tool helps to create a template for the XML
configuration from an DocBook XML repository. It scans through available
branches and DC files and creates an XML file that then needs to be fixed.
The script will guess some basic values, but everything should be checked.

Example:
```
docserv-createconfig --languages="en-us de-de" --contact="mail@example.com" /path/to/repo
```
