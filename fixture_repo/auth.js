import { generateId } from './utils';

export function createSession(userId) {
  const sessionId = generateId();
  return { sessionId, userId };
}

export function login(username, password) {
  const session = createSession(username);
  return session;
}