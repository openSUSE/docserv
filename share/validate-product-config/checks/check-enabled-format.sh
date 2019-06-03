#!/bin/bash

# all format tags need at least one format attribute set to "1" or "true"

file=$1

format_issues=$($starlet sel -t -c "//format[not(@*='true') and not(@*='1')]" $file)
count_format_issues=$(echo -e "$format_issues" | sed 's/>/>\n/g' | wc -l)

# FIXME: welp! terribly unhelpful error message here
[[ "$format_issues" ]] && \
  echo -e \
    "There is/are $count_format_issues format element(s) where no attribute is set to \"true\" or \"1\"."

exit 0
