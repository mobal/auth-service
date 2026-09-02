# Changelog

## [0.9.0](https://github.com/mobal/auth-service/compare/v0.8.0...v0.9.0) (2026-09-02)


### Features

* add docstrings on models explaining OAuth2 value contracts ([5e1786d](https://github.com/mobal/auth-service/commit/5e1786db11ca780efb65259c4276808f411fbe77))
* **test:** add more user service tests ([6a4d90e](https://github.com/mobal/auth-service/commit/6a4d90e1a6989b7f63a41d042215171429534c5b))
* updated README.md ([f1c7303](https://github.com/mobal/auth-service/commit/f1c730361232424848843d38fdfc3d95bdbf76e5))
* use user service validation endpoint instead of password hashing ([afa0f42](https://github.com/mobal/auth-service/commit/afa0f42abc5567f02f1ace081be855427ebf02c8))


### Bug Fixes

* add ConditionExpression and ConsistentRead to service repository ([47981d5](https://github.com/mobal/auth-service/commit/47981d56418d7f90c6249016f450abb1405fbc45))
* add list of allowed urls ([02b8803](https://github.com/mobal/auth-service/commit/02b88037c9ef92109f72b2044793648cfb7442b7))
* add missing password hasher dep ([cfb08ec](https://github.com/mobal/auth-service/commit/cfb08ec402bc53d8842108d7e0fd1404724857ac))
* add missing WWW-Authenticate headers on 401 responses ([6c02455](https://github.com/mobal/auth-service/commit/6c02455b5190aee059b6b8292ab96292e6ce26c3))
* address code review findings ([e322c91](https://github.com/mobal/auth-service/commit/e322c9191f1fd7250dfad2e1e0b976742c45d588))
* address critical RFC/security gaps for production readiness ([d27751f](https://github.com/mobal/auth-service/commit/d27751f59dc83cac1996cc444d1e8b67bddb11a0))
* address test false positives and infrastructure issues ([38f7486](https://github.com/mobal/auth-service/commit/38f748622594b6e0510a3dfd789499130386cf76))
* address test quality and edge-case coverage in unit and integration tests ([bfcf5bb](https://github.com/mobal/auth-service/commit/bfcf5bb170f0d8c4f16c953340efe5a69a1306a9))
* **auth:** remove bearer token query parameter fallback ([55ed4e3](https://github.com/mobal/auth-service/commit/55ed4e3477d0cc88d32861b687194b95d935fb8a))
* cache ssm parameters ([1db9be5](https://github.com/mobal/auth-service/commit/1db9be59938a2c0bb0ee6be03ef7cbd21d43a9e8))
* check Attributes availability ([9133b9c](https://github.com/mobal/auth-service/commit/9133b9c2fee9290b38f6e626e297fd69ae183c41))
* ContextVar without default ([29fd2f8](https://github.com/mobal/auth-service/commit/29fd2f88bfab73220c949f0ec8ec7e464e4155fe))
* correlation ID pollution across requests in concurrent environments ([e4a642c](https://github.com/mobal/auth-service/commit/e4a642c6403895c00aea898ae1dc833b827c4b69))
* CORS allows all origins ([92169cf](https://github.com/mobal/auth-service/commit/92169cfe7ef6da48e4ead5058e4e6489bb909755))
* CORS allows all origins on an auth service ([32db926](https://github.com/mobal/auth-service/commit/32db9266860bbce7ea703e2efcd6f6aba1e58a11))
* dead default in request.scope.get() ([55bb6c3](https://github.com/mobal/auth-service/commit/55bb6c35b8cdb031a7835f9f90d07124d9488212))
* derive test JWT issuer from settings.app_name ([a346935](https://github.com/mobal/auth-service/commit/a3469353cd4c7d85d5536926cc6d08197b67048d))
* disable log_event (do not leak tokens and other sensitive information) ([03e2083](https://github.com/mobal/auth-service/commit/03e2083d4d2ec545c445b334f2d3149889cefbdc))
* duplicate ExceptionMiddleware ([dee7e81](https://github.com/mobal/auth-service/commit/dee7e81bb334a902973ff170257c69651284c370))
* enable debug mode in non prod environment only ([c638ad2](https://github.com/mobal/auth-service/commit/c638ad2dbe7eb6c577fa3e5d718e00a9e7cfddf2))
* env file loading order wrong ([40ab013](https://github.com/mobal/auth-service/commit/40ab01303a5e04ba0c6235ba4b8f10d77b3011db))
* ErrorResponse timestamp evaluated at class time ([a400c2f](https://github.com/mobal/auth-service/commit/a400c2f78a19af8bbadb2dfdea542d929eca0627))
* forbid extra parameters ([eaf72d7](https://github.com/mobal/auth-service/commit/eaf72d75187de8549a71f189a4280fc91f8bb1a4))
* grant type accepts empty strings ([3101c87](https://github.com/mobal/auth-service/commit/3101c87728ec9f743bf935497a09a21b64883232))
* imports (and removed accidentaly pushed review documents) ([31f1312](https://github.com/mobal/auth-service/commit/31f1312d04ed65e13be4f106e403e3e093ef909e))
* incomplete PyJWT exception coverage ([6e4af56](https://github.com/mobal/auth-service/commit/6e4af5669d7cf9ce7c76a973cc4a41d517cff260))
* inconsistent return types between get_by_id and get_by_refresh_token ([5f9e6ad](https://github.com/mobal/auth-service/commit/5f9e6ad8a1cba1cae101dc96bbae6c72672afbcf))
* invalid qa ([f82d18d](https://github.com/mobal/auth-service/commit/f82d18d8accf5e480bedd712cd59d11f55f42d32))
* **jwt:** add audience and issuer validation to token decode ([b7dc314](https://github.com/mobal/auth-service/commit/b7dc3143822114d2b8e69282b204317688f1f9d5))
* linting ([6d3a4bb](https://github.com/mobal/auth-service/commit/6d3a4bb624728d30654289b7aa3e3ccf4d30ee03))
* linting ([256a8db](https://github.com/mobal/auth-service/commit/256a8dbef14247d2da28f2647c4ba7d07ecb01f6))
* logger initialized before env files ([fbe1440](https://github.com/mobal/auth-service/commit/fbe14407adb5388433d7f532605bfbbeda16e694))
* lower requirements layer size ([3c28172](https://github.com/mobal/auth-service/commit/3c28172e7ae88d7d4e86f2fcfa99e34c215fa036))
* make JWTBearer.token_service required and add missing TokenRepository.consume_by_id ([4c7a40e](https://github.com/mobal/auth-service/commit/4c7a40e3e98fbfa18ebdb09b0e410f835f46c55c))
* misleading parameter name code_id in delete_by_id ([df0a74c](https://github.com/mobal/auth-service/commit/df0a74cfc87e22ba3b0987154528ea4143c53f2b))
* misleading parameter name code_id in delete_by_id and consume_by_id ([54dae6d](https://github.com/mobal/auth-service/commit/54dae6de7fdf8eabc1f138b182666e99d1b94106))
* missing return type annotations ([e70f906](https://github.com/mobal/auth-service/commit/e70f906b75605fd4cd5006addac59db9c4b87292))
* missing return type annotations in repositories and auth_service ([a2824ec](https://github.com/mobal/auth-service/commit/a2824ec2f48b6111675fa2db84ae84e3685021d6))
* no default for STAGE env var in settings fixture ([3ec170a](https://github.com/mobal/auth-service/commit/3ec170a55333b3d4dffa5bfa36bb1a8ee2035e0d))
* overly broad except Exception in parse authorization header ([4bc1b60](https://github.com/mobal/auth-service/commit/4bc1b600d144a0639971f58939c5ba2d8529d339))
* pydantic ValidationError in JWT token parsing ([aee9f3a](https://github.com/mobal/auth-service/commit/aee9f3a16e08df093fd04c45a47bd504a8c59b49))
* redundant import pytest as pytest ([d98ae01](https://github.com/mobal/auth-service/commit/d98ae019f722e2e0abd3668ad1aef38061941645))
* refresh token reuse ([54152c2](https://github.com/mobal/auth-service/commit/54152c27b421aba40d530da8f85055ea37e9a13f))
* remove duplicate logging and exception-level logging for expected client errors ([5b77a23](https://github.com/mobal/auth-service/commit/5b77a23006cb2961374e54e339ed3589b3b3a99a))
* removed the unused clients: dict[str, Any] = {} global and its now-unnecessary from typing import Any import ([9bb9126](https://github.com/mobal/auth-service/commit/9bb912619385913d2d27d613d7689f3623dab459))
* replaced every f-string logger call across the 10 affected files in app/ with lazy %s formatting, so log messages are only formatted when the respective log level is enabled ([147355a](https://github.com/mobal/auth-service/commit/147355a7a5e532fdbaab1832fdb258320dc8cfff))
* replaced f string to templates in logging ([871eee3](https://github.com/mobal/auth-service/commit/871eee35bd3f358d45327dc0361498cd2f9687a2))
* return RFC 6749 error codes and wire JWT bearer dependency ([4d0a29d](https://github.com/mobal/auth-service/commit/4d0a29d3c9da0722385656f6acb2e7cf4cc91ea0))
* settings fixture missing jwt_token_lifetime, causing pre-existing test failures ([6c51868](https://github.com/mobal/auth-service/commit/6c518680a11d68b914bfbae84726cbae6b4bb915))
* shared mutable state on JWTBearer ([e75b0d4](https://github.com/mobal/auth-service/commit/e75b0d49c07c536b45c42bdd8826081902520a92))
* sindle use enforcement for authorization codes ([f73770b](https://github.com/mobal/auth-service/commit/f73770b60c343a2a45f5d22d1c333270f253d09b))
* support list of string ([03b03ec](https://github.com/mobal/auth-service/commit/03b03ec45fd6ea5bd137783bfbfee6797260671d))
* **tests:** align repository and service tests with actual API ([a85e7a9](https://github.com/mobal/auth-service/commit/a85e7a9b4b7ba005be25a984f32d4bfe5fb28ea2))
* timezone inconsistency - use pendulum.now('UTC') consistently ([b9cea3f](https://github.com/mobal/auth-service/commit/b9cea3f74fe167890377669c3fe4cddda3fe2b6f))
* timezone inconsistency in authorization code repository ([b0206b2](https://github.com/mobal/auth-service/commit/b0206b261088fc1f6417e43e2e9e9dd2a6cb56fc))
* token can be None, causing AttributeError → 500 instead of 401 ([40efd49](https://github.com/mobal/auth-service/commit/40efd495c4b55e07555de6b940996eaf14f6a79a))
* type mismatch os.environ.get() to get_parameter() ([9323380](https://github.com/mobal/auth-service/commit/932338021d44241ea9848dce8dca1fd19de9cbf0))
* unnecessary round-trip conversion for expire_at ([b4346ea](https://github.com/mobal/auth-service/commit/b4346eabbbac7e5fc02bdfe1f95de832ec1bdfb0))
* use constant-time comparison for PKCE challenge validation ([ecb9016](https://github.com/mobal/auth-service/commit/ecb9016cae2c2b44ff1d3f1dbbf7db61e7365f65))
* use zip bytes for hash value ([717f890](https://github.com/mobal/auth-service/commit/717f89001bec3263f511658fac15392699954b51))
* wrong OAuth error message for response type ([e22f8f7](https://github.com/mobal/auth-service/commit/e22f8f724013b1d738e6b45d9dab089c7ede1f76))


### Documentation

* actualize all review and audit reports to 2026-07-19 ([058336e](https://github.com/mobal/auth-service/commit/058336e79073a7fba2ecae7a7e92410ebb0c8786))
* actualize review reports to reflect fixed findings ([1ddf83a](https://github.com/mobal/auth-service/commit/1ddf83a7502eebfe10462ffbf7caccc947a80c01))
* add fix_priority.md ([cc53fd2](https://github.com/mobal/auth-service/commit/cc53fd2492b99e0fe34096502f7a637ec0f9bfa6))
* consolidate review docs into single reference ([3400cf9](https://github.com/mobal/auth-service/commit/3400cf9f533f2ff8c8327b70243d3a3a419b008f))
* fill in AGENTS.md project facts ([06cf632](https://github.com/mobal/auth-service/commit/06cf632edb8be1c01647d1dda841119f20d5c427))
* move project reports and plans to docs/ directory ([81d25d9](https://github.com/mobal/auth-service/commit/81d25d9f8a4f418d6a62e774f1a8c0b1f8ed9738))
* verify and update docs ([cc75b79](https://github.com/mobal/auth-service/commit/cc75b79f7c5275975a084d7ec7968939a623320b))

## [0.8.0](https://github.com/mobal/auth-service/compare/v0.7.0...v0.8.0) (2026-04-01)


### Features

* add authorize endpoint ([553e74a](https://github.com/mobal/auth-service/commit/553e74a7aca9965cb8a95268ab2524527e49d1bc))
* add main.tf ([a11b6d1](https://github.com/mobal/auth-service/commit/a11b6d1e793ecc362d35c2e5ae3b7b7a86671ca9))
* add more test to reach 90%+ test coverage ([9a2b361](https://github.com/mobal/auth-service/commit/9a2b361152954955cae98a2f22b88953eadbb5f4))
* add services table ([954090e](https://github.com/mobal/auth-service/commit/954090efb3881f25855e0910546f96f612d70a78))
* **auth:** implement RFC 6749 compliant client credentials for service-to-service communication ([a8237e7](https://github.com/mobal/auth-service/commit/a8237e78d703a1b4f57cc54a18a1428d558e5496))
* enrich logging ([1335212](https://github.com/mobal/auth-service/commit/13352120aa093f45109908f1316a51023e86e65e))
* get service by name instead of id ([a16f214](https://github.com/mobal/auth-service/commit/a16f214c75a5d481cad9b892a265c67e9e704c42))
* Harden client credentials Basic auth validation with strict Base64 decoding ([3ae92c8](https://github.com/mobal/auth-service/commit/3ae92c828b5932dab21200269d30cc739a89bdcc))
* set default refresh token length to 32 ([3a7155c](https://github.com/mobal/auth-service/commit/3a7155ccb92c0f21e9620e561040e0df26193f74))
* updated users api url to /api/v1/ ([8111a61](https://github.com/mobal/auth-service/commit/8111a61a868324b15d5e142b86fc3f2041e21993))


### Bug Fixes

* add missing iam roles ([f713a8c](https://github.com/mobal/auth-service/commit/f713a8cf746e4d966d911aaea3ed499ed9c9ecff))
* added missing env variables ([8cb64b9](https://github.com/mobal/auth-service/commit/8cb64b9aa17c5cbf3e22c4d20073844588cab573))
* bug fixes based on claude's advice ([144bb6a](https://github.com/mobal/auth-service/commit/144bb6a8aa4f60e87b8c68944019f1a82dfe4d99))
* bugs ([d8de007](https://github.com/mobal/auth-service/commit/d8de007275ed8e2e6bf0372ed8f2dc0d1cdf1f85))
* check for empty items array ([76ed718](https://github.com/mobal/auth-service/commit/76ed718c2fcc58a249cc5ae5c13481ba31544962))
* do not require jwt token during refresh ([a359a4b](https://github.com/mobal/auth-service/commit/a359a4baa8d6778374e2676db142569eb60cfab7))
* do not set refresh token as none if not exists ([25f9d7e](https://github.com/mobal/auth-service/commit/25f9d7e132cabb900dfaafe81d49a7df0042ab6d))
* fixed some bugs / misconfiguration in ci.yml ([78f8fad](https://github.com/mobal/auth-service/commit/78f8fad69683d344c84365b7355680d9ff262c42))
* get user data from items array ([fc7947d](https://github.com/mobal/auth-service/commit/fc7947dac92368037feacfa80496492b428e1481))
* moved cors middleware to the last ([65d97fc](https://github.com/mobal/auth-service/commit/65d97fc6c55a6123a2893011625db2b4b9eed1bd))
* remove unused policy ([16eb00d](https://github.com/mobal/auth-service/commit/16eb00dfa155a96f83ce54d27a086af95f1ca2e4))
* removed duplications ([2b2adbc](https://github.com/mobal/auth-service/commit/2b2adbc8c03c164190a778e291f7e336003e563e))
* removed unused attr and index (copy'n'paste failure) ([11909ac](https://github.com/mobal/auth-service/commit/11909aca282e888e65befa99587204d7bb9d48bb))
* replaced test email domain ([a29cfab](https://github.com/mobal/auth-service/commit/a29cfab348ac4ad1efeaa8e2f7fb0675bcf29f4a))
* replaced usjonresponse with jsonreaponse (deprecated) ([32622e9](https://github.com/mobal/auth-service/commit/32622e9bcbb2361da7409d2aa0da72fcf3e1ece4))
* restore run check on every branch after push or new pr ([c9fce72](https://github.com/mobal/auth-service/commit/c9fce72ee06856a55154c572602f196dd07a1ddd))
* typo ([2a99da6](https://github.com/mobal/auth-service/commit/2a99da645f49b78a5d1ac289f4b9599508aeb296))
* urls ([e986957](https://github.com/mobal/auth-service/commit/e986957d591d7963ee8386b6756faee51410eca4))
* use proper cache headers (RFC 6749) ([cf7ea6e](https://github.com/mobal/auth-service/commit/cf7ea6e94ffe9f63701219f63992caa247e6075f))
* use revoke token during logout ([6b19d61](https://github.com/mobal/auth-service/commit/6b19d6160f84a640323a4c7f38fe3a89b35a7fcd))
* user service base url ssm param name ([f82570a](https://github.com/mobal/auth-service/commit/f82570a2fed84495b6f8b84f3a18b7648678af0b))
* user service ssm param name [#2](https://github.com/mobal/auth-service/issues/2) ([315bf0b](https://github.com/mobal/auth-service/commit/315bf0b7b6d2ac66d5bfab99f63a373dc0aa6cd5))

## [0.7.0](https://github.com/mobal/auth-service/compare/v0.6.0...v0.7.0) (2026-02-26)


### Features

* add cors middleware ([d0c0a54](https://github.com/mobal/auth-service/commit/d0c0a541b8af5bfceb4b982c8a22091878551210))
* add refresh token expiration ([7bbab2e](https://github.com/mobal/auth-service/commit/7bbab2e32888594dbc801cf7fa86755902524fd1))
* added pre_authorization wrapper ([c5ba608](https://github.com/mobal/auth-service/commit/c5ba608359beab57e785c1dafa7eb9194a918960))
* added rate limiting middleware ([696c8b9](https://github.com/mobal/auth-service/commit/696c8b9bf823e05c42221f18823e9f1784982094))
* added role check ([a16dfe3](https://github.com/mobal/auth-service/commit/a16dfe37cc4bf8067fd22a4f9b74e23cda794c39))
* work with artifacts ([3086653](https://github.com/mobal/auth-service/commit/3086653c09b07901d1476e679ce516c8be802abd))


### Bug Fixes

* add stage to apigw url ([39b458e](https://github.com/mobal/auth-service/commit/39b458e463449f59f60de996a3146c944b3f1794))
* removed unused error_id ([2d0c221](https://github.com/mobal/auth-service/commit/2d0c22132d67ff6b1e84977f308906109f1205be))
* typo ([c2c536b](https://github.com/mobal/auth-service/commit/c2c536bfac9e4e490341a1340fde808056277096))

## [0.6.0](https://github.com/mobal/auth-service/compare/v0.5.1...v0.6.0) (2026-02-11)


### Features

* add support for multiple .env files ([7fbb0f3](https://github.com/mobal/auth-service/commit/7fbb0f390f145b3b4b8106864ebb6e7e6d737561))
* added .env.example ([a288b04](https://github.com/mobal/auth-service/commit/a288b04ce4c3065bbfb5e3ea950b38b34be25e45))
* added /register endpoint ([5e3ef14](https://github.com/mobal/auth-service/commit/5e3ef14730495f44edfe1b058271c35dfe636c91))
* added Dockerfile ([c0b349e](https://github.com/mobal/auth-service/commit/c0b349ee12ab075b69c7d1ca8012ab4eca3c5c14))
* added TokenResponse ([11b0af2](https://github.com/mobal/auth-service/commit/11b0af2f96886a8e99fde4000feca6c8bdfb336a))
* refreshed workflow.yml ([bb903f3](https://github.com/mobal/auth-service/commit/bb903f378499b915740d2714074639f0db397a69))
* replaced mypy with ty, added tflint and minor refactors ([9bdc0fe](https://github.com/mobal/auth-service/commit/9bdc0fe7a4878e118c787f1c72ce056f4ec9c9f8))
* set display_name to optional ([d6b5183](https://github.com/mobal/auth-service/commit/d6b5183528d19a7623e1ef6c5f669b875e893930))
* updated error format (renamed message to error and added timestamp) ([187b544](https://github.com/mobal/auth-service/commit/187b544ae413a2c0b01c055291ce109a022efb4a))


### Bug Fixes

* added password handling during registration ([39ab82b](https://github.com/mobal/auth-service/commit/39ab82bb6b37bb9c59e298dfd9d504621069ec2e))
* python version number ([1737593](https://github.com/mobal/auth-service/commit/17375934747783b795faf80a0c62184ad767dd12))

## [0.5.1](https://github.com/mobal/auth-service/compare/v0.5.0...v0.5.1) (2025-12-01)


### Bug Fixes

* logging ([5786dc1](https://github.com/mobal/auth-service/commit/5786dc1c6aac0805062c7afc0362a7c44b793b64))
* run GH workflow on pull request ([1a73dad](https://github.com/mobal/auth-service/commit/1a73dada30401adaf9acd0cfe3392a644e3987b0))

## [0.4.0](https://github.com/mobal/auth-service/compare/v0.3.0...v0.4.0) (2025-05-14)


### Features

* replaced json response with ujson response ([8be89dc](https://github.com/mobal/auth-service/commit/8be89dc6487cbec35ee1f55ad64c176f154c0bd6))

## [0.5.0](https://github.com/mobal/auth-service/compare/v0.4.0...v0.5.0) (2025-05-16)


### Features

* use aws context id if available and x-correlation-id is not set ([50087c9](https://github.com/mobal/auth-service/commit/50087c95335df898abf3b6964d44581a40cdfe75))


### Bug Fixes

* replaced Pipfile.lock with uv.lock (oops) ([69d1cd4](https://github.com/mobal/auth-service/commit/69d1cd4bdaac18e8c403bbe5ec53b8427ed528a5))

## [0.4.0](https://github.com/mobal/auth-service/compare/v0.3.0...v0.4.0) (2025-05-14)


### Features

* replaced json response with ujson response ([8be89dc](https://github.com/mobal/auth-service/commit/8be89dc6487cbec35ee1f55ad64c176f154c0bd6))

## [0.3.0](https://github.com/mobal/auth-service/compare/v0.2.0...v0.3.0) (2025-05-13)


### Features

* removed unnecessary async functions and replaced pipenv with uv ([bbae3c0](https://github.com/mobal/auth-service/commit/bbae3c00204699b8515d7e60c51d8940ae6baff7))

## [0.2.0](https://github.com/mobal/auth-service/compare/v0.1.0...v0.2.0) (2025-04-18)


### Features

* added bandit ([0b11bb8](https://github.com/mobal/auth-service/commit/0b11bb88c18b3ff4121bdffcb08cfb8263156db9))
* added jwt auth test ([c409bf5](https://github.com/mobal/auth-service/commit/c409bf56c5bed9817593c6aef9dd681aea436bd8))
* added jwt bearer tests ([0edbfa8](https://github.com/mobal/auth-service/commit/0edbfa8b3d4edd7a1ad10f3e054b0ec2f5fdd930))
* added missing auth service unit tests ([a9b3258](https://github.com/mobal/auth-service/commit/a9b3258af9aa55df7b56196c81ccbf14a9499e04))
* added missing integration tests ([7c6d72d](https://github.com/mobal/auth-service/commit/7c6d72d8c06efbcccb763913419fb52b8c98caf0))
* added token repository unit tests ([5f608c2](https://github.com/mobal/auth-service/commit/5f608c22a0c8447eccb30c25e4d3b8df28e21667))
* added token service unit tests ([21ebc8f](https://github.com/mobal/auth-service/commit/21ebc8ff1608a0dce08d3f9c3ea062324b97c1d0))
* added verbose to bandit ([809d86c](https://github.com/mobal/auth-service/commit/809d86cd6af6f22ec6e74e257d9ce5d95de83b92))
* removed user roles ([aa5a34d](https://github.com/mobal/auth-service/commit/aa5a34d5be23e2cad3d5938f8664328762867239))
* separate test tasks ([2604d15](https://github.com/mobal/auth-service/commit/2604d15a7b85ddd2d864af8bbfce437e3b9b6496))
* updated workflow.yml ([1605348](https://github.com/mobal/auth-service/commit/160534859b94cc1c4dcaaed576423f9cad41064a))


### Bug Fixes

* fixed mypy errors ([7435208](https://github.com/mobal/auth-service/commit/7435208c6467e14964e6d3f3a0b82e4beaaf1eec))

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
