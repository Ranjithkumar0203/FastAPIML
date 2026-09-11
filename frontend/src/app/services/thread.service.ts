import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ChatMessage, Thread } from '../models';

@Injectable({ providedIn: 'root' })
export class ThreadService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = '/api';

  getThreads(): Observable<Thread[]> { return this.http.get<Thread[]>(`${this.apiUrl}/threads`); }
  createThread(): Observable<Thread> { return this.http.post<Thread>(`${this.apiUrl}/threads`, {}); }
  getMessages(threadId: string): Observable<ChatMessage[]> { return this.http.get<ChatMessage[]>(`${this.apiUrl}/threads/${threadId}/messages`); }
  deleteThread(threadId: string): Observable<void> { return this.http.delete<void>(`${this.apiUrl}/threads/${threadId}`); }
}
