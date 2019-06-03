#!/bin/bash

# make sure all language codes from the document are also configured in the INI
# file

file=$1

if [[ "$valid_languages" ]]; then
  languages=$($starlet sel -t -v "//@lang" $file | sort -u)
  unrecognized_languages=$(comm -1 -3 <(echo -e "$valid_languages") <(echo -e "$languages"))
  [[ "$unrecognized_languages" ]] && \
    echo -e \
      "Some lang attributes are not supported by your configuration INI. Check for occurrences of the following unsupported lang attribute(s): "$(echo -e "$unrecognized_languages" | tr '\n' ' ')"."
fi

exit 0
