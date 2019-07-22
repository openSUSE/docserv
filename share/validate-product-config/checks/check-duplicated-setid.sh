#!/bin/bash

# we want to allow IDs that start with a digit, hence we can't use RelaxNG's
# xsd:ID data type, but we can use xmlstarlet to check

file=$1

setids=$($starlet sel -t -v "//@setid" $file | sort)
uniquesetids=$(echo -e "$setids" | sort -u)

[[ ! "$setids" == "$uniquesetids" ]] && \
  echo -e \
    "Some setid values are not unique. Check for occurrences of the following duplicated setid(s): " \
    $(comm -2 -3 <(echo -e "$setids") <(echo -e "$uniquesetids") | tr '\n' ' ') \
    "."

exit 0
