This contains a docker image to run Fava

Configuration:

- Bind mount the ledger files at `/data`
- Expose port `5000` for the Fava website

Commands to run

```
docker build --tag fava .
docker run --volume "$(pwd)/../accounts:/data" -p 5000:5000 -it fava
```
