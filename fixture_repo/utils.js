export function formatCurrency(amount) {
  return "Rs " + amount.toFixed(2);
}

export function generateId() {
  return Math.random().toString(36).substring(2, 9);
}

export function logError(message) {
  console.log("Error: " + message);
}