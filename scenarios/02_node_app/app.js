function safeDivide(a, b) {
    if (b === 0) {
        return "Error: Division by zero";
    }
    return a / b;
}

function applyDiscount(price, customerType) {
    if (price < 0) {
        throw new Error("Price cannot be negative");
    }
    if (customerType === "premium") {
        return price * 0.80;
    } else if (customerType === "standard") {
        return price * 0.95;
    }
    return price;
}

module.exports = { safeDivide, applyDiscount };