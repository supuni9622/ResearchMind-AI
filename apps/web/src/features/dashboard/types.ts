export interface DashboardResearchSession {
  id: string;
  title: string;
  questionCount: number;
  documentCount: number;
  updatedAt: string;
}

export interface DashboardQuestion {
  id: string;
  question: string;
  conversationTitle: string;
  askedAt: string;
  conversationId: string;
}

export interface DashboardSuggestion {
  id: string;
  prompt: string;
  reason: string;
}
