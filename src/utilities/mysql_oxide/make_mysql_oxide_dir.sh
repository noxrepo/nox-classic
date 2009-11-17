
# builds fake 'nox' dir used by mysql_oxide.  See readme

if  [ $# -lt 1 ] 
then

  echo "usage: ./make_mysql_oxide_dir [absolute path to asesna/nox/src directory]"
  exit 1

fi

cp -r -s $1 . 

# need to delete the soft-line before copying
rm nox/lib/core.py
cp core.py nox/lib
rm nox/apps/ndb/ndbcomponent.py 
cp ndbcomponent.py nox/apps/ndb

echo "done creating mysql_oxide directory"

