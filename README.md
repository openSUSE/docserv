# What is it about?
This is a set of scripts and configuration files to automatically build DocBook XML documentation in several languages and publish the result as static web content.

# Installation
Automatic RPM builds are available in the openSUSE Build Service in the Documentation:Tools repository (https://build.opensuse.org/project/show/Documentation:Tools).

## openSUSE 15.0
   1. ```zypper ar https://download.opensuse.org/repositories/Documentation:/Tools/openSUSE_Leap_15.0/Documentation:Tools.repo```
   2. ```zypper in docserv```

## openSUSE 42.3
   1. ```zypper ar https://download.opensuse.org/repositories/Documentation:/Tools/openSUSE_Leap_42.3/Documentation:Tools.repo```
   2. ```zypper in docserv```

# Running Docserv² From the Git Repository

Not all parts of Docserv² can be run directly from the repository. To use the
parts that can be, first source the `dev-mode.sh` script that sets environment
variables for Docserv².

   1. `cd` to the local repository checkout
   2. Source the dev-mode.sh script: `. dev-mode.sh`
