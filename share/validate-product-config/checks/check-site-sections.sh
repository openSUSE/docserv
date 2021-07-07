#!/bin/bash

# Make sure all site sections from the document are also configured
# in the INI file

file=$1

if [[ "$valid_site_sections" ]]; then
  site_value=$($starlet sel -t -v "//@site-section" $file )
  valid_site_sections=$(echo "${valid_site_sections}" | tr -s " " "\n")
  unrecognized_site_section=$(comm -1 -3 <(echo -e "$valid_site_sections") <(echo -e "$site_value"))

  [[ "$unrecognized_site_section" ]] && \
    echo -e \
      "Got value \"${unrecognized_site_section//$'\n'/ }\", but expected \"${valid_site_sections//$'\n'/ }\". Check your files."
fi

exit 0
