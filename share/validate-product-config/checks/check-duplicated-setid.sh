#!/bin/bash

# we want to allow IDs that start with a digit, hence we can't use RelaxNG's
# xsd:ID data type, but we can use xmlstarlet to check

file=$1

setids=$($starlet sel -t -v "//@categoryid" $file | sort)
uniquecategoryids=$(echo -e "$categoryids" | sort -u)

[[ ! "$categoryids" == "$uniquecategoryids" ]] && \
  echo -e \
    "Some categoryid values are not unique. Check for occurrences of the following duplicated categoryid(s): " \
    $(comm -2 -3 <(echo -e "$categoryids") <(echo -e "$uniquecategoryids") | tr '\n' ' ') \
    "."

exit 0
