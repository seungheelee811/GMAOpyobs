# ChangeLog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

# [Unreleased]

### Added

### Fixed

### Removed

# [v1.0.6] 2023-09-08

### Added

- mxd04 and vx04 will write out gridded angstrom exponent if available

### Fixed

### Removed

# [v1.0.5] 2023-06-15

### Added

- mxd04 Level3 gridded product writes out the number of observations that went into the grid cell
- man.py function to create a concatenated of all the seperate cruises

### Fixed

- reading date/time variables from MAN concatenated file needs to be unicode not byte

### Removed

# [v.1.0.4] 2023-06-07

### Added

### Fixed

- removed all instances of using the 'types' module in pyobs

### Removed

# [v1.0.3] 2023-05-25

### Added

- add interpolated 490 AOD to aeronet.py. lines up with VIIRS wavelengths
- subroutine binObsCnt3D to binObs_py to counts obs in NNR L3 files
- vx04.py VIIRS reader

### Changed

### Fixed

### Removed

# [v1.0.2] 2023-05-17

### Added

### Changed

### Fixed

- mxd04.writeods now writes a 'post_anal' file. this saves the original retrieved AOD in the ods files

### Removed 

## [1.0.1] - 2023-05-16

### Fixed

- bug in config.py. integer divide needs // in python3
- bug in icarrtt.py. Config call not updated when going to python3

### Added

- Added changelog enforcer and yaml linter

## [1.0.0] - 2023-05-11

### Added

- Initial release
- Constructing GMAOpyobs from bits and pieces of GMAO_Shared/GMAO_pyobs

