resource "aws_dynamodb_table" "services" {
  name         = "${local.app_name}-services"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "name"
    type = "S"
  }

  global_secondary_index {
    name = "NameIndex"

    key_schema {
      attribute_name = "name"
      key_type       = "HASH"
    }

    projection_type = "ALL"
  }
}

resource "aws_dynamodb_table" "role_scopes" {
  name         = "${local.app_name}-role-scopes"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "role"

  attribute {
    name = "role"
    type = "S"
  }
}

resource "aws_dynamodb_table" "tokens" {
  name         = "${local.app_name}-tokens"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "jti"

  attribute {
    name = "jti"
    type = "S"
  }

  attribute {
    name = "refresh_token"
    type = "S"
  }

  global_secondary_index {
    name = "RefreshTokenIndex"

    key_schema {
      attribute_name = "refresh_token"
      key_type       = "HASH"
    }

    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}

resource "aws_dynamodb_table" "audiences" {
  name         = "${local.app_name}-audiences"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "audience"

  attribute {
    name = "audience"
    type = "S"
  }
}

resource "aws_dynamodb_table" "authorization_codes" {
  name         = "${local.app_name}-authorization-codes"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "code"
    type = "S"
  }

  global_secondary_index {
    name = "CodeIndex"

    key_schema {
      attribute_name = "code"
      key_type       = "HASH"
    }

    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}

resource "aws_dynamodb_table" "browser_sessions" {
  name         = "${local.app_name}-browser-sessions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}

resource "aws_dynamodb_table" "pending_authorization_requests" {
  name         = "${local.app_name}-pending-authorization-requests"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}

resource "aws_dynamodb_table" "google_oidc_states" {
  name         = "${local.app_name}-google-oidc-states"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "state"

  attribute {
    name = "state"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}
