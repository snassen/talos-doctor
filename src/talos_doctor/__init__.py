"""talos-doctor: checks that a Mac is ready for Talos, and says the next step when it is not; and screens a
change (a pull request, a diff) for text aimed at a model before any agent reads it (talos_doctor.screen).

It reads only and never reads a secret. It runs on its own, before Talos is installed
(`uvx --from git+<this repository's URL> talos-doctor`), and from inside Talos as `talos doctor`.
"""

__version__ = "0.2.0"
