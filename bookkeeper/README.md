# How to run this?

Config

- Needs the ledger files mounted at /data
- Needs the source files (.py) mounted at /src

```
docker build --tag bookkeeper .
docker run --rm --volume "$(pwd)/../accounts:/data" --volume "$(pwd):/src" -it bookkeeper collect-and-so
rt /data/CONFIG.yaml
```

Note that there are two positional arguments:

1. The operations to run
1. The location of the `CONFIG.yaml` file.
