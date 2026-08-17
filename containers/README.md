# Container isolation

`ContainerSandbox` runs tool commands with no network, dropped Linux capabilities, a PID limit,
CPU/memory limits, a read-only root filesystem and only the candidate directory mounted writable.
Use `--container-image` with an image that legally contains the required Vitis HLS installation and
licence configuration. The included project does not redistribute AMD software.

This reduces the danger of executing generated C/C++, but its not a proof of perfect isolation.
Operate on a disposable host or VM, keep credentials outside the mounted directory, and review the
container runtime and AMD licence requirements with the system owner.
