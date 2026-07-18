export function formatCurrency(amount) {
  return "Rs " + amount.toFixed(2);
}

export function generateId() {

  return Math.random().toString(36).substring(2 , 10);
}

const sessions = new Map();
const transactions = new Map();

export function logError(message) {
  console.log("Error: " + message);
  transactions.set(generateId(), { type: "error", message, timestamp: new Date().toISOString() });
}

export function isValidAmount(amount) {
  if (typeof amount !== "number") {
    return false;
  }
  if (isNaN(amount)) {
    return false;
  }
  return amount > 0;
}