from app.services.row_validation import matches_type, validate_batch, validate_row


def test_matches_type():
    """Test primitive type matching."""
    # String
    assert matches_type("hello", "string") is True
    assert matches_type(123, "string") is False
    
    # Number (int and float, but NO bool)
    assert matches_type(123, "number") is True
    assert matches_type(12.5, "number") is True
    assert matches_type(0, "number") is True
    assert matches_type(-55, "number") is True
    
    assert matches_type(True, "number") is False  # Watch for bool shadow
    assert matches_type("123", "number") is False

    # Boolean
    assert matches_type(True, "boolean") is True
    assert matches_type(False, "boolean") is True
    assert matches_type(1, "boolean") is False
    assert matches_type(0, "boolean") is False


def test_validate_row_valid():
    """Test valid rows against a schema pass."""
    schema = {
        "name": "trade",
        "fields": [
            {"name": "symbol", "type": "string", "required": True},
            {"name": "price", "type": "number"},
            {"name": "active", "type": "boolean", "required": False},
        ]
    }
    
    # All fields
    row = {"symbol": "AAPL", "price": 10.5, "active": True}
    assert validate_row(row, schema) == []
    
    # Missing optional fields
    row_partial = {"symbol": "NVDA"}
    assert validate_row(row_partial, schema) == []


def test_validate_row_invalid():
    """Test rows with schema violations return precise errors."""
    schema = {
        "name": "trade",
        "fields": [
            {"name": "symbol", "type": "string", "required": True},
            {"name": "price", "type": "number"},
        ]
    }
    
    # Unknown field
    errors = validate_row({"symbol": "AAPL", "unknown": "xx"}, schema)
    assert len(errors) == 1
    assert errors[0]["field"] == "unknown"
    assert "Unknown field" in errors[0]["message"]
    
    # Missing required
    errors = validate_row({"price": 10}, schema)
    assert len(errors) == 1
    assert errors[0]["field"] == "symbol"
    assert "Required field is missing" in errors[0]["message"]
    
    # Incorrect type
    errors = validate_row({"symbol": "AAPL", "price": "100"}, schema)
    assert len(errors) == 1
    assert errors[0]["field"] == "price"
    assert "Expected number" in errors[0]["message"]


def test_validate_batch():
    """Test batch validation returns structured row-indexed errors."""
    schema = {
        "name": "trade",
        "fields": [
            {"name": "symbol", "type": "string", "required": True},
        ]
    }
    
    rows = [
        {"symbol": "AAPL"}, # Valid (index 0)
        {"symbol": 123},    # Invalid type (index 1)
        {"price": 500},     # Missing required, unknown field (index 2)
    ]
    
    row_errors = validate_batch(rows, schema)
    assert len(row_errors) == 2
    
    assert row_errors[0]["row_index"] == 1
    assert len(row_errors[0]["errors"]) == 1
    assert row_errors[0]["errors"][0]["field"] == "symbol"
    
    assert row_errors[1]["row_index"] == 2
    assert len(row_errors[1]["errors"]) == 2 # missing symbol, unknown price
