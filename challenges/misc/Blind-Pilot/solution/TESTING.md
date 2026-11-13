# GM verification

Run the field and planner unit tests with:

```sh
python solution/test_challenge.py
```

Run the reference solver against the local service started by `docker-compose.yml`:

```sh
python solution/solve.py 127.0.0.1 5103
```
