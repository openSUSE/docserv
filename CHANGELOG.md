# Release History

## v3.6, 2019-09-02, sknorr

- Make unsupported.html page more useful
- Remove <styleroot/> element from schema (never properly implemented)
- Remove beta_warning parameter from INI (never properly implemented)
- Handle --draft/--meta/--remarks options supplied via INI or XML
  config
- Handle XSLT parameters supplied via INI or XML config
  (needs daps2docker 0.11)
- Allow omitting the default language's name from path components
- Set <link rel=canonical> by default
- Allow copying favicon.ico and .htaccess file
- Minor bug fixes


## v3.5, 2019-08-06, sknorr

- Improve error mails: omit some unnecessary details, add interesting
  ones
- Improve DC hash tool to properly normalize profiling values
- Fix two tracebacks (hopefully)


## v3.4, 2019-08-04, sknorr

- Support `<ref/>` elements in the web UI (and not only in the config)
- Much better support for localized pages via docservui.js (still
  completely missing any semblance of actual UI translation, but at
  least we show the right documents now)
- Make `<sortname/>` actually sort items in the UI
- Fix `@navigation-visible=hidden` functionality (works now)
- Add build dates to the web UI
- Add `@lifecycle` value to web UI (for beta and unpublished documents)
- Add links to Zip files in the web UI


## v3.3, 2019-08-02, sknorr

- Correctly pick up file extension of the template


## v3.1/v3.2, 2019-08-02, sknorr

- Make sure not to delete product pages of current product


## v3.0, 2019-08-02, sknorr

- Update product configuration schema to 3.0
  - Rename `<extralinks/>` to `<external/>`
  - Allow internal links
  - Add default docset value
  - For product acronym, use `<acronym/>` instead of `<shortname/>`
  - Add `<sortname/>` tag for product sort name
- Use `@lifecycle` values across build process
- Major improvements to build-navigation
  - Generate JSON files for all content
  - Use updated template system
- Tons of other fixes


## v2.0, 2019-06-03, sknorr

- Update product configuration schema to 2.0
  - Allow document categories
  - Allow unlinked documents
  - Make translation configuration more manageable by introducing
    "positive-list"/"full" mode in addition "negative-list" mode
- Improve validation of product configuration
- Reorganize share directory
- Ship example configuration within /usr/share/ directory to avoid
  overwriting real configuration under /etc/ in all circumstances


## v1.0, 2019-05-16, sknorr

- A release out of necessity, not a big 1.0
- Update configuration schema to 0.9.10
- Many improvements to docserv-createconfig


## v0.9.21 and earlier

- Turmoil
