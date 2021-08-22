#!/usr/bin/env zsh

# arguments: <config filename> <output file> <main journal> <DB file with transactions>

# categorises the transactions and puts them in another DB
if python ../collect-beans/categoriser.py $1 $4 categorised_beans.db; then
  # puts the transactions in the file
  if python ../collect-beans/insert.py $1 categorised_beans.db $2 $3 > tmp-$2; then
    mv tmp-$2 $2
  fi
fi
