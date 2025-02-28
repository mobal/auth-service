# Changelog

## 0.1.0 (2025-02-28)


### Features

* added .python-version ([5e9cc5c](https://github.com/mobal/auth-service/commit/5e9cc5cb12711dd505a365b27f91dccef4bbf8ba))
* added archives to gitignore ([3b9e9a0](https://github.com/mobal/auth-service/commit/3b9e9a05bc29427f8061d36fbcaff96034a7185b))
* added locals.tf ([21b3074](https://github.com/mobal/auth-service/commit/21b3074b60417dc28e79ea7372fa87c74ef8050d))
* added mypy ([d3c32a1](https://github.com/mobal/auth-service/commit/d3c32a13d09e7ee3a89e3b674ac01406518f3f36))
* Added pytest-env ([4e8f6f6](https://github.com/mobal/auth-service/commit/4e8f6f620ff31dbcd74f439645b396f29f3a0375))
* added refresh tests ([78a8b4e](https://github.com/mobal/auth-service/commit/78a8b4e02e53df08a0026994230b735babdf4646))
* added refresh token ([6555bc0](https://github.com/mobal/auth-service/commit/6555bc014915952beffa781cb91170dd8fb680d2))
* added refresh token index ([9b0be81](https://github.com/mobal/auth-service/commit/9b0be8197c471db2cbe880a349cc1faa2e1fe816))
* added refresh token tests ([56992b1](https://github.com/mobal/auth-service/commit/56992b19795ec5667c108367e1c1f8051d2099f0))
* added release-please ([6f99541](https://github.com/mobal/auth-service/commit/6f99541ddbdb43beaf66df209647178bbd73f229))
* added repository tests ([76570e4](https://github.com/mobal/auth-service/commit/76570e481c0170d8b9e89a7c62baf620b66d9659))
* added terraform files ([b1fd6c2](https://github.com/mobal/auth-service/commit/b1fd6c2abd812086176b8e7c766f2357a7b62a18))
* added token repository tests ([d226ad5](https://github.com/mobal/auth-service/commit/d226ad5017ac600e1961b52dd33008f887869017))
* added tokens table ([76bf376](https://github.com/mobal/auth-service/commit/76bf37636dd170c7e828c16de9e44693c63ba27f))
* added tokens table ([b668884](https://github.com/mobal/auth-service/commit/b66888496ffbac4a85ef08651836dc9afbd14655))
* added ttl to ttl field ([ae0fe0d](https://github.com/mobal/auth-service/commit/ae0fe0ddfd073927f90018d3fafd562fd964e77e))
* added user private claim to jwt token ([8cccc7b](https://github.com/mobal/auth-service/commit/8cccc7bd443732eedca27e41e02e14974060c2a7))
* added X-Api-Key ([3cfa19c](https://github.com/mobal/auth-service/commit/3cfa19c19782139935ee5317c0fa796d39cb4957))
* added X-Api-Key to cache service calls ([1a4d807](https://github.com/mobal/auth-service/commit/1a4d80704352dee22adf89e6a5b4baf4c0104bf8))
* first implementation of refresh token ([850b3d9](https://github.com/mobal/auth-service/commit/850b3d99175c1d5454f4c9f61dcd497b0763c32a))
* get jwt secret and cache service api key from parameter store ([6419e89](https://github.com/mobal/auth-service/commit/6419e897a5a0bd3f51881a8d62f19fb069d0c32c))
* re added the use of cache service ([fc22bda](https://github.com/mobal/auth-service/commit/fc22bdae41ddd19a095d9e1a7d45f4504676582a))
* removed serverless ([c339822](https://github.com/mobal/auth-service/commit/c3398221636f26eddb34135f9f85d07ee12158a6))
* removed vpc config ([63cf103](https://github.com/mobal/auth-service/commit/63cf1039000c81cbfbaff6623633405e41e5d6e0))
* Replaced refresh jwt token with string ([418f1de](https://github.com/mobal/auth-service/commit/418f1de433b9974da9e26750f465e4bc98a83d42))
* token repository implementation ([c167aaf](https://github.com/mobal/auth-service/commit/c167aaf7a507a8a6e41d787c5b8a0128b83d442c))
* use token service instead of cache service during token validation ([30a58f7](https://github.com/mobal/auth-service/commit/30a58f7dcae55c0ec18b63ca8080503a95755a40))
* use token_hex instead of uuid for refresh tokens ([8b50e2c](https://github.com/mobal/auth-service/commit/8b50e2c20a02b10d1727524b3466dd021088f20c))


### Bug Fixes

* Added mypy and fixed errors ([ec98ba0](https://github.com/mobal/auth-service/commit/ec98ba01cfa4b7bd134e40c1dbef7b569c2faf14))
* added user to jwt token ([4cbf82d](https://github.com/mobal/auth-service/commit/4cbf82d4860dddde0e887dd6d72ae36bc5aba9bf))
* fixed error, missing iam policies and typos ([115d715](https://github.com/mobal/auth-service/commit/115d715030c39c510a95d01e1dee4905516eb9d4))
* fixed typo ([23e0428](https://github.com/mobal/auth-service/commit/23e04281359329b8e7836c49d8934549d4af0032))
* fixed variable names ([c0e6170](https://github.com/mobal/auth-service/commit/c0e6170fbf7c5e40fe05534b83d21b7255b542eb))
* replaced app timezone with default timezone ([1ad2b9a](https://github.com/mobal/auth-service/commit/1ad2b9a41a1c46cd1e408ec4136d049acb49e7e5))
* Revert arm64 to x86_64 due to compatibility issues ([cbc8225](https://github.com/mobal/auth-service/commit/cbc8225a27b727a1b6d9070ce77c138721affda6))
* set default asyncio fixture loop scope ([cb6238d](https://github.com/mobal/auth-service/commit/cb6238d7c630158d1d2bf954b63d207ab07bb77d))
* unindexed attributes removed ([fdd238e](https://github.com/mobal/auth-service/commit/fdd238ec06adac37ac1159bdd409c2a772c77526))
* Updated serverless.yml ([ac23364](https://github.com/mobal/auth-service/commit/ac233646bfacbb11be0eacc2d4c956820603b3ff))
* use isinstance instead of type ([aca5bbc](https://github.com/mobal/auth-service/commit/aca5bbc52f48f1886385ca0b2b31c4475b25b71b))
* use str sub in jwt tokens ([971aaef](https://github.com/mobal/auth-service/commit/971aaefbace8899a041c50d75bf0e12257f5cfd5))
* variable naming ([2142dae](https://github.com/mobal/auth-service/commit/2142daef1cbc1d6841da7bc11d31e8f5f954560b))
* wrong return type ([8040811](https://github.com/mobal/auth-service/commit/80408110635bc0ba8409b119ecd06ea72e9275be))
