# What is this?
Docserv² is a daemon to semi-automatically build
DAPS-compatible DocBook XML and AsciiDoc documentation sources and generate
accompanying Web pages for navigating the result.

High notes:

* Supports HTML, PDF, Single-HTML, and EPUB output formats
* Support for localized documentation
* Documents created outside of Docserv² can be linked to from the navigational
  pages
* Output directory tree is all-static Web content
* Separation of build server and publishing server(s)
* Documentation sources are automatically synchronized from a remote Git
  repository
* Output documents can be rebuilt and synchronized to publishing servers using
  a simple API call
* Rigorous configuration format that (hopefully) prevents errors etc.


# Installing Docserv²
RPM builds are available in the openSUSE Build Service in the
[`Documentation:Tools` repository](https://build.opensuse.org/project/show/Documentation:Tools).

## openSUSE Leap 15.1
   1. ```zypper ar --refresh https://download.opensuse.org/repositories/Documentation:/Tools/openSUSE_Leap_15.1/Documentation:Tools.repo```
   2. ```zypper in docserv```

# Dependencies

Docserv² depends on the following software:

  * Linux with systemd
  * Python 3.4, 3.5, or 3.6
  * `pygit2`, `lxml`
  * Docker Engine
  * Bash
  * `xmllint`, `xsltproc`
  * `xmlstarlet`
  * Jing (needs a JVM)
  * `daps2docker` (https://github.com/openSUSE/daps2docker or available from the
    openSUSE Build Service's `Documentation:Tools` repository)

# Running Docserv² From the Git Repository

Docserv² does not run straight out of the Git repository. To use it, first
make sure that the dependencies listed above are installed and then set up
a development environment:

   1. Make sure the Docker service is running: `systemctl start docker`
      (To run Docserv² as a regular user, make sure your user is part of the group `docker`.)
   2. `cd` to the local repository checkout
   3. Source the dev-mode.sh script: `source dev-mode.sh`
   4. Make sure that the right configuration (INI) directory is chosen (defaults
      to the configuration directory from this repository). To set a different one, use
      `export DOCSERV_CONFIG_DIR=/path/to/dir`.
   5. Create a virtual environment with Python: `python3 -m venv .venv`
   6. Activate the virtual environment: `source .venv/bin/activate`
   7. Update the pip Python package manager: `pip install -U pip setuptools`
   8. Install requirements via pip: `pip install -r requirements.txt`
   9. Install Docserv² with setuptools in develop mode: `python3 setup.py develop`

# Scripts That Are Part of Docserv²

Parts of Docserv² that can be run individually:
  * `docserv`: The main build scheduling script (see below).
  * `docserv-createconfig`: Create the outline of an XML configuration for a
     product (see below)
  * `docserv-stitch`: Validate the Docserv² XML configuration and merge it into
    a single big XML file (see `--help`).
  * `docserv-build-navigation`: Build the navigation HTML pages for Docserv²
    (see `--help`).


# Docserv² Configuration

The Docserv² configuration consists of three parts:

  * INI file: Configures paths and basic parameters.
  * XML configuration files: Configures product definitions
  * Web Templates: Configures HTML templates and UI translation strings


# Running Docserv² Itself

## Preparation:

   1. Make sure that the server(s) you want to sync to are set up with
      passwordless SSH access for the users `docserv` or `root` on your machine.
   2. Make sure your machine has a working command-line mail setup via
      `sendmail`.
   3. Enable/start the Docker engine: `systemctl enable --now docker.service`
   4. Adapt the configuration in `/etc/docserv` to your needs.
   5. Choose how to run Docserv²:
      * When running from an installed system package, you can run Docserv²
        as a service: `systemctl enable --now docserv@docserv.service`
      * When running from the Git repostory or you are just trying out
        Docserv², use: `docserv docserv`
        The second `docserv` denotes the name of your INI file.


## Testing Your Installation:

Send a build instruction, for example: `curl --header "Content-Type: application/json" --request POST --data '[{"docset": "15ga","lang": "de-de", "product": "sles", "target": "internal"}, {"docset": "15ga","lang": "en-us", "product": "sles", "target": "internal"}]' http://localhost:8080`
To send a build instruction, you can also use `sendbuildinstruction.sh` from
this repository. For more information, see its `--help`.

## Making Docserv² Run Reliably

Since this is a massive-scale tool that ferociously handles exabytes of
information, it can be helpful to increase the number of file descriptors
that may be open at the same time: `sudo ulimit -n 4096`. (Before starting
Docserv², notably.)


# Using `docserv-createconfig`

The `docserv-createconfig` tool creates a template for the XML product
configuration from a DAPS-compliant Git repository. It scans through available
branches and DC files and creates an XML file that then needs to be enhanced
manually. The script will guess many basic values, but the file needs to be
checked after creation and will not be valid or useful immediately.

1. Make sure you have a local repository clone of the Git repository to
   build the configuration file available.
2. Run the script: `docserv-createconfig /path/to/repo`
3. Answer the questions.
4. At the end, `docserv-creatconfig` will produce a file. Move it to the
   correct configuration directory and further edit it there.


# Developing Web Templates

Web templates allow customizing the web front-end of Docserv2. There is an
example template in `config/templates/` in this Git repository.

Our web templates currently consist of the following files:

* `/path/to/template/dir/template-main.html` - main index page, copied into the
  directory for each UI language
* `/path/to/template/dir/template-product.html` - a product page, copied into
  the directory for each docset
* `/path/to/template/dir/template-unsupported.html` - a listing of unsupported
  documents (which will only be available within Zip archives and not unpacked)
* `/path/to/template/dir/res/*` - web resources, such as CSS, Javascript, or
  images. Docserv2 will automatically copy a Javascript file called
  `docservui.js` into this directory. This is an offer you can use to parse
  the JSON data that the templates rely on but there is no obligation to use it.

The HTML templates must literally include a Javascript block with the following
variables to properly work with `docservui.js`:

* `template-main.html`:
  ```
  <script>
  var basePath = '@{{#base_path#}}';
  var templateExtension = '@{{#template_extension#}}';
  var pageRole = 'main';
  var pageLanguage = '@{{#ui_language#}}';
  </script>
  ```

* `template-product.html`:
  ```
  <script>
  var basePath = '@{{#base_path#}}';
  var templateExtension = '@{{#template_extension#}}';
  var pageRole = 'product';
  var pageLanguage = '@{{#ui_language#}}';
  var pageProduct = '@{{#product#}}';
  var pageDocSet = '@{{#docset#}}';
  </script>
  ```

* `template-unsupported.html`:
  ```
  <script>
  var basePath = '@{{#base_path#}}';
  var templateExtension = '@{{#template_extension#}}';
  var pageRole = 'unsupported';
  var pageLanguage = '@{{#ui_language#}}';
  </script>
  ```


All three of the HTML template files largely depend on JSON data to fill them
in. To locally test whether everything works without running a server, you
need to disable some browser security mechanisms:

* Firefox: In `about:config`, set `security.fileuri.strict_origin_policy` to
  `false`.

* Chrome: Start the browser with `chromium --allow-file-access-from-files`
