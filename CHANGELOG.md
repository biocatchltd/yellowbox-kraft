# Yellowbox-Kraft Changelog
## NEXT
### Internal
* updated github actions
* Added Python 3.15 to the test matrix (confluent-kafka builds from source on 3.15).
* Removed Python 3.8 and 3.9 from the test matrix.
* Default Kafka image is now bitnamilegacy/kafka:4.0.0-debian-12-r10.
* Restored the broker readiness wait and the kafka network alias in the tests.
## 0.1.1
### Added
* support for python 3.12
### Removed
* support for python 3.7
## 0.1.0
* initial
