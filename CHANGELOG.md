# Release History

## v6.4, 2021-11-23, sknorr

- Stitch:
  - Fix check for `<overridedesc/>`
- docservui.js:
  - Fix headline levels to improve SEO (a little)


## v6.3, 2021-11-18, sknorr

- Docserv² core/build-navigation:
  - Fix a number of errors/tracebacks resulting from problematic
    build instructions
- docservui.js:
  - Support descriptions for site section tabs


## v6.2, 2021-11-15, sknorr

- Build-navigation:
  - Slightly update the name of HTML templates:
     - `template-section-DEFAULT` ->
       `template-section-default`
     - `template-section-$NAME.$CYCLE` ->
        `template-section.$NAME.$CYCLE`
  - Do not resort site sections, keep order as defined in the INI


## v6.1, 2021-09-16, sknorr

- Docserv² core:
  - Do not include DocBook remarks and meta information in "beta"
    builds
- Build-navigation:
  - Correctly pick HTML templates based on the lifecycle value
    again 
- Product configuration schema:
  - `<docset/>` now allows the additional element
    `<listingversion/>` which can be used to override the
    `<version/>` value on homepage product listings


## v6.0, 2021-09-15, sknorr

- Docserv² core:
  - Added support for site sections; site sections allow for multiple
    high-level entry pages (#39)
- Docserv² INI config:
  - The INI now allows using relative paths to find Docserv² resources
  - The new target-based options `site_sections` and `default_site_section`
    allow configuring site sections
- Product configuration schema:
  - `<product/>` gained an optional `@site-section` attribute to allow
    associating products with one of these sections
  - `<product/>` gained an optional `@docset-sort` attribute to allow switching
    an individual product's versions from Z-A (descending) to A-Z (default)
    sorting in the version selector
  - `<docset/>`'s `<version/>` gained an optional `@includes-productname`
    attribute to indicate that the version text already includes the name of the
    product and is enough to uniquely identify this product
  - `<docset/>`s gained the optional `<overridedesc/>` element which allows to
    set up per-docset product descriptions.
- DC-Hash:
  - DC-Hash now supports `OUTPUTNAME` and `ADOC_ATTRIBUTES`, and is much better
    at deciding which content is duplicated and which is not (#260)
- Stitch:
  - Stitch now requires rather than permits the `--valid-languages` parameter
  - Stitch now requires the new `--site-sections` and `--default-site-sections`
    parameters
- docservui.js:
  - If there's only a single product displayed on the page, docservui.js will
    preselect that product and give hints about the situation to the page
    template


## v5.4, 2021-04-29, sknorr

- docservui.js:
  - Further improved `dsUiLoaded` variable state
  - Improved IE 11 compatibility of docservui.js


## v5.3, 2021-04-28, sknorr

- docservui.js
  - Fixed `dsUiLoaded` variable state


## v5.2, 2021-04-27, sknorr

- build-navigation:
  - Fixed `@titleformat` functionality on internal references
  - Updated output titles to adhere to the style
    "Product: Title - Subtitle"
  - Fixed date display on output pages


## v5.1, 2021-04-26, sknorr

- Included forgotten files that broke fragments support in 5.0
- Fixed build-navigation conditional that meant we'd add links to
  docsets with disabled navigation on internal homepages


## v5.0, 2021-04-26, sknorr

- Docserv² core:
  - Improved reliability of Git updates
  - Made use of daps2docker's new `filelist.json` option to more
    reliably find out about build successes
  - Fixed errors when submitting invalid JSON as a BI
  - Updated metadata cache scripts to also find product names and
    subtitles within documents
  - Allow running build instructions for products that do not have a
    `<builddocs/>` section
  - Do not copy build results when any of the builds was broken
- Navigation builder:
  - Added localizable SSI fragments code
- Docserv² INI config:
  - Added option to choose container image per target with
    `build_container = reference`
  - Added parameter `server_root_files` for files that need to be
    copied to the root directory of the server as-is
  - Allowed scaling number of threads automatically with
    `max_threads = max` in the INI
- Product configuration schema:
  - Updated version to 5.0
  - Added option to choose a specific build container image within a
    docset using `builddocs/buildcontainer/@image=reference`
  - Update supported subset of HTML to include `<br/>` and `<hr/>`
  - Added `@titleformat` attribute to `<deliverable/>`, `<ref/>`, and
    `<link/>` to allow selecting display of title/subtitle/docset/
    product name in the navigation UI
  - Added `docset/@navigation` as a replacement for
    `docset/@navigation-visible` and support the new value `disabled`
    which disabled building navigation for a docset altogether
  - Removed support for `<urlredirect/>` which was never supported in
    code
  - Removed support for `product/@navigation-visible` which was never
    supported in code
- docservui.js
  - Added variable dsUiLoaded, so dependant scripts can detect UI load
    state
  - Improved path normalization to avoid `//` in the output
  - Added support for basic localization


## v4.0, 2021-02-22, sknorr

- Docserv² core:
  - Fixed "Too many open files" issue (#199) by closing temporary
    parameter files
  - Allowed disabling sync to a target server
  - Added a mode where Docserv² does not send mail
- Schema:
  - Updated version number to 4.0
  - Allowed `<subdir>` as child of `<deliverable>`, so specific
    deliverables can be built from different subdirs
  - Removed support for `@translation-type="negative-list"` which went
    unused so far, `positive-list` is now called `list`
  - Removed the `@default` attribute from `<docset>` which had no
    current practical use


## v3.8, 2021-01-11, sknorr

- Use software license (GPL 3) consistently
- docservui.js:
  - Display correct month is displayed in the UI
  - Make language selector work on Chromium-based browsers
  - Display internal links that have no category
  - Fix version sort order for index page
  - Allow #product to preselect a product on the index page
  - Fix URL generation to allow downloading localized archive files
  - Improve presentation of archive files
- DocServ2 core:
  - Avoid syncing .git and similar directories
- schema/build-navigation:
  - Allow linking manually built archive files
  - Allow `<a rel=...>` attribute
  - Correctly export titles with XML special characters in them


## v3.7, 2019-09-02, sknorr

- Actually make unsupported.html page more useful
- Truncate error mails over 100k characters in length


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
