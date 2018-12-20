# What is it about?
This is a set of scripts and configuration files to automatically build DocBook XML documentation in several languages and publish the result as static web content.

# Installation
Automatic RPM builds are available in the openSUSE Build Service in the Documentation:Tools repository (https://build.opensuse.org/project/show/Documentation:Tools).

## openSUSE 15.0
   1. ```zypper ar --refresh https://download.opensuse.org/repositories/Documentation:/Tools/openSUSE_Leap_15.0/Documentation:Tools.repo```
   2. ```zypper in docserv```
   3. ```systemctl enable docker.service && systemctl start docker.service```
   4. Change the configuration in ```/etc/docserv```
   5. ```systemctl enable docserv@docserv.service && systemctl start docserv@docserv.service```

# Running Docserv² From the Git Repository

Not all parts of Docserv² can be run directly from the repository. To use the
parts that can be, first source the `dev-mode.sh` script that sets environment
variables for Docserv².

   1. `cd` to the local repository checkout
   2. Source the dev-mode.sh script: `. dev-mode.sh`
   3. Create a virtual environment with Python: `python3 -m venv .venv`
   4. Activate the virtual environment: `source .venv/bin/activate`
   5. Install docserv with setuptools in develop mode: `python3 setup.py develop`
   6. Adapt the configuration files to your needs.
   7. Start the server with `docserv docserv`
   8. Send a build instruction: `curl --header "Content-Type: application/json" --request POST --data '[{"docset": "15ga","lang": "de-de", "product": "sles", "target": "internal"}, {"docset": "15ga","lang": "en-us", "product": "sles", "target": "internal"}]' http://localhost:8080`
