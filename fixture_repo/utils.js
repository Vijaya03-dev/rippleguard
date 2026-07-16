export function formatCurrency(amount) {
    return `₹${amount.toFixed(2)}`;
}

export function generateId() {
    return Math.random().toString(36).substring(2, 9);
}