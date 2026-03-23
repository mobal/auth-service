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
