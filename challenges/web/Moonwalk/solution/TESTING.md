# GM verification

Install the challenge runtime and solution dependencies with:

```sh
python -m pip install -r src/requirements.txt -r solution/requirements.txt
```

Run the in-process checks with:

```sh
python solution/test_challenge.py
```

Run the reference solver against the local service described by `docker-compose.yml`:

```sh
python solution/solve.py http://127.0.0.1:5102
```
