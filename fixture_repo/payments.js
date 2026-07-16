import { formatCurrency, generateId } from './utils';
import { createSession } from './auth';

export function processPayment(userId, amount) {
  const session = createSession(userId);
  const transactionId = generateId();
  const formatted = formatCurrency(amount);
  return { transactionId, formatted, session };
}

export function refundPayment(transactionId) {
  return transactionId;
}