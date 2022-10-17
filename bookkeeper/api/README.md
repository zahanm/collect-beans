# How to run this?

Config

- Needs the ledger files mounted at /data
- Needs the source files (.py) mounted at /src

```
docker build --tag book-api bookkeeper/api
docker run --rm --volume "$(pwd)/../accounts:/data" --volume "$(pwd):/app/src" --publish 5005:5005 -it book-api
```
