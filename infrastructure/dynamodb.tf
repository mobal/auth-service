resource "aws_dynamodb_table" "users" {
  name         = "${var.stage}-users"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "email"
    type = "S"
  }

  attribute {
    name = "username"
    type = "S"
  }

  global_secondary_index {
    name = "EmailIndex"

    key_schema {
      attribute_name = "email"
      key_type = "HASH"
    }

    projection_type = "ALL"
  }

  global_secondary_index {
    name = "UsernameIndex"

    key_schema {
      attribute_name = "username"
      key_type = "HASH"
    }

    projection_type = "ALL"
  }
}

resource "aws_dynamodb_table" "services" {
  name         = "${var.stage}-services"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }
}

resource "aws_dynamodb_table" "tokens" {
  name         = "${var.stage}-tokens"
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
    name            = "RefreshTokenIndex"

    key_schema {
      attribute_name = "refresh_token"
      key_type = "HASH"
    }

    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}

resource "aws_dynamodb_table" "authorization_codes" {
  name         = "${var.stage}-authorization-codes"
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
    name            = "CodeIndex"

    key_schema {
      attribute_name = "code"
      key_type = "HASH"
    }

    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}
