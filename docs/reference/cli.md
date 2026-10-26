<!-- Generated file. Do not edit by hand. -->
<!-- Source: src/pyinit/cli.py. Regenerate with: just docs -->

# CLI reference

Generate new Python projects from data-driven profiles.

**Usage**:

```console
$ pyinit [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Commands**:

* `new`: Create a new project from a profile.
* `list`: List available profiles.
* `describe`: Show a profile or artifact.

## `pyinit new`

Create a new project from a profile.

**Usage**:

```console
$ pyinit new [OPTIONS] {profile} [directory]
```

**Arguments**:

* `profile`: Profile id, for example app-cli.  [required]
* `directory`: Target directory (default: current directory).  [default: .]

**Options**:

* `--python <str>`: Python version X.Y (3.11 or newer).  [default: 3.12]
* `--no-check`: Skip the final &#x27;just check&#x27;.
* `--dry-run`: Print the plan without writing anything.
* `--profile-file <path>`: Load an external profile TOML file.
* `--help`: Show this message and exit.

## `pyinit list`

List available profiles.

**Usage**:

```console
$ pyinit list [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `pyinit describe`

Show a profile or artifact.

**Usage**:

```console
$ pyinit describe [OPTIONS] {identifier}
```

**Arguments**:

* `identifier`: Profile or artifact id.  [required]

**Options**:

* `--help`: Show this message and exit.
