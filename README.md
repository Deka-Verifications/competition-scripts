# Competition Scripts

This repository contains scripts and definitions that are useful to execute
benchmark experiments for competitions of automatic tools,
like solvers, verifiers, and test generators.

The scripts are based on the benchmarking framework [BenchExec](https://github.com/sosy-lab/benchexec) [1].

## Instructions for Execution

The concrete instructions for how to use the scripts in this repository
are provided in the competition-specific repositories.

- SV-COMP uses this repository as as submodule in repository https://gitlab.com/sosy-lab/sv-comp/bench-defs

  Documentation for execution: https://gitlab.com/sosy-lab/sv-comp/bench-defs#sv-comp-reproducibility

- Test-Comp uses this repository as as submodule in repository https://gitlab.com/sosy-lab/test-comp/bench-defs

  Documentation for execution: https://gitlab.com/sosy-lab/test-comp/bench-defs#test-comp-reproducibility


## Computing Environment on Competition Machines

The following instructions are specific to competitions that are executed on the compute cluster at LMU Munich (Apollon machines),
and try to explain the computing environment that is used for the competitions.


### Installed Ubuntu packages

A list of Ubuntu packages that are installed on the competition packages is available here:
https://gitlab.com/sosy-lab/benchmarking/competition-scripts/-/blob/main/test/Ubuntu-packages.txt


### Docker Image
The competition provides a Docker image that tries to provide an environment
that has mostly the same packages installed as the competition machines:
- Docker definition: https://gitlab.com/sosy-lab/benchmarking/competition-scripts/-/blob/main/test/Dockerfile.user.2022
- Docker image: `registry.gitlab.com/sosy-lab/benchmarking/competition-scripts/user:latest`
- Test if the tool works with the installation:
  - Unzip tool archive to temporary directory `<TOOL>` (**`<TOOL>` must be an absolute path!**)
  - `docker pull registry.gitlab.com/sosy-lab/benchmarking/competition-scripts/user:latest`
  - `docker run --rm -i -t --volume=<TOOL>:/tool --workdir=/tool registry.gitlab.com/sosy-lab/benchmarking/competition-scripts/user:latest bash`
  - Start tool


### Parameters of RunExec

<!-- Fetch latest version from the Ansible configuration for the competition machines:
https://gitlab.com/sosy-lab/admin/sysadmin/ansible/-/blob/master/roles/vcloud-worker/templates/Config.j2
Last synchronized: 2020-12-05 from commit 670c4eb
-->

```
--container
--read-only-dir /
--hidden-dir /home
--hidden-dir /var/lib/cloudy # environment-specific
--set-cgroup-value pids.max=5000
--output-directory <work-dir>
--overlay-dir <run-dir>
--quiet
--maxOutputSize 2MB
--dir <work-dir>
--output <logfile>
--full-access-dir /sys/fs/cgroup # competition-specific
--timelimit <depends on benchmark XML>
--softtimelimit 900s # only if specified in benchmark XML
--memlimit 15GB
--memoryNodes 0 # hardware-specific
--cores 0-7 # hardware-specific
```


## References

[1]: Dirk Beyer, Stefan Löwe, and Philipp Wendler.
     Reliable Benchmarking: Requirements and Solutions.
     International Journal on Software Tools for Technology Transfer (STTT), 21(1):1-29, 2019.
     https://doi.org/10.1007/s10009-017-0469-y


