# How to run this?

Config

- Needs the ledger files mounted at /data
- Needs the source files (.py) mounted at /app/src

```
docker build --tag book-api bookkeeper/api
docker run --volume "$(pwd)/accounts:/data" --volume "$(pwd):/app/src" --publish 5005:5005 -it book-api
```

For the `/collect.py` endpoint, here's how it is used.

```sh
python3 <(curl --silent http://localhost:5005/collect.py)
```
