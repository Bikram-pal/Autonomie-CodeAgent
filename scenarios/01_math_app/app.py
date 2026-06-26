def safe_divide(a, b):
    if b == 0:
        return "Error: Division by zero"
    return a / b


def apply_discount(price, customer_type):
    if price < 0:
        raise ValueError("Price cannot be negative")

    if customer_type == "premium":
        return price * 0.80
    elif customer_type == "standard":
        return price * 0.95
    else:
        return price