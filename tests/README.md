# Instructions for running tests

Install deps (e.g. pytest):

```bash
make install-pydeps-test
```

Some tests shell out to CLI tools (`ps`, `ifconfig`, ...). On UNIX install
them with:

```bash
make install-sysdeps-test
```

Run tests:

```bash
make test
```

Run tests in parallel (faster):

```bash
make test-parallel
```

Run a specific test:

```bash
make test ARGS=tests/test_system.py::TestDiskAPIs
```

Test C extension memory leaks:

```bash
make test-memleaks
```
