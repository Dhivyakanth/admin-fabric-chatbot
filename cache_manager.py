

class CacheManager:
    def __init__(self):
        # Store context as {session_id: [ (question, answer), ... ] }
        self.sessions = {}

    def _normalize(self, question):
        return question.strip().lower() if question else ""

    def update_context(self, user_question, model_answer, session_id="default"):
        norm_q = self._normalize(user_question)
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append((norm_q, model_answer))

    def get_context(self, user_question=None, session_id="default"):
        if session_id not in self.sessions:
            return None
        if user_question:
            norm_q = self._normalize(user_question)
            for q, a in reversed(self.sessions[session_id]):
                if q == norm_q:
                    return a
            return None
        # Return full session context
        return self.sessions[session_id]
