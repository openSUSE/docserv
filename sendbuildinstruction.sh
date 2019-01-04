#!/bin/bash
# Generate a JSON string and send it to a Docserv² instance.
#
# To use:
#
# 1-Provide a file `server.conf` in the same directory as this script. Include
#   the following contents:
#     server=http://server.address  # server address
#     port=8080                     # server port
#     targets=target,names          # target sync servers, as defined in the INI
# 2-Run this script:
#   ./$0 --products=PRODUCTS --docsets=DOCSETS --langs=LANGS
#
#   * all parameters are mandatory
#   * "=" characters are mandatory
#   * multiple values may be comma-separated or space-separated


me=$(test -L $(realpath $0) && readlink $(realpath $0) || echo $(realpath $0))
mydir=$(dirname $me)

out() {
  >&2 echo -e "$1"
  exit 1
}

app_help() {
  sed -rn '/#!/{n; p; :loop n; p; /^[ \t]*$/q; b loop}' $me | sed -r -e 's/^# ?//' -e "s/\\\$0/$(basename $me)/"
  exit
}

products=
docsets=
langs=

for i in "$@"
  do
    case $i in
      -h|--help)
        app_help
      ;;
      --products=*|--product=*|-p=*)
        products=$(echo "$i" | sed -r -e 's/^[^=]+=//' -e 's/,/ /g')
      ;;
      --docsets=*|--docset=*|-d=*)
        docsets=$(echo "$i" | sed -r -e 's/^[^=]+=//' -e 's/,/ /g')
      ;;
      --langs=*|--lang=*|-l=*)
        langs=$(echo "$i" | sed -r -e 's/^[^=]+=//' -e 's/,/ /g')
      ;;
      *)
        unknown+="  $i\n"
      ;;
    esac
done

if [[ -f $mydir/server.conf ]]; then
  . server.conf
else
  out "No server.conf found. See --help."
fi
([[ ! "$targets" ]] || [[ ! "$server" ]] || [[ ! "$port" ]]) &&
  out "server.conf does not include all necessary parameters. See --help."

[[ "$unknown" ]] &&
  out "Unknown command-line parameters present:\n${unknown}See --help."

([[ ! "$products" ]] || [[ ! "$docsets" ]] || [[ ! "$langs" ]]) &&
  out "Missing at least one command-line parameter. See --help."

targets=$(echo "$targets" | sed -r -e 's/^[^=]+=//' -e 's/,/ /g')

# ---

json='['

for target in $targets; do
  for product in $products; do
    for docset in $docsets; do
      for lang in $langs; do
        json+='{'
        json+='"target":"'$target'",'
        json+='"product":"'$product'",'
        json+='"docset":"'$docset'",'
        json+='"lang":"'$lang'"'
        json+='},'
      done
    done
  done
done

json=$(echo "$json" | sed -r 's/,$/]/')

echo -e "JSON as she spoke (to $server:$port):\n$json"


curl \
  --header "Content-Type: application/json" \
  --request POST \
  --data "$json" \
  ${server}:${port}
