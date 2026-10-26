# Yellowbox-Kraft Changelog
## 0.1.2
### Added
* Python 3.15 support
### Changed
* Default Kafka image to bitnamilegacy/kafka:4.0.0-debian-12-r10
### Fixed
* Kafka startup readiness now waits for the server to respond
* Outer Kafka listener advertises `DOCKER_EXPOSE_HOST` (default `127.0.0.1`) instead of `localhost`, so clients do not follow an IPv6 `localhost` address when the broker port is IPv4-only
### Internal
* Updated GitHub Actions workflows
## 0.1.1
### Added
* support for python 3.12
### Removed
* support for python 3.7
## 0.1.0
* initial
