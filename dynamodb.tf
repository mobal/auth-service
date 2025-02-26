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

  global_secondary_index {
    name            = "EmailIndex"
    hash_key        = "email"
    projection_type = "ALL"
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
    name = "jwt_token"
    type = "S"
  }

  attribute {
    name = "refresh_token"
    type = "S"
  }

  attribute {
    name = "ttl"
    type = "N"
  }
}