#!/usr/bin/env zsh

# arguments: <config filename> <journal file> <DB file with transactions>

# categorises the transactions and puts them in another DB
if python ../collect-beans/categoriser.py $1 $3 categorised_beans.db; then
  # puts the transactions in the file
  if python ../collect-beans/insert.py $1 categorised_beans.db $2 > tmp-$2; then
    mv tmp-$2 $2
  fi
fi
