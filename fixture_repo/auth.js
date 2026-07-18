import { generateId } from './utils';

export function createSession(userId) {
  const sessionId = generateId();
  const session = {
    sessionId,
    userId, 
    createdAt: new Date().toISOString(),
  };
  return session;
}

const sessions = new Map();

export function login(username, password) {
  const session = createSession(username);
  sessions.set(session.sessionId, session);
  return session;
}
export function logoutSession(sessionId) {
  sessions.delete(sessionId);
  return sessionId;
}
