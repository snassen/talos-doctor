"""talos-doctor: checks that a Mac is ready for Talos, and says the next step when it is not.

It reads only and never reads a secret. It runs on its own, before Talos is installed
(`uvx --from git+<this repository's URL> talos-doctor`), and from inside Talos as `talos doctor`.
"""

__version__ = "0.1.0"
