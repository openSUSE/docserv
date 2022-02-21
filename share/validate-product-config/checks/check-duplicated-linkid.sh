#!/bin/bash

# we want to allow IDs that start with a digit, hence we can't use RelaxNG's
# xsd:ID data type, but we can use xmlstarlet to check
# @linkids only need to be locally unique (i.e. within one <internal/> element).

file=$1

externals=$($starlet sel -t -v "count(//weblinks)" $file)

for external in $(seq 1 $externals); do
  linkids=$($starlet sel -t -v '(//weblinks)['"$external"']/link/@linkid' $file | sort)
  uniquelinkids=$(echo -e "$linkids" | sort -u)

  curdocset=$($starlet sel -t -v '(//weblinks)['"$external"']/ancestor::docset/@setid' $file)

  [[ ! "$linkids" == "$uniquelinkids" ]] && \
    echo -e \
      "Some linkid values are not unique. Check for occurrences of the following duplicated linkid(s) within the docset ${curdocset}: " \
      $(comm -2 -3 <(echo -e "$linkids") <(echo -e "$uniquelinkids") | tr '\n' ' ') \
      "."
done

exit 0
