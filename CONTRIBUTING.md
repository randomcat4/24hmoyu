# Contributing

Contributions are welcome when they preserve the project's authorization boundary.

Before adding a collector capability:

1. link the official provider documentation;
2. document whether authorization is user-only or administrator-gated;
3. add tests for pagination and permission-denied behavior;
4. use synthetic/sanitized fixtures only;
5. do not add browser-cookie, local-database, or undocumented-endpoint fallbacks;
6. mark unverified behavior as unsupported instead of guessing.

Run tests with:

```bash
python -m pip install -e '.[dev]'
pytest
```
