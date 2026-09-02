graph TD
    A[Start Refactor] --> B[Update Dependencies]
    B --> C[Update Production Code]
    C --> D[Update Test Files]
    D --> E[Validate Changes]
    E --> F[Run Tests]
    F --> G[Complete]

    subgraph Dependencies
        B1[Remove pendulum from pyproject.toml]
    end

    subgraph ProductionCode
        C1[Update app/__init__.py]
        C2[Update app/repositories/authorization_code_repository.py]
        C3[Update app/services/auth_service.py]
        C4[Update app/services/token_service.py]
    end

    subgraph TestFiles
        D1[Update tests/conftest.py]
        D2[Update tests/integration/conftest.py]
        D3[Update tests/integration/test_auth_api.py]
        D4[Update tests/unit/conftest.py]
        D5[Update tests/unit/repository/test_authorization_code_repository.py]
        D6[Update tests/unit/repository/test_service_repository.py]
        D7[Update tests/unit/repository/test_token_repository.py]
        D8[Update tests/unit/service/test_auth_service.py]
        D9[Update tests/unit/service/test_token_service.py]
    end

    subgraph Validation
        E1[Code Review]
        E2[Manual Testing]
    end

    subgraph Testing
        F1[Unit Tests]
        F2[Integration Tests]
    end

    B --> B1
    C --> C1
    C --> C2
    C --> C3
    C --> C4
    D --> D1
    D --> D2
    D --> D3
    D --> D4
    D --> D5
    D --> D6
    D --> D7
    D --> D8
    D --> D9
    E --> E1
    E --> E2
    F --> F1
    F --> F2

    style A fill:#f9f,stroke:#333
    style G fill:#bbf,stroke:#333,color:#fff